import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="FPK Converter",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    
    .info-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #667eea;
        margin: 10px 0px;
    }
    .info-title { color: #1f1f1f; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .info-value { color: #667eea; font-size: 24px; font-weight: 800; }
    
    .stButton>button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
    
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- LOGIKA LOGIN ---
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
    if not cleaned_df_list: raise ValueError("Data tidak ditemukan dalam format tabel.")
    
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
        with st.spinner("Sabar Fan, lagi dihitung..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                df_result = process_data(tmp_path)
                st.session_state.final_df = df_result
                st.session_state.final_total = df_result['Disetujui'].sum()
                st.session_state.final_count = len(df_result)
                os.unlink(tmp_path)
                st.success("Berhasil dikonversi!")
            except Exception as e:
                st.error(f"Gagal: {e}")

    if 'final_df' in st.session_state:
        st.divider()
        
        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")
        jumlah_data = f"{st.session_state.final_count} Data SEP"

        st.markdown(f"""
            <div class="info-box">
                <div class="info-title">JUMLAH DATA BERHASIL DI-CONVERT</div>
                <div class="info-value">{jumlah_data}</div>
                <br>
                <div class="info-title">TOTAL NOMINAL DARI CSV</div>
                <div class="info-value">{total_rp}</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.caption("Cek PDF lu, samain jumlah data & total nominalnya.")

      st.subheader("Preview Data")
        
        # Buat data bayangan untuk preview agar tidak merusak data asli
        df_preview = st.session_state.final_df.copy()
        df_preview.insert(0, 'No', range(1, 1 + len(df_preview)))
        
        # Tabel dengan kolom No yang kecil dan nominal rapi
        st.dataframe(
            df_preview, 
            use_container_width=True, 
            height=400, 
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn(
                    "No", 
                    width=40,    # Kolom No kecil banget
                ),
                "No.SEP": st.column_config.TextColumn(
                    "No. SEP", 
                    width="medium"
                ),
                "Disetujui": st.column_config.NumberColumn(
                    "Nominal Disetujui",
                    format="Rp %d", # Muncul titik ribuan otomatis
                    width="medium",
                )
            }
        )

        # Bagian Download
        csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"FPK_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        # Tombol Reset
        if st.button("Reset"):
            for key in ['final_df', 'final_total', 'final_count']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
