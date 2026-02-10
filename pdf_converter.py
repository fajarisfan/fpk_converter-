import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter", page_icon="🔐", layout="centered")

# --- STYLE CSS (Sama seperti sebelumnya) ---
st.markdown("""<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    .info-box { background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 8px solid #667eea; margin: 10px 0px; }
    .info-title { color: #1f1f1f; font-size: 14px; font-weight: bold; }
    .info-value { color: #667eea; font-size: 24px; font-weight: 800; }
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

# --- FUNGSI EKSTRAK NAMA PERIODE DARI PDF ---
def ambil_nama_periode(pdf_path):
    try:
        # Baca teks mentah dari halaman pertama saja untuk cari periode
        text_data = tabula.read_pdf(pdf_path, pages=1, area=[0, 0, 50, 100], relative_area=True, pandas_options={'header': None})
        full_text = " ".join(str(val) for df in text_data for val in df.values.flatten())
        
        # Cari pola bulan (Januari-Desember) dan Tahun
        match = re.search(r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}', full_text, re.IGNORECASE)
        if match:
            return f"FPK_{match.group(0).replace(' ', '_')}"
        return "Hasil_Konversi_FPK"
    except:
        return "Hasil_Konversi_FPK"

# --- FUNGSI PROSES DATA ---
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
st.markdown('<div class="main-header"><h1>📄 FPK Converter</h1></div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload PDF FPK", type=['pdf'], label_visibility="collapsed")

if uploaded_file:
    if st.button("Proses Sekarang"):
        with st.spinner("Sabar Fan, lagi dibaca isinya..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # 1. Ambil Nama Periode dari isi PDF
                nama_file_otomatis = ambil_nama_periode(tmp_path)
                
                # 2. Proses Data Tabel
                df_result = process_data(tmp_path)
                
                st.session_state.final_df = df_result
                st.session_state.final_total = df_result['Disetujui'].sum()
                st.session_state.final_count = len(df_result)
                st.session_state.auto_filename = f"{nama_file_otomatis}.csv"
                
                os.unlink(tmp_path)
                st.success(f"Berhasil! Periode terdeteksi: {nama_file_otomatis.replace('FPK_', '')}")
            except Exception as e:
                st.error(f"Gagal: {e}")

    if 'final_df' in st.session_state:
        st.divider()
        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
        
        st.markdown(f"""
            <div class="info-box">
                <div class="info-title">JUMLAH DATA</div><div class="info-value">{st.session_state.final_count} Data SEP</div><br>
                <div class="info-title">TOTAL NOMINAL</div><div class="info-value">{total_rp}</div>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Cek Dulu Datanya")
        df_preview = st.session_state.final_df.copy()
        df_preview.insert(0, 'No', range(1, 1 + len(df_preview)))
        
        st.dataframe(df_preview, use_container_width=True, height=350, hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width=40),
                "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d")
            }
        )

        # DOWNLOAD DENGAN NAMA OTOMATIS DARI ISI PDF
        csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"Ambil File {st.session_state.auto_filename}",
            data=csv_data,
            file_name=st.session_state.auto_filename,
            mime="text/csv"
        )
        
        if st.button("Mulai Ulang"):
            for key in ['final_df', 'final_total', 'final_count', 'auto_filename']:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
