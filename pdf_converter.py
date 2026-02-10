import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import time
from datetime import datetime
import base64

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="FPK PDF Converter + Viewer",
    page_icon="🔐",
    layout="wide",
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

# --- FUNGSI TAMPILKAN PDF (VERSI HP FRIENDLY) ---
def display_pdf(file_bytes):
    base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
    
    # Pake tag <object> sebagai alternatif <iframe> buat browser HP
    pdf_display = f"""
        <object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="600px">
            <div style="background:#fff3cd; padding:20px; border-radius:10px; border:1px solid #ffeeba;">
                <p>⚠️ <b>Waduh, HP lu nggak dukung pratinjau langsung.</b></p>
                <p>Tapi tenang, lu tetep bisa proses filenya kok. Kalau mau liat aslinya, klik tombol di bawah ini:</p>
                <a href="data:application/pdf;base64,{base64_pdf}" download="cek_pdf_asli.pdf" 
                   style="background:#667eea; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; display:inline-block;">
                   Buka PDF Manual
                </a>
            </div>
        </object>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- FUNGSI PROSES CONVERT ---
def process_pdf_to_df(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list: raise ValueError("Gagal baca tabel PDF.")
    
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    if not cleaned_df_list: raise ValueError("Struktur PDF tidak sesuai format FPK.")
    
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    
    # Bersihkan No.SEP
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    
    # Bersihkan Nominal (Polos untuk CSV)
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
        if st.session_state.pin_input == DEFAULT_PIN or pin_display == DEFAULT_PIN:
            st.session_state.logged_in = True; st.rerun()
        else: st.error("PIN Salah")
    st.markdown('</div>', unsafe_allow_html=True)

# --- HALAMAN UTAMA ---
def main_app():
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    st.markdown('<div class="main-header"><h1>📄 FPK Smart Converter</h1></div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload PDF FPK", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file:
        # Layout Bagi Dua
        col_pdf, col_hasil = st.columns([1.2, 1])
        
        with col_pdf:
            st.subheader("📑 Pratinjau PDF")
            display_pdf(uploaded_file.getvalue())
            
        with col_hasil:
            st.subheader("📊 Kontrol Konversi")
            
            # Button polos tanpa emot
            if st.button("Proses Sekarang", type="primary", use_container_width=True):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    # Simpan hasil di session state biar ga ilang pas rerun
                    st.session_state.result_df = process_pdf_to_df(tmp_path)
                    st.session_state.total_nominal = st.session_state.result_df['Disetujui'].sum()
                    os.unlink(tmp_path)
                    st.success("Konversi Berhasil!")
                except Exception as e:
                    st.error(f"Gagal: {e}")

            # Tampilkan hasil kalau sudah diproses
            if 'result_df' in st.session_state:
                df = st.session_state.result_df
                total = st.session_state.total_nominal
                
                # Tampilan Nominal (Hasil hitung CSV)
                st.metric("Total Nominal (Hasil Hitung CSV)", f"Rp {total:,.0f}".replace(",", "."))
                st.caption("Cocokkan angka di atas dengan nominal pada PDF di sebelah kiri.")
                
                st.dataframe(df, height=350, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download CSV", 
                    data=csv, 
                    file_name=f"FPK_{datetime.now().strftime('%Y%m%d')}.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )

def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in: login_page()
    else: main_app()

if __name__ == "__main__":
    main()

