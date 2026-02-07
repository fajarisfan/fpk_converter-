import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import hashlib
import time
from datetime import datetime, timedelta
from io import BytesIO
import base64

# Konfigurasi halaman
st.set_page_config(
    page_title="FPK PDF Converter",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk styling
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom login styling */
    .login-container {
        max-width: 400px;
        margin: 100px auto;
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
    
    .pin-input {
        letter-spacing: 8px;
        font-size: 24px;
        text-align: center;
        font-family: monospace !important;
        padding: 15px !important;
        margin: 10px 0;
    }
    
    .btn-login {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 15px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        width: 100% !important;
        margin-top: 20px !important;
    }
    
    .keypad-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin: 20px 0;
    }
    
    .keypad-btn {
        padding: 15px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        background: white;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .keypad-btn:hover {
        background: #f8f9fa;
        border-color: #667eea;
    }
    
    .keypad-btn.clear {
        grid-column: span 2;
        background: #ff6b6b;
        color: white;
        border-color: #ff6b6b;
    }
    
    .keypad-btn.enter {
        background: #667eea;
        color: white;
        border-color: #667eea;
    }
    
    .demo-info {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        text-align: left;
        border-left: 4px solid #667eea;
    }
    
    /* Main app styling */
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
    
    .btn-convert {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 15px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        width: 100% !important;
    }
    
    .btn-download {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%) !important;
        color: white !important;
        border: none !important;
        padding: 15px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        width: 100% !important;
    }
    
    .logout-btn {
        background: #ff6b6b !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        position: absolute;
        top: 20px;
        right: 20px;
    }
    
    .session-timer {
        position: fixed;
        top: 20px;
        right: 100px;
        background: white;
        padding: 10px 15px;
        border-radius: 8px;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 1000;
    }
    
    .timer-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: conic-gradient(#667eea 0% 100%, #e0e0e0 100% 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 12px;
    }
    
    .format-info {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Konfigurasi PIN (default: 1234)
DEFAULT_PIN = "1234"
SESSION_TIMEOUT = 1800  # 30 menit dalam detik

def hash_pin(pin):
    """Hash PIN untuk keamanan"""
    return hashlib.sha256(pin.encode()).hexdigest()

def check_session_timeout():
    """Cek apakah session sudah timeout"""
    if 'login_time' in st.session_state:
        elapsed = time.time() - st.session_state.login_time
        return elapsed > SESSION_TIMEOUT
    return True

def clean_fpk_data(pdf_path):
    """
    Fungsi pembersihan data FPK untuk format asli PDF
    """
    # 1. Ekstraksi Data dari PDF
    df_list = tabula.read_pdf(
        pdf_path, 
        pages='all', 
        multiple_tables=True, 
        lattice=True, 
        pandas_options={'header': None}
    )

    if not df_list:
        raise ValueError("Tidak ada tabel yang berhasil diekstrak.")

    # Filter dan Gabungkan DataFrames
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    
    if not cleaned_df_list:
        raise ValueError("Tidak ada tabel dengan struktur kolom yang sesuai (min 6 kolom) yang ditemukan.")
        
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()

    # Pembersihan Baris Non-Data
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    
    # Penentuan Nama Kolom
    df_data.columns = [
        'No. Urut',          
        'No.SEP',            
        'Tgl. Verifikasi',   
        'Biaya Riil RS',     
        'Diajukan',    
        'Disetujui'    
    ]

    # --- PEMBERSIHAN KOLOM No.SEP ---
    if 'No.SEP' in df_data.columns:
        df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.strip()
        df_data['No.SEP'] = df_data['No.SEP'].str.replace(r'[^a-zA-Z0-9]', '', regex=True)
        df_data['No.SEP'] = df_data['No.SEP'].str.replace(r'\s+', '', regex=True)
    
    # --- PEMBERSIHAN KOLOM Disetujui ---
    if 'Disetujui' in df_data.columns:
        df_data['Disetujui'] = df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
        df_data['Disetujui'] = df_data['Disetujui'].str.replace(r'\s+', '', regex=True)
        df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'], errors='coerce')
        df_data['Disetujui'] = df_data['Disetujui'].fillna(0).astype(int)
    
    # --- FILTER KOLOM YANG DIBUTUHKAN ---
    df_final = df_data[['No.SEP', 'Disetujui']].copy()
    
    # --- HAPUS BARIS KOSONG ATAU TIDAK VALID ---
    df_final = df_final[df_final['No.SEP'].notna() & (df_final['No.SEP'].str.strip() != '')]
    df_final = df_final[df_final['No.SEP'].str.replace(r'\s+', '', regex=True) != '']
    df_final = df_final[df_final['Disetujui'] > 0]
    df_final = df_final.reset_index(drop=True)
    
    return df_final

def get_download_link(df, filename="FPK_Data.csv"):
    """Generate download link untuk CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="btn-download">⬇️ Download CSV</a>'
    return href

def login_page():
    """Halaman login dengan PIN"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Logo
    st.markdown('<div class="logo-icon">🔐</div>', unsafe_allow_html=True)
    st.title("FPK Converter")
    st.markdown('<p class="text-muted">Masukkan PIN untuk mengakses konverter</p>', unsafe_allow_html=True)
    
    # PIN Input
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN Akses", type="password", max_chars=6, 
                           placeholder="••••••", key="pin_input",
                           label_visibility="collapsed")
    
    # Virtual Keypad dengan JavaScript
    keypad_js = """
    <script>
    function addKey(value) {
        const input = document.querySelector('input[type="password"]');
        if (input.value.length < 6) {
            input.value += value;
            // Trigger Streamlit update
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
        }
    }
    
    function clearKey() {
        const input = document.querySelector('input[type="password"]');
        input.value = '';
        const event = new Event('input', { bubbles: true });
        input.dispatchEvent(event);
    }
    
    // Add keyboard support
    document.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '9') {
            addKey(e.key);
        } else if (e.key === 'Backspace') {
            clearKey();
        } else if (e.key === 'Enter') {
            document.querySelector('.btn-login').click();
        }
    });
    </script>
    """
    
    st.markdown(keypad_js, unsafe_allow_html=True)
    
    # Keypad UI
    st.markdown('<div class="keypad-container">', unsafe_allow_html=True)
    cols = st.columns(3)
    
    keypad_buttons = [
        ("1", "2", "3"),
        ("4", "5", "6"),
        ("7", "8", "9"),
        ("C", "0", "↵")
    ]
    
    for row in keypad_buttons:
        cols = st.columns(3)
        for idx, key in enumerate(row):
            with cols[idx]:
                if key == "C":
                    if st.button("C", key=f"key_{key}", use_container_width=True):
                        st.session_state.pin_input = ""
                        st.rerun()
                elif key == "↵":
                    if st.button("↵", key=f"key_{key}", use_container_width=True, type="primary"):
                        # Login logic akan diproses di button login
                        pass
                else:
                    if st.button(key, key=f"key_{key}", use_container_width=True):
                        current_pin = st.session_state.get("pin_input", "")
                        if len(current_pin) < 6:
                            st.session_state.pin_input = current_pin + key
                            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Login Button
    if st.button("🔐 Masuk ke Konverter", key="login_btn", use_container_width=True):
        if pin == DEFAULT_PIN:
            st.session_state.logged_in = True
            st.session_state.login_time = time.time()
            st.session_state.user = "demo_user"
            st.session_state.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
            st.success("Login berhasil! Mengalihkan...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("PIN salah. Coba lagi.")
    
    # Demo Info
    st.markdown("""
    <div class="demo-info">
        <h6>📋 Info Demo</h6>
        <p><strong>PIN Demo:</strong> <code>1234</code></p>
        <p><small>Session akan berakhir dalam 30 menit setelah login</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back to Portfolio
    st.markdown("""
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://isfan.dev" style="color: #667eea; text-decoration: none;">
            ← Kembali ke Portfolio
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def main_app():
    """Halaman utama converter"""
    # Session timer
    if 'login_time' in st.session_state:
        elapsed = time.time() - st.session_state.login_time
        remaining = max(0, SESSION_TIMEOUT - elapsed)
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        # Update timer setiap detik
        if remaining > 0:
            st.markdown(f"""
            <div class="session-timer">
                <div class="timer-circle">{minutes:02d}:{seconds:02d}</div>
                <div>
                    <div style="font-weight: bold; font-size: 12px;">Session Timer</div>
                    <div style="font-size: 11px; color: #666;">Auto logout: {minutes:02d}:{seconds:02d}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Auto logout
            if remaining <= 0:
                st.session_state.clear()
                st.error("Session telah berakhir. Silakan login kembali.")
                st.stop()
        else:
            st.session_state.clear()
            st.error("Session telah berakhir. Silakan login kembali.")
            st.stop()
    
    # Logout button
    if st.button("🚪 Logout", key="logout_btn", use_container_width=False):
        st.session_state.clear()
        st.success("Logout berhasil!")
        time.sleep(1)
        st.rerun()
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>📄 FPK PDF to CSV Converter</h1>
        <p>Konversi file PDF FPK ke format CSV dengan header asli</p>
    </div>
    """, unsafe_allow_html=True)
    
    # User info
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info(f"👤 Logged in as: **Demo User** | Session ID: `{st.session_state.get('session_id', 'N/A')}`")
    
    # Upload section
    st.markdown('<div class="upload-area">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload File PDF FPK")
    st.markdown("Pilih atau tarik file PDF FPK untuk dikonversi")
    
    uploaded_file = st.file_uploader(
        " ",  # Empty label karena sudah ada di CSS
        type=['pdf'],
        label_visibility="collapsed",
        key="file_uploader"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Format info
    with st.expander("📋 Format Output CSV", expanded=True):
        st.code("""No.SEP,Disetujui
1028R0010825V007480,5810400
1028R0010825V007875,17002900
1028R0010825V007887,10572300""")
        st.markdown("""
        <div class="format-info">
            <p><strong>Format output:</strong> <code>No.SEP,Disetujui</code></p>
            <p><small>• Header sesuai dengan format PDF asli</small></p>
            <p><small>• Data sudah dibersihkan dari karakter tidak perlu</small></p>
            <p><small>• Hanya data valid yang akan diekstrak</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Process button
    if uploaded_file is not None:
        if st.button("✨ Konversi ke CSV", key="convert_btn", use_container_width=True, type="primary"):
            with st.spinner("🔄 Memproses PDF... Harap tunggu"):
                try:
                    # Simpan file upload ke temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    # Process PDF
                    df_result = clean_fpk_data(tmp_path)
                    
                    # Tampilkan preview
                    st.success(f"✅ Konversi berhasil! {len(df_result)} data diekstrak.")
                    
                    # Preview data
                    st.subheader("👁️ Preview Data (10 baris pertama)")
                    st.dataframe(df_result.head(10), use_container_width=True)
                    
                    if len(df_result) > 10:
                        st.caption(f"... dan {len(df_result) - 10} data lainnya")
                    
                    # Download section
                    st.subheader("📥 Download Hasil Konversi")
                    
                    # Generate filename
                    filename = f"FPK_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    # Download button
                    csv = df_result.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # Stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Data", len(df_result))
                    with col2:
                        st.metric("Format", "CSV UTF-8")
                    with col3:
                        st.metric("Header", "No.SEP, Disetujui")
                    
                    # Cleanup temporary file
                    os.unlink(tmp_path)
                    
                except Exception as e:
                    st.error(f"❌ Gagal memproses PDF: {str(e)}")
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
    else:
        st.info("📝 Silakan upload file PDF FPK untuk memulai konversi")

# Main app logic
def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Check session timeout
    if st.session_state.logged_in and check_session_timeout():
        st.session_state.clear()
        st.warning("Session telah berakhir. Silakan login kembali.")
    
    # Show appropriate page
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    # Check requirements
    try:
        import tabula
    except ImportError:
        st.error("❌ Package 'tabula-py' tidak terinstall. Install dengan: `pip install tabula-py`")
        st.stop()
    
    try:
        import pandas
    except ImportError:
        st.error("❌ Package 'pandas' tidak terinstall. Install dengan: `pip install pandas`")
        st.stop()
    
    # Run main app
    main()
