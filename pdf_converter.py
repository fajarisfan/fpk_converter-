import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
import pdfplumber
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter & Audit", page_icon="🔐", layout="centered")

# --- STYLE CSS (Ditambah style buat box audit) ---
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

# --- FUNGSI EKSTRAK NAMA PERIODE ---
def ambil_nama_periode(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            bulan_pola = r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)"
            match = re.search(f"{bulan_pola}\s+(\d{{4}})", text, re.IGNORECASE)
            if match:
                bulan = match.group(1).upper()
                tahun = match.group(2)
                return f"FPK_{bulan}_{tahun}"
    except Exception as e: print(f"Gagal baca periode: {e}")
    return "Hasil_Konversi_FPK"

# --- FUNGSI PROSES DATA TABEL ---
def process_data(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list: raise ValueError("PDF tidak terbaca.")
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)

# --- HALAMAN UTAMA ---
st.markdown('<div class="main-header"><h1>📄 FPK Converter & Audit</h1></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload PDF FPK", type=['pdf'], label_visibility="collapsed")

if uploaded_file:
    if st.button("Proses Sekarang"):
        with st.spinner("Sabar Fan, lagi dibaca isinya..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                nama_periode = ambil_nama_periode(tmp_path)
                df_result = process_data(tmp_path)
                st.session_state.final_df = df_result
                st.session_state.final_total = df_result['Disetujui'].sum()
                st.session_state.final_count = len(df_result)
                st.session_state.auto_filename = f"{nama_periode}.csv"
                os.unlink(tmp_path)
                st.success(f"Berhasil! File: {st.session_state.auto_filename}")
            except Exception as e: st.error(f"Gagal: {e}")

    if 'final_df' in st.session_state:
        st.divider()
        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
        
        st.markdown(f"""
            <div class="info-box">
                <div class="info-title">JUMLAH DATA</div><div class="info-value">{st.session_state.final_count} Data SEP</div><br>
                <div class="info-title">TOTAL NOMINAL KLAIM (GROSS)</div><div class="info-value">{total_rp}</div>
            </div>
        """, unsafe_allow_html=True)

        # --- FITUR AUDIT JASPEL (TAMBAHAN) ---
        st.markdown('<div class="audit-box"><h3>🔍 Audit Pembanding Jaspel</h3>', unsafe_allow_html=True)
        
        # Hitung Estimasi Jaspel Dasar (45%)
        estimasi_jaspel = st.session_state.final_total * 0.45
        
        # Input Net Jaspel dari ICHA untuk melihat potongan
        icha_input = st.number_input("Input 'Net Jaspel' dari Sistem ICHA:", value=0, help="Masukkan angka Jaspel yang muncul di sistem ICHA untuk dibandingkan.")
        
        if icha_input > 0:
            # Breakdown Pembagian (Logic ICHA: 64, 16, 12, 8)
            dr_sp = icha_input * 0.64
            perawat = icha_input * 0.16
            man_struk = icha_input * 0.12
            man_admin = icha_input * 0.08
            
            st.markdown(f"""
                <div class="info-title">ESTIMASI JASPEL (45% DARI GROSS)</div>
                <div class="audit-value">Rp {estimasi_jaspel:,.0f}</div><br>
                <div class="info-title">SELISIH POTONGAN (RS/PAJAK/DLL)</div>
                <div class="audit-value">Rp {estimasi_jaspel - icha_input:,.0f}</div>
            """, unsafe_allow_html=True)
            
            st.write("#### Pembagian Kantong Besar (Versi Audit):")
            audit_data = {
                "Kategori": ["Dokter Sp/Operator (64%)", "Perawat/Askep (16%)", "Manajemen Struktural (12%)", "Manajemen Admin (8%)"],
                "Nominal": [dr_sp, perawat, man_struk, man_admin]
            }
            st.table(pd.DataFrame(audit_data).style.format({"Nominal": "Rp {:,.0f}"}))
        else:
            st.warning("Masukkan angka Net Jaspel ICHA di atas untuk melihat pembagian.")
        
        st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("Preview Data")
        df_preview = st.session_state.final_df.copy()
        df_preview.insert(0, 'No', range(1, 1 + len(df_preview)))
        st.dataframe(df_preview, use_container_width=True, height=300, hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width=40),
                "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d")
            }
        )

        csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Ambil File CSV", data=csv_data, file_name=st.session_state.auto_filename, mime="text/csv")
        
        if st.button("Reset"):
            for key in ['final_df', 'final_total', 'final_count', 'auto_filename']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
