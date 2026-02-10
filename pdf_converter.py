import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import hashlib
import time
from datetime import datetime
import base64

# Konfigurasi halaman
st.set_page_config(
    page_title="FPK PDF Converter",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk tampilan professional
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .login-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 40px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        text-align: center;
    }
    .logo-icon {
        font-size: 64px;
        color: #667eea;
        margin-bottom: 20px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .keypad-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin: 20px 0;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .upload-area {
        border: 3px dashed #667eea;
        border-radius: 10px;
        padding: 3rem;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

DEFAULT_PIN = "1234"
SESSION_TIMEOUT = 1800 

# --- FUNGSI PROSES PDF ---
def clean_fpk_data(pdf_path):
    # Ekstraksi Data
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list:
        raise ValueError("Gagal baca tabel PDF.")

    # Filter tabel yang valid
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    if not cleaned_df_list:
        raise ValueError("Struktur PDF tidak sesuai format FPK.")
        
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']

    # Bersihkan No.SEP
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    
    # Bersihkan Nominal (Simpan sebagai angka murni untuk CSV)
    df_data['Disetujui'] = df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'], errors='coerce').fillna(0).astype(int)
    
    # Total nominal untuk Dashboard (Visual Only)
    total_val = df_data['Disetujui'].sum()
    
    # Data Final (Nominal tetap polos sesuai SOP Jaspel Icha)
    df_final = df_data[['No.SEP', 'Disetujui']].copy()
    df_final = df_final[df_final['No.SEP'] != ""].reset_index(drop=True)
    
    return df_final, total_val

# --- HALAMAN LOGIN (KEYPAD STABLE) ---
def login_page():
    if 'pin_input' not in st.session_state:
        st.session_state.pin_input = ""

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="logo-icon">🔐</div>', unsafe_allow_html=True)
    st.title("FPK Converter")
    
    # Input field sinkron dengan session state
    pin_display = st.text_input("PIN Akses", type="password", value=st.session_state.pin_input, 
                               placeholder="••••••", label_visibility="collapsed")
    
    # Keypad Logic
    st.markdown('<div class="keypad-container">', unsafe_allow_html=True)
    for row in [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]:
        cols = st.columns(3)
        for idx, num in enumerate(row):
            if cols[idx].button(num, key=f"btn_{num}", use_container_width=True):
                if len(st.session_state.pin_input) < 6:
                    st.session_state.pin_input += num
                    st.rerun()

    c1, c2, c3 = st.columns(3)
    if c1.button("C", key="btn_clear", use_container_width=True):
        st.session_state.pin_input = ""; st.rerun()
    if c2.button("0", key="btn_0", use_container_width=True):
        if len(st.session_state.pin_input) < 6:
            st.session_state.pin_input += "0"; st.rerun()
    if c3.button("⌫", key="btn_back", use_container_width=True):
        st.session_state.pin_input = st.session_state.pin_input[:-1]; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🔓 Masuk ke Konverter", key="login_btn", use_container_width=True, type="primary"):
        if st.session_state.pin_input == DEFAULT_PIN or pin_display == DEFAULT_PIN:
            st.session_state.logged_in = True
            st.session_state.login_time = time.time()
            st.rerun()
        else:
            st.error("PIN salah!")
    st.markdown('</div>', unsafe_allow_html=True)

# --- HALAMAN UTAMA ---
def main_app():
    # Logout button
    if st.button("🚪 Logout"):
        st.session_state.clear(); st.rerun()

    st.markdown('<div class="main-header"><h1>📄 FPK PDF to CSV Converter</h1><p>Recon Data RS & SOP Jaspel</p></div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Pilih File PDF FPK", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        if st.button("✨ Konversi Sekarang", type="primary", use_container_width=True):
            with st.spinner("🔄 Sedang memproses..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    df_res, total_rp = clean_fpk_data(tmp_path)
                    
                    # TAMPILAN STATISTIK (Pake Titik biar gampang dicek)
                    st.success(f"✅ Berhasil! {len(df_res)} data SEP diekstrak.")
                    m1, m2 = st.columns(2)
                    m1.metric("Total SEP", f"{len(df_res)} Baris")
                    # Format Rupiah pake titik cuma buat di dashboard web
                    formatted_nominal = f"Rp {total_rp:,.0f}".replace(",", ".")
                    m2.metric("Total Nominal Disetujui", formatted_nominal)
                    
                    st.divider()
                    
                    # PREVIEW & DOWNLOAD (Nominal murni tanpa titik buat SOP Icha)
                    st.subheader("👁️ Preview Data (Nominal Polos)")
                    st.dataframe(df_res, use_container_width=True)
                    
                    csv_data = df_res.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV (Format Jaspel)",
                        data=csv_data,
                        file_name=f"FPK_RESULT_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Gagal proses: {e}")

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
