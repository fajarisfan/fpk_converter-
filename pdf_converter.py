import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import hashlib
import time
from datetime import datetime
import base64

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="FPK PDF Converter + Viewer",
    page_icon="🔐",
    layout="wide", # Pakai layout wide biar lega buat bagi 2 layar
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .login-container { max-width: 400px; margin: 80px auto; padding: 40px; background: white; border-radius: 15px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2); text-align: center; }
    .keypad-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem; }
    .stMetric { background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #667eea; }
</style>
""", unsafe_allow_html=True)

DEFAULT_PIN = "1234"

# --- FUNGSI TAMPILKAN PDF ---
def display_pdf(file_bytes):
    base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- FUNGSI PROSES CONVERT ---
def process_pdf_to_df(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list: raise ValueError("Gagal baca tabel PDF.")
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    if not cleaned_df_list: raise ValueError("Struktur PDF tidak sesuai.")
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'], errors='coerce').fillna(0).astype(int)
    df_final = df_data[['No.SEP', 'Disetujui']].copy()
    return df_final[df_final['No.SEP'] != ""].reset_index(drop=True)

# --- HALAMAN LOGIN ---
def login_page():
    if 'pin_input' not in st.session_state: st.session_state.pin_input = ""
    st.markdown('<div class="login-container"><h1>🔓 Login</h1>', unsafe_allow_html=True)
    pin_display = st.text_input("PIN", type="password", value=st.session_state.pin_input, placeholder="••••••", label_visibility="collapsed")
    st.markdown('<div class="keypad-container">', unsafe_allow_html=True)
    for num in ["1","2","3","4","5","6","7","8","9","C","0","⌫"]:
        if st.button(num, key=f"k_{num}", use_container_width=True):
            if num == "C": st.session_state.pin_input = ""
            elif num == "⌫": st.session_state.pin_input = st.session_state.pin_input[:-1]
            elif len(st.session_state.pin_input) < 6: st.session_state.pin_input += num
            st.rerun()
    if st.button("Masuk", use_container_width=True, type="primary"):
        if st.session_state.pin_input == DEFAULT_PIN:
            st.session_state.logged_in = True; st.rerun()
        else: st.error("PIN Salah")
    st.markdown('</div>', unsafe_allow_html=True)

# --- HALAMAN UTAMA ---
def main_app():
    st.markdown('<div class="main-header"><h1>📄 FPK Smart Converter</h1></div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload PDF FPK", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        # Layout Bagi Dua: Kiri (PDF) | Kanan (Hasil)
        col_pdf, col_hasil = st.columns([1, 1])
        
        with col_pdf:
            st.subheader("📑 Dokumen PDF Asli")
            display_pdf(uploaded_file.getvalue()) # PDF diem di sini
            
        with col_hasil:
            st.subheader("📊 Hasil Konversi CSV")
            if st.button("✨ Proses Sekarang", type="primary", use_container_width=True):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    df_convert = process_pdf_to_df(tmp_path)
                    total_nominal = df_convert['Disetujui'].sum()
                    
                    # Dashboard Statistik
                    st.success(f"Ditemukan {len(df_convert)} data SEP.")
                    st.metric("Total Nominal (Hasil Convert)", f"Rp {total_nominal:,.0f}".replace(",", "."))
                    
                    st.warning("⚠️ Cek total nominal di atas dengan angka di PDF sebelah kiri!")
                    
                    # Preview Tabel
                    st.dataframe(df_convert, height=400, use_container_width=True)
                    
                    # Download Button
                    csv = df_convert.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download CSV (Format Jaspel)", csv, "Hasil_FPK.csv", "text/csv", use_container_width=True)
                    
                    os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Silakan upload PDF untuk melihat pratinjau dan konversi.")

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in: login_page()
    else: main_app()

if __name__ == "__main__":
    main()
