import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
from datetime import datetime
import base64

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="FPK Converter",
    page_icon="🔐",
    layout="centered", # Pakai centered biar fokus di tengah layar HP
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    .stMetric { background: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #667eea; }
    .stButton>button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- LOGIKA LOGIN SEDERHANA ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="main-header"><h1>🔐 Masuk</h1></div>', unsafe_allow_html=True)
    pin = st.text_input("Masukkan PIN", type="password")
    if st.button("Masuk"):
        if pin == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("PIN Salah")
    st.stop()

# --- FUNGSI PROSES ---
def process_data(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list: raise ValueError("PDF tidak terbaca.")
    
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'], errors='coerce').fillna(0).astype(int)
    
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)

# --- HALAMAN UTAMA ---
st.markdown('<div class="main-header"><h1>📄 FPK Converter</h1></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload PDF FPK", type=['pdf'], label_visibility="collapsed")

if uploaded_file:
    if st.button("Proses Sekarang"):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            # Convert & Hitung
            df_result = process_data(tmp_path)
            st.session_state.final_df = df_result
            st.session_state.final_total = df_result['Disetujui'].sum()
            os.unlink(tmp_path)
            st.success("Berhasil dikonversi!")
        except Exception as e:
            st.error(f"Gagal: {e}")

    # Munculin Hasil (Sebelum Download)
    if 'final_df' in st.session_state:
        st.divider()
        
        # Angka Nominal Hasil Convert
        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
        st.metric(label="Total Nominal dari CSV", value=total_rp)
        st.caption("Samakan angka di atas dengan total yang ada di PDF lu.")

        # Preview Tabel
        st.subheader("Preview Data")
        st.dataframe(st.session_state.final_df, use_container_width=True, height=300)

        # Download
        csv = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"FPK_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        if st.button("Reset"):
            del st.session_state.final_df
            st.rerun()
