import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
import pdfplumber
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter Multi-File", page_icon="🔐", layout="centered")

# --- STYLE CSS ---
st.markdown("""<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    .info-box { background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 8px solid #667eea; margin: 10px 0px; }
    .audit-box { background-color: #fff4e6; padding: 20px; border-radius: 15px; border-left: 8px solid #ff922b; margin: 20px 0px; }
    .info-title { color: #1f1f1f; font-size: 14px; font-weight: bold; }
    .info-value { color: #667eea; font-size: 24px; font-weight: 800; }
    .audit-value { color: #d9480f; font-size: 20px; font-weight: 700; }
    .stButton>button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- LOGIKA LOGIN (PIN: 1234) ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<div class="main-header"><h1>🔐 Masuk</h1></div>', unsafe_allow_html=True)
    pin = st.text_input("Masukkan PIN", type="password")
    if st.button("Masuk"):
        if pin == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else: st.error("PIN Salah")
    st.stop()

# --- FUNGSI PROSES DATA TABEL ---
def process_data(pdf_path):
    try:
        df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
        if not df_list: return pd.DataFrame()
        
        cleaned_df_list = []
        for df in df_list:
            if df.shape[1] >= 6 and len(df) > 1:
                cleaned_df_list.append(df)
        
        if not cleaned_df_list: return pd.DataFrame()
        
        df = pd.concat(cleaned_df_list, ignore_index=True)
        df_data = df.iloc[:, :6].copy()
        df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
        
        df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
        df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
        df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
        
        return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

# --- HALAMAN UTAMA ---
st.markdown('<div class="main-header"><h1>📄 Multi FPK Converter & Audit</h1></div>', unsafe_allow_html=True)

# Update: accept_multiple_files=True agar bisa upload RI dan RJ sekaligus
uploaded_files = st.file_uploader("Upload PDF FPK (Bisa pilih banyak sekaligus)", type=['pdf'], accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    if st.button("Proses Sekarang"):
        all_dfs = []
        total_nominal = 0
        total_data = 0
        
        with st.spinner(f"Lagi baca {len(uploaded_files)} file, sabar ya..."):
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                df_hasil = process_data(tmp_path)
                if not df_hasil.empty:
                    all_dfs.append(df_hasil)
                
                os.unlink(tmp_path)
            
            if all_dfs:
                final_combined_df = pd.concat(all_dfs, ignore_index=True)
                st.session_state.final_df = final_combined_df
                st.session_state.final_total = final_combined_df['Disetujui'].sum()
                st.session_state.final_count = len(final_combined_df)
                st.success(f"Berhasil menggabungkan {len(uploaded_files)} file!")
            else:
                st.error("Gagal membaca data dari file yang diupload.")

    if 'final_df' in st.session_state:
        st.divider()
        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
        
        st.markdown(f"""
            <div class="info-box">
                <div class="info-title">TOTAL DATA GABUNGAN</div><div class="info-value">{st.session_state.final_count} Data SEP</div><br>
                <div class="info-title">TOTAL NOMINAL KLAIM (GROSS)</div><div class="info-value">{total_rp}</div>
            </div>
        """, unsafe_allow_html=True)

        # --- FITUR AUDIT JASPEL (MULTI-FILE) ---
        st.markdown('<div class="audit-box"><h3>🔍 Audit Pembanding Jaspel</h3>', unsafe_allow_html=True)
        
        # Hitung Estimasi Jaspel Dasar (45%) dari TOTAL GABUNGAN
        estimasi_jaspel = st.session_state.final_total * 0.45
        
        st.markdown(f"""
            <div class="info-title">ESTIMASI JASPEL (45% DARI TOTAL KLAIM)</div>
            <div class="audit-value">Rp {estimasi_jaspel:,.0f}</div>
        """, unsafe_allow_html=True)
        
        icha_input = st.number_input("Input 'Net Jaspel' dari Sistem ICHA:", value=0)
        
        if icha_input > 0:
            st.markdown(f"""
                <div class="info-title">SELISIH POTONGAN (RS/PAJAK/DLL)</div>
                <div class="audit-value">Rp {estimasi_jaspel - icha_input:,.0f}</div>
            """, unsafe_allow_html=True)
            
            st.write("#### Pembagian Kantong Besar (Berdasarkan Net ICHA):")
            audit_data = {
                "Kategori": ["Dokter Sp/Operator (64%)", "Perawat/Askep (16%)", "Manajemen Struktural (12%)", "Manajemen Admin (8%)"],
                "Nominal": [icha_input * 0.64, icha_input * 0.16, icha_input * 0.12, icha_input * 0.08]
            }
            st.table(pd.DataFrame(audit_data).style.format({"Nominal": "Rp {:,.0f}"}))
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Download Gabungan
        csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Ambil CSV Gabungan", data=csv_data, file_name="FPK_GABUNGAN_AUDIT.csv", mime="text/csv")
        
        if st.button("Reset"):
            for key in ['final_df', 'final_total', 'final_count']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
