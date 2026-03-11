import os
import pandas as pd
import streamlit as st
import tabula
import tempfile
import re
import pdfplumber
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="FPK Converter", page_icon="⚡", layout="centered")

# --- STYLE CSS MODERN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    * { font-family: 'Sora', sans-serif !important; }
    
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    
    /* Background */
    .stApp {
        background-color: #0a0a0f;
        background-image: 
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent),
            radial-gradient(ellipse 40% 40% at 80% 80%, rgba(139, 92, 246, 0.08), transparent);
    }
    
    /* Sembunyiin semua elemen default streamlit yg ga perlu */
    .block-container { padding-top: 2rem; max-width: 680px; }

    /* HEADER */
    .app-header {
        text-align: center;
        padding: 3rem 2rem 2rem;
        margin-bottom: 0.5rem;
    }
    .app-header .badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #818cf8;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 6px 16px;
        border-radius: 100px;
        margin-bottom: 1.2rem;
    }
    .app-header h1 {
        font-size: 3rem !important;
        font-weight: 800 !important;
        color: #f1f5f9 !important;
        line-height: 1.1 !important;
        margin: 0 !important;
        letter-spacing: -1.5px;
    }
    .app-header h1 span {
        background: linear-gradient(135deg, #6366f1, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .app-header p {
        color: #64748b;
        font-size: 0.95rem;
        margin-top: 0.8rem;
        font-weight: 300;
    }

    /* LOGIN BOX */
    .login-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 20px;
        padding: 2.5rem;
        backdrop-filter: blur(10px);
        margin-top: 1rem;
    }
    
    /* UPLOAD AREA */
    .upload-zone {
        background: rgba(255,255,255,0.02);
        border: 1.5px dashed rgba(99, 102, 241, 0.35);
        border-radius: 20px;
        padding: 2rem;
        transition: all 0.3s;
        margin-bottom: 1rem;
    }
    .upload-zone:hover {
        border-color: rgba(99, 102, 241, 0.7);
        background: rgba(99, 102, 241, 0.05);
    }

    /* INPUT FIELDS */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
        padding: 14px 18px !important;
        font-size: 0.95rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 4px !important;
        transition: all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(99, 102, 241, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }
    .stTextInput label {
        color: #94a3b8 !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }

    /* FILE UPLOADER */
    .stFileUploader > div {
        background: rgba(255,255,255,0.02) !important;
        border: 1.5px dashed rgba(99, 102, 241, 0.35) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        transition: all 0.3s !important;
    }
    .stFileUploader > div:hover {
        border-color: rgba(99, 102, 241, 0.7) !important;
        background: rgba(99, 102, 241, 0.05) !important;
    }
    .stFileUploader label {
        color: #94a3b8 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #64748b !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] span {
        color: #818cf8 !important;
        font-weight: 600 !important;
    }

    /* BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 52px !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4) !important;
        filter: brightness(1.1) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* RESET BUTTON - khusus */
    .reset-btn > button {
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #64748b !important;
        box-shadow: none !important;
    }
    .reset-btn > button:hover {
        background: rgba(255,255,255,0.05) !important;
        color: #94a3b8 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* DOWNLOAD BUTTON */
    .stDownloadButton > button {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        color: #34d399 !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.1) !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(16, 185, 129, 0.2) !important;
        border-color: rgba(16, 185, 129, 0.5) !important;
        box-shadow: 0 8px 30px rgba(16, 185, 129, 0.2) !important;
        color: #6ee7b7 !important;
    }

    /* STATS CARDS */
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .stat-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.2s;
    }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    .stat-card:last-child::before {
        background: linear-gradient(90deg, #10b981, #34d399);
    }
    .stat-label {
        color: #475569;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .stat-value {
        color: #f1f5f9;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1;
    }
    .stat-value.green { color: #34d399; }
    .stat-sub {
        color: #334155;
        font-size: 0.75rem;
        margin-top: 0.4rem;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* SUCCESS & ERROR MSGS */
    .stSuccess {
        background: rgba(16, 185, 129, 0.08) !important;
        border: 1px solid rgba(16, 185, 129, 0.2) !important;
        border-radius: 12px !important;
        color: #34d399 !important;
    }
    .stError {
        background: rgba(239, 68, 68, 0.08) !important;
        border: 1px solid rgba(239, 68, 68, 0.2) !important;
        border-radius: 12px !important;
    }

    /* SPINNER */
    .stSpinner > div {
        border-top-color: #6366f1 !important;
    }

    /* DIVIDER */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
        margin: 1.5rem 0 !important;
    }

    /* DATAFRAME */
    .stDataFrame {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
    }
    [data-testid="stDataFrameResizable"] {
        background: rgba(255,255,255,0.02) !important;
    }

    /* SUBHEADER */
    .stSubheader, h3 {
        color: #94a3b8 !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }

    /* SUCCESS BADGE */
    .file-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #34d399;
        padding: 8px 16px;
        border-radius: 100px;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# --- LOGIKA LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""
        <div class="app-header">
            <div class="badge">⚡ FPK Converter</div>
            <h1>Selamat <span>Datang</span></h1>
            <p>Masukkan PIN untuk mengakses aplikasi</p>
        </div>
    """, unsafe_allow_html=True)

    pin = st.text_input("PIN AKSES", type="password", placeholder="••••")
    if st.button("Masuk →"):
        if pin == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ PIN salah. Coba lagi.")
    st.stop()


# --- FUNGSI EKSTRAK NAMA PERIODE ---
def ambil_nama_periode(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            bulan_pola = r"(JANUARI|FEBRUARI|MARET|APRIL|MEI|JUNI|JULI|AGUSTUS|SEPTEMBER|OKTOBER|NOVEMBER|DESEMBER)"
            match = re.search(f"{bulan_pola}\\s+(\\d{{4}})", text, re.IGNORECASE)
            if match:
                bulan = match.group(1).upper()
                tahun = match.group(2)
                return f"FPK_{bulan}_{tahun}"
    except Exception as e:
        print(f"Gagal baca periode: {e}")
    return "Hasil_Konversi_FPK"


# --- FUNGSI PROSES DATA TABEL ---
def process_data(pdf_path):
    df_list = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, lattice=True, pandas_options={'header': None})
    if not df_list:
        raise ValueError("PDF tidak terbaca.")
    cleaned_df_list = [df for df in df_list if df.shape[1] >= 6 and len(df) > 1]
    df = pd.concat(cleaned_df_list, ignore_index=True)
    df_data = df.iloc[:, :6].copy()
    df_data = df_data[pd.to_numeric(df_data.iloc[:, 0], errors='coerce').notna()]
    df_data.columns = ['No. Urut', 'No.SEP', 'Tgl. Verifikasi', 'Biaya Riil RS', 'Diajukan', 'Disetujui']
    df_data['No.SEP'] = df_data['No.SEP'].astype(str).str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.strip()
    df_data['Disetujui'] = pd.to_numeric(df_data['Disetujui'].astype(str).str.replace(r'[^0-9]', '', regex=True), errors='coerce').fillna(0).astype(int)
    return df_data[['No.SEP', 'Disetujui']].reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════
# MODUL AUDIT JASPEL — SIMRS ICHA
# Berdasarkan Dokumentasi Modul Jaspel SIMRS ICHA
# (ditambahkan sebagai tab ke-2, kode FPK Converter tidak diubah)
# ═══════════════════════════════════════════════════════════════════
import numpy as np
import io

# ── Konstanta Master Jaspel ──────────────────────────────────────

TARIF_BPJS = {
    "Rawat Jalan Rehabilitasi Medik": 0.45,
    "Rawat Jalan Hemodialisa":        0.30,
    "Rawat Jalan (Lainnya)":          0.35,
    "Rawat Inap":                     0.30,
    "IGD":                            0.35,
}
TARIF_SELISIH = 0.05
TARIF_BARANG  = 0.0385

KOLOM_PENERIMA = [
    "dr_operator", "dr_spesialis", "dr_umum",
    "perawat", "petugas_khusus", "mgmt_struktural", "mgmt_administrasi", "farmasi"
]

MASTER_JASPEL = {
    0:  {"info": "NON Jaspel",                                                          "type": "-",        "dr_operator": 0,  "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 0,  "mgmt_struktural": 0,  "mgmt_administrasi": 0,  "farmasi": 0},
    1:  {"info": "Pemeriksaan Dokter (Poli & IGD)",                                     "type": "BPJS",     "dr_operator": 64, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 16, "petugas_khusus": 0,  "mgmt_struktural": 12, "mgmt_administrasi": 8,  "farmasi": 0},
    2:  {"info": "Visit, Konsul & Askep - Dokter Spesialis",                            "type": "BPJS",     "dr_operator": 51, "dr_spesialis": 0,  "dr_umum": 13, "perawat": 16, "petugas_khusus": 0,  "mgmt_struktural": 12, "mgmt_administrasi": 8,  "farmasi": 0},
    3:  {"info": "Visit, Konsul & Askep - Dokter Umum",                                 "type": "BPJS",     "dr_operator": 0,  "dr_spesialis": 13, "dr_umum": 51, "perawat": 16, "petugas_khusus": 0,  "mgmt_struktural": 12, "mgmt_administrasi": 8,  "farmasi": 0},
    4:  {"info": "Visit, Konsul & Askep - Asuhan Keperawatan",                          "type": "BPJS",     "dr_operator": 8,  "dr_spesialis": 0,  "dr_umum": 8,  "perawat": 60, "petugas_khusus": 0,  "mgmt_struktural": 13, "mgmt_administrasi": 11, "farmasi": 0},
    5:  {"info": "Tindakan Operatif di OK & VK - Operator",                             "type": "BPJS",     "dr_operator": 59, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 8,  "petugas_khusus": 12, "mgmt_struktural": 14, "mgmt_administrasi": 7,  "farmasi": 0},
    6:  {"info": "Tindakan Operatif di OK & VK - Anastesi",                             "type": "BPJS",     "dr_operator": 59, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 7,  "petugas_khusus": 15, "mgmt_struktural": 12, "mgmt_administrasi": 7,  "farmasi": 0},
    7:  {"info": "Tindakan di Ruangan - Medis",                                         "type": "BPJS",     "dr_operator": 66, "dr_spesialis": 0,  "dr_umum": 2,  "perawat": 17, "petugas_khusus": 0,  "mgmt_struktural": 9,  "mgmt_administrasi": 6,  "farmasi": 0},
    8:  {"info": "Tindakan di Ruangan - Medis Didelegasikan",                           "type": "BPJS",     "dr_operator": 30, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 45, "petugas_khusus": 0,  "mgmt_struktural": 14, "mgmt_administrasi": 11, "farmasi": 0},
    9:  {"info": "Tindakan di Ruangan - Keperawatan",                                   "type": "BPJS",     "dr_operator": 15, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 60, "petugas_khusus": 0,  "mgmt_struktural": 13, "mgmt_administrasi": 12, "farmasi": 0},
    10: {"info": "Radiologi - Rontgen",                                                  "type": "BPJS",     "dr_operator": 56, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 2,  "petugas_khusus": 22, "mgmt_struktural": 10, "mgmt_administrasi": 10, "farmasi": 0},
    11: {"info": "Radiologi - USG",                                                      "type": "BPJS",     "dr_operator": 68, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 2,  "petugas_khusus": 15, "mgmt_struktural": 9,  "mgmt_administrasi": 6,  "farmasi": 0},
    12: {"info": "Radiologi - CT SCAN",                                                  "type": "BPJS",     "dr_operator": 68, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 2,  "petugas_khusus": 15, "mgmt_struktural": 9,  "mgmt_administrasi": 6,  "farmasi": 0},
    13: {"info": "Tindakan Rehab Medis - Dokter",                                        "type": "BPJS",     "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 15, "farmasi": 0},
    14: {"info": "Tindakan Rehab Medis - Terapis",                                       "type": "BPJS",     "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 50, "mgmt_struktural": 10, "mgmt_administrasi": 15, "farmasi": 0},
    15: {"info": "Tindakan Rehab Medis - Terapi Wicara",                                 "type": "BPJS",     "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 50, "mgmt_struktural": 10, "mgmt_administrasi": 15, "farmasi": 0},
    16: {"info": "Tindakan Rehab Medis - Ocupasi Terapi",                                "type": "BPJS",     "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 50, "mgmt_struktural": 10, "mgmt_administrasi": 15, "farmasi": 0},
    17: {"info": "Tindakan Rehab Medis - Psikologi",                                     "type": "BPJS",     "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 50, "mgmt_struktural": 10, "mgmt_administrasi": 15, "farmasi": 0},
    18: {"info": "Laboratorium",                                                          "type": "BPJS",     "dr_operator": 34, "dr_spesialis": 2,  "dr_umum": 4,  "perawat": 7,  "petugas_khusus": 30, "mgmt_struktural": 12, "mgmt_administrasi": 11, "farmasi": 0},
    19: {"info": "Laboratorium Patologi Anatomi",                                         "type": "BPJS",     "dr_operator": 68, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 2,  "petugas_khusus": 15, "mgmt_struktural": 9,  "mgmt_administrasi": 6,  "farmasi": 0},
    20: {"info": "Farmasi",                                                               "type": "BPJS",     "dr_operator": 5,  "dr_spesialis": 0,  "dr_umum": 2,  "perawat": 5,  "petugas_khusus": 53, "mgmt_struktural": 15, "mgmt_administrasi": 20, "farmasi": 0},
    21: {"info": "Hemodialisa",                                                           "type": "BPJS",     "dr_operator": 30, "dr_spesialis": 0,  "dr_umum": 30, "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 12, "mgmt_administrasi": 8,  "farmasi": 0},
    22: {"info": "Bank Darah RS",                                                         "type": "BPJS",     "dr_operator": 40, "dr_spesialis": 2,  "dr_umum": 2,  "perawat": 5,  "petugas_khusus": 26, "mgmt_struktural": 14, "mgmt_administrasi": 11, "farmasi": 0},
    23: {"info": "Pemulasaraan Jenazah",                                                  "type": "BPJS",     "dr_operator": 49, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 16, "mgmt_struktural": 13, "mgmt_administrasi": 15, "farmasi": 0},
    24: {"info": "Instalasi Forensik - Visum Dokter Spesialis",                          "type": "BPJS",     "dr_operator": 52, "dr_spesialis": 0,  "dr_umum": 10, "perawat": 2,  "petugas_khusus": 18, "mgmt_struktural": 10, "mgmt_administrasi": 8,  "farmasi": 0},
    25: {"info": "Instalasi Forensik - Visum Dokter Umum",                               "type": "BPJS",     "dr_operator": 0,  "dr_spesialis": 10, "dr_umum": 52, "perawat": 2,  "petugas_khusus": 18, "mgmt_struktural": 10, "mgmt_administrasi": 8,  "farmasi": 0},
    26: {"info": "Instalasi Forensik - Hispatologi Forensik",                            "type": "BPJS",     "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 15, "mgmt_struktural": 9,  "mgmt_administrasi": 6,  "farmasi": 0},
    27: {"info": "Instalasi Forensik - Toxikologi Jenazah",                              "type": "BPJS",     "dr_operator": 38, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 7,  "petugas_khusus": 30, "mgmt_struktural": 14, "mgmt_administrasi": 11, "farmasi": 0},
    28: {"info": "Instalasi Forensik - Radiologi Jenazah",                               "type": "BPJS",     "dr_operator": 56, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 2,  "petugas_khusus": 22, "mgmt_struktural": 10, "mgmt_administrasi": 10, "farmasi": 0},
    29: {"info": "Instalasi Forensik - Tindakan Lainnya",                                "type": "BPJS",     "dr_operator": 49, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 5,  "petugas_khusus": 16, "mgmt_struktural": 15, "mgmt_administrasi": 15, "farmasi": 0},
    30: {"info": "Mikrobiologi",                                                          "type": "BPJS",     "dr_operator": 34, "dr_spesialis": 2,  "dr_umum": 4,  "perawat": 7,  "petugas_khusus": 30, "mgmt_struktural": 12, "mgmt_administrasi": 11, "farmasi": 0},
    31: {"info": "Rawat Jalan",                                                           "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    32: {"info": "Rawat Inap - Dokter Spesialis",                                         "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 10, "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    33: {"info": "Rawat Inap - Dokter Umum",                                              "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 10, "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    34: {"info": "Rawat Inap - Asuhan Keperawatan",                                       "type": "NON BPJS", "dr_operator": 6,  "dr_spesialis": 0,  "dr_umum": 5,  "perawat": 75, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    35: {"info": "Tindakan Medis - di Poliklinik",                                        "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    36: {"info": "Tindakan Medis - di Ruangan",                                           "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    37: {"info": "Tindakan Medis - Keperawatan Medis di Ruangan/Poli",                    "type": "NON BPJS", "dr_operator": 10, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 75, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    38: {"info": "UGD - Tindakan Medis di IGD",                                           "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 30, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    39: {"info": "UGD - Tindakan Keperawatan/Medis Didelegasikan",                        "type": "NON BPJS", "dr_operator": 30, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 55, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    40: {"info": "Tindakan Medis OK Untuk Operator",                                      "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 15, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    41: {"info": "Tindakan Medis di OK untuk Anestesi",                                   "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 15, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    42: {"info": "Tindakan Medis VK untuk Operator",                                      "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    43: {"info": "Tindakan Medis di VK untuk Anestesi oleh Dokter Ahli Anestesi",         "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 15, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    44: {"info": "Partus ditolong Dokter",                                                 "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    45: {"info": "Partus Normal ditolong Bidan",                                           "type": "NON BPJS", "dr_operator": 10, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 75, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    46: {"info": "Partus Patologi ditolong Bidan",                                         "type": "NON BPJS", "dr_operator": 30, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 55, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    47: {"info": "Pemeriksaan Laboratorium Klinis",                                        "type": "NON BPJS", "dr_operator": 35, "dr_spesialis": 0,  "dr_umum": 3,  "perawat": 10, "petugas_khusus": 35, "mgmt_struktural": 17, "mgmt_administrasi": 0,  "farmasi": 0},
    48: {"info": "Pemeriksaan Laboratorium Patologis Anatomi",                             "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    49: {"info": "Pemeriksaan Radiologi - Rutin",                                          "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 20, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    50: {"info": "Pemeriksaan Radiologi - Canggih/Intervensi dari Spesialis",              "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    51: {"info": "Pemeriksaan Elektomedis - ECG Expertise",                                "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 25, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    52: {"info": "Pemeriksaan Elektomedis - ECG Non Expertise",                            "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 30, "mgmt_administrasi": 0,  "farmasi": 0},
    53: {"info": "Pemeriksaan Elektomedis - EEG",                                          "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 25, "petugas_khusus": 0,  "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    54: {"info": "Pemeriksaan Elektomedis - USG",                                          "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    55: {"info": "Farmasi",                                                                "type": "NON BPJS", "dr_operator": 5,  "dr_spesialis": 0,  "dr_umum": 1,  "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 19, "mgmt_administrasi": 0,  "farmasi": 55},
    56: {"info": "Rehabilitasi - Penanganan oleh Dokter Ahli Rehab Medik",                 "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 20, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    57: {"info": "Rehabilitasi - Penanganan oleh Tenaga Fisio Terapis",                    "type": "NON BPJS", "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 50, "mgmt_struktural": 20, "mgmt_administrasi": 0,  "farmasi": 0},
    58: {"info": "Rehabilitasi - Penanganan oleh Tenaga Terapi Wicara",                    "type": "NON BPJS", "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 50, "mgmt_struktural": 20, "mgmt_administrasi": 0,  "farmasi": 0},
    59: {"info": "Rehabilitasi - Penanganan oleh Tenaga Terapis Ocupasi",                  "type": "NON BPJS", "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 50, "mgmt_struktural": 20, "mgmt_administrasi": 0,  "farmasi": 0},
    60: {"info": "Rehabilitasi - Penanganan oleh Tenaga Psikolog",                         "type": "NON BPJS", "dr_operator": 20, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 50, "mgmt_struktural": 20, "mgmt_administrasi": 0,  "farmasi": 0},
    61: {"info": "Diklat Medis",                                                           "type": "NON BPJS", "dr_operator": 0,  "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 35, "petugas_khusus": 0,  "mgmt_struktural": 65, "mgmt_administrasi": 0,  "farmasi": 0},
    62: {"info": "Diklat Keperawatan",                                                     "type": "NON BPJS", "dr_operator": 25, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 50, "petugas_khusus": 0,  "mgmt_struktural": 25, "mgmt_administrasi": 0,  "farmasi": 0},
    63: {"info": "Pemeriksaan Dokter Medical Check Up",                                    "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    64: {"info": "Konsultasi Gizi",                                                        "type": "NON BPJS", "dr_operator": 0,  "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 10, "petugas_khusus": 0,  "mgmt_struktural": 90, "mgmt_administrasi": 0,  "farmasi": 0},
    65: {"info": "Hemodialisa",                                                            "type": "NON BPJS", "dr_operator": 35, "dr_spesialis": 0,  "dr_umum": 35, "perawat": 25, "petugas_khusus": 0,  "mgmt_struktural": 5,  "mgmt_administrasi": 0,  "farmasi": 0},
    66: {"info": "Pemulasaraan Jenazah",                                                   "type": "NON BPJS", "dr_operator": 0,  "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 0,  "mgmt_struktural": 0,  "mgmt_administrasi": 0,  "farmasi": 0},
    67: {"info": "Instalasi Forensik - Visum Dokter Spesialis (Non BPJS)",                 "type": "NON BPJS", "dr_operator": 60, "dr_spesialis": 0,  "dr_umum": 10, "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    68: {"info": "Instalasi Forensik - Visum Dokter Umum (Non BPJS)",                      "type": "NON BPJS", "dr_operator": 0,  "dr_spesialis": 10, "dr_umum": 60, "perawat": 20, "petugas_khusus": 0,  "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    69: {"info": "Instalasi Forensik - Hispatologi Forensik (Non BPJS)",                   "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    70: {"info": "Instalasi Forensik - Toxikologi Jenazah (Non BPJS)",                     "type": "NON BPJS", "dr_operator": 70, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 20, "mgmt_struktural": 10, "mgmt_administrasi": 0,  "farmasi": 0},
    71: {"info": "Instalasi Forensik - Radiologi Jenazah (Non BPJS)",                      "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 15, "petugas_khusus": 20, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    72: {"info": "Instalasi Forensik - Memandikan dan Mengkhafani",                        "type": "NON BPJS", "dr_operator": 10, "dr_spesialis": 0,  "dr_umum": 0,  "perawat": 0,  "petugas_khusus": 75, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    73: {"info": "Instalasi Forensik - Tindakan Lainnya (Non BPJS)",                       "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 2,  "dr_umum": 3,  "perawat": 0,  "petugas_khusus": 25, "mgmt_struktural": 20, "mgmt_administrasi": 0,  "farmasi": 0},
    74: {"info": "Bank Darah (BDRS)",                                                      "type": "NON BPJS", "dr_operator": 50, "dr_spesialis": 0,  "dr_umum": 5,  "perawat": 10, "petugas_khusus": 20, "mgmt_struktural": 15, "mgmt_administrasi": 0,  "farmasi": 0},
    75: {"info": "Mikrobiologi (Non BPJS)",                                                "type": "NON BPJS", "dr_operator": 35, "dr_spesialis": 0,  "dr_umum": 3,  "perawat": 10, "petugas_khusus": 35, "mgmt_struktural": 17, "mgmt_administrasi": 0,  "farmasi": 0},
}

# ── Fungsi Kalkulasi Inti ────────────────────────────────────────

def _hitung_jaspel_bpjs(total_billing, klaim_cbg, jenis_rawat, jaspel_naik_kelas=0.0, pembayaran=None):
    tarif            = TARIF_BPJS.get(jenis_rawat, 0.35)
    jasa_pelayanan   = klaim_cbg * tarif
    selisih_cbg      = klaim_cbg - total_billing
    jaspel_selisih   = selisih_cbg * TARIF_SELISIH if selisih_cbg > 0 else 0.0
    jaspel_total     = jasa_pelayanan + jaspel_selisih + jaspel_naik_kelas
    bayar            = pembayaran if pembayaran is not None else total_billing
    pct_bayar        = (bayar / total_billing * 100) if total_billing > 0 else 100.0
    jaspel_final     = jaspel_total * (pct_bayar / 100)
    return {
        "total_billing": round(total_billing, 2), "klaim_cbg": round(klaim_cbg, 2),
        "jenis_rawat": jenis_rawat, "tarif_pct": tarif * 100,
        "jasa_pelayanan": round(jasa_pelayanan, 2), "selisih_cbg": round(selisih_cbg, 2),
        "jaspel_selisih": round(jaspel_selisih, 2), "jaspel_naik_kelas": round(jaspel_naik_kelas, 2),
        "jaspel_total": round(jaspel_total, 2), "pembayaran_pct": round(pct_bayar, 2),
        "jaspel_final": round(jaspel_final, 2),
    }

def _hitung_jaspel_non_bpjs(jumlah, tipe_transaksi, id_jaspel):
    basis = jumlah * TARIF_BARANG if tipe_transaksi in ("barang", "paket_bhp") else jumlah
    master = MASTER_JASPEL.get(id_jaspel, MASTER_JASPEL[0])
    hasil = {"basis_jaspel": round(basis, 2)}
    for k in KOLOM_PENERIMA:
        hasil[k] = round(basis * master.get(k, 0) / 100, 2)
    return hasil

def _audit_baris_bpjs(row):
    try:
        res = _hitung_jaspel_bpjs(
            float(row.get("total_billing", 0)), float(row.get("klaim_cbg", 0)),
            str(row.get("jenis_rawat", "Rawat Jalan (Lainnya)")),
            float(row.get("jaspel_naik_kelas", 0)), row.get("pembayaran", None)
        )
        sistem  = float(row.get("jaspel_final_sistem", 0))
        selisih = round(res["jaspel_final"] - sistem, 2)
        return pd.Series({
            "audit_jasa_pelayanan": res["jasa_pelayanan"], "audit_selisih_cbg": res["selisih_cbg"],
            "audit_jaspel_selisih": res["jaspel_selisih"], "audit_jaspel_total": res["jaspel_total"],
            "audit_pembayaran_pct": res["pembayaran_pct"], "audit_jaspel_final": res["jaspel_final"],
            "sistem_jaspel_final": sistem, "selisih_audit_vs_sistem": selisih,
            "status": "✅ OK" if abs(selisih) < 1 else "⚠️ SELISIH",
        })
    except Exception as e:
        return pd.Series({"status": f"❌ Error: {e}"})

def _audit_baris_non_bpjs(row):
    try:
        res = _hitung_jaspel_non_bpjs(
            float(row.get("jumlah", 0)),
            str(row.get("tipe_transaksi", "jasa")).lower(),
            int(row.get("id_jaspel", 0))
        )
        selisih_map = {}
        for k in KOLOM_PENERIMA:
            selisih_map[f"selisih_{k}"] = round(res.get(k, 0) - float(row.get(f"sistem_{k}", 0)), 2)
        total_sel = sum(abs(v) for v in selisih_map.values())
        result = {"audit_basis_jaspel": res["basis_jaspel"]}
        result.update({f"audit_{k}": res.get(k, 0) for k in KOLOM_PENERIMA})
        result.update(selisih_map)
        result["total_selisih_absolut"] = round(total_sel, 2)
        result["status"] = "✅ OK" if total_sel < 1 else "⚠️ SELISIH"
        return pd.Series(result)
    except Exception as e:
        return pd.Series({"status": f"❌ Error: {e}"})

def _buat_template_csv(cols):
    df = pd.DataFrame(columns=cols)
    for i in range(3):
        df.loc[i] = ["" for _ in cols]
    return df.to_csv(index=False)

def _ringkasan_audit(df_hasil):
    total   = len(df_hasil)
    ok      = (df_hasil["status"] == "✅ OK").sum()
    sel     = (df_hasil["status"] == "⚠️ SELISIH").sum()
    err     = df_hasil["status"].str.startswith("❌").sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Baris", total)
    c2.metric("✅ OK",       ok,  delta=f"{ok/total*100:.1f}%" if total else "0%")
    c3.metric("⚠️ Selisih", sel, delta=f"{sel/total*100:.1f}%" if total else "0%")
    c4.metric("❌ Error",    err)
    if "selisih_audit_vs_sistem" in df_hasil.columns:
        st.info(f"Total selisih absolut: **Rp {df_hasil['selisih_audit_vs_sistem'].abs().sum():,.2f}**")

def _dl_excel(df, nama):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Hasil Audit")
    st.download_button("⬇️ Download Hasil Audit (.xlsx)", buf.getvalue(), nama,
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Sub-tab: Audit BPJS ─────────────────────────────────────────

def _subtab_audit_bpjs():
    TMPL_BPJS = ["no_sep","nama_rm","asuransi","jenis_rawat","total_billing",
                 "klaim_cbg","jaspel_naik_kelas","pembayaran","jaspel_final_sistem"]
    st.markdown("##### 🏥 Audit Jaspel BPJS")
    st.caption("Upload CSV tagihan BPJS → sistem hitung ulang & bandingkan dengan nilai di ICHA.")
    with st.expander("📋 Format kolom CSV"):
        st.markdown("""
| Kolom | Keterangan |
|---|---|
| `no_sep` | Nomor SEP |
| `jenis_rawat` | Rawat Jalan (Lainnya) / Rawat Inap / IGD / Rawat Jalan Hemodialisa / Rawat Jalan Rehabilitasi Medik |
| `total_billing` | Total tagihan (Rp) |
| `klaim_cbg` | Nilai INA CBGs disetujui (Rp) |
| `jaspel_naik_kelas` | Jaspel naik kelas (Rp) |
| `pembayaran` | Pembayaran aktual (kosong = sama billing) |
| `jaspel_final_sistem` | Nilai Jaspel Final dari ICHA (Rp) |
        """)
        st.download_button("⬇️ Template CSV BPJS", _buat_template_csv(TMPL_BPJS),
                           "template_audit_bpjs.csv", "text/csv")
    up = st.file_uploader("Upload CSV BPJS", type=["csv"], key="aud_bpjs")
    if up:
        try:
            df = pd.read_csv(up)
            st.success(f"✅ {len(df):,} baris terbaca")
            missing = [c for c in ["total_billing","klaim_cbg","jenis_rawat","jaspel_final_sistem"] if c not in df.columns]
            if missing:
                st.error(f"Kolom wajib tidak ada: {missing}"); return
            with st.expander("👁️ Preview (10 baris)"):
                st.dataframe(df.head(10), use_container_width=True)
            if st.button("🔍 Jalankan Audit BPJS", type="primary", key="btn_aud_bpjs"):
                with st.spinner("Menghitung..."):
                    df_h = pd.concat([df.reset_index(drop=True), df.apply(_audit_baris_bpjs, axis=1)], axis=1)
                st.markdown("---")
                _ringkasan_audit(df_h)
                bad = df_h[df_h["status"] != "✅ OK"]
                if not bad.empty:
                    st.markdown(f"**⚠️ {len(bad)} baris bermasalah:**")
                    st.dataframe(bad, use_container_width=True)
                else:
                    st.success("🎉 Semua baris sesuai!")
                with st.expander("📄 Seluruh hasil"):
                    st.dataframe(df_h, use_container_width=True)
                _dl_excel(df_h, "hasil_audit_bpjs.xlsx")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# ── Sub-tab: Audit Non BPJS ─────────────────────────────────────

def _subtab_audit_non_bpjs():
    TMPL_NON = ["id_tagihan","nama_rm","nama_item","tipe_transaksi","id_jaspel","jumlah",
                "sistem_dr_operator","sistem_dr_spesialis","sistem_dr_umum","sistem_perawat",
                "sistem_petugas_khusus","sistem_mgmt_struktural","sistem_mgmt_administrasi","sistem_farmasi"]
    st.markdown("##### 🏨 Audit Jaspel Non BPJS")
    st.caption("Upload CSV transaksi Non BPJS → cek proporsi per penerima vs nilai sistem.")
    with st.expander("📋 Format kolom CSV"):
        st.markdown("""
| Kolom | Keterangan |
|---|---|
| `tipe_transaksi` | `barang` / `paket_bhp` / `jasa` / `rikjang` |
| `id_jaspel` | ID dari Master Jaspel (0–75) |
| `jumlah` | Nilai transaksi (Rp) |
| `sistem_dr_operator` … | Nilai dari ICHA per penerima (Rp) |
        """)
        st.download_button("⬇️ Template CSV Non BPJS", _buat_template_csv(TMPL_NON),
                           "template_audit_non_bpjs.csv", "text/csv")
    up = st.file_uploader("Upload CSV Non BPJS", type=["csv"], key="aud_nonbpjs")
    if up:
        try:
            df = pd.read_csv(up)
            st.success(f"✅ {len(df):,} baris terbaca")
            missing = [c for c in ["jumlah","tipe_transaksi","id_jaspel"] if c not in df.columns]
            if missing:
                st.error(f"Kolom wajib tidak ada: {missing}"); return
            with st.expander("👁️ Preview (10 baris)"):
                st.dataframe(df.head(10), use_container_width=True)
            if st.button("🔍 Jalankan Audit Non BPJS", type="primary", key="btn_aud_nbpjs"):
                with st.spinner("Menghitung..."):
                    df_h = pd.concat([df.reset_index(drop=True), df.apply(_audit_baris_non_bpjs, axis=1)], axis=1)
                st.markdown("---")
                _ringkasan_audit(df_h)
                bad = df_h[df_h["status"] != "✅ OK"]
                if not bad.empty:
                    st.markdown(f"**⚠️ {len(bad)} baris bermasalah:**")
                    st.dataframe(bad, use_container_width=True)
                else:
                    st.success("🎉 Semua baris sesuai!")
                with st.expander("📄 Seluruh hasil"):
                    st.dataframe(df_h, use_container_width=True)
                _dl_excel(df_h, "hasil_audit_non_bpjs.xlsx")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# ── Sub-tab: Simulasi Manual ─────────────────────────────────────

def _subtab_simulasi():
    st.markdown("##### 🧮 Simulasi Perhitungan Manual")
    mode = st.radio("Golongan Penjamin:", ["BPJS", "Non BPJS"], horizontal=True, key="sim_mode")
    if mode == "BPJS":
        c1, c2 = st.columns(2)
        with c1:
            tb  = st.number_input("Total Billing (Rp)", min_value=0.0, value=198100.0, step=1000.0, format="%.2f", key="sim_tb")
            cbg = st.number_input("Klaim INA CBGs (Rp)", min_value=0.0, value=198100.0, step=1000.0, format="%.2f", key="sim_cbg")
            nk  = st.number_input("Jaspel Naik Kelas (Rp)", min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="sim_nk")
        with c2:
            jr  = st.selectbox("Jenis Rawat:", list(TARIF_BPJS.keys()), key="sim_jr")
            pm  = st.number_input("Pembayaran Aktual (0 = sama billing)", min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="sim_pm")
            sv  = st.number_input("Jaspel Final Sistem ICHA (Rp):", min_value=0.0, value=0.0, step=100.0, format="%.2f", key="sim_sv")
        if st.button("Hitung ▶", type="primary", key="sim_bpjs_btn"):
            h = _hitung_jaspel_bpjs(tb, cbg, jr, nk, pm if pm > 0 else None)
            c1, c2, c3 = st.columns(3)
            c1.metric("Jasa Pelayanan",   f"Rp {h['jasa_pelayanan']:,.2f}")
            c1.metric("Tarif",            f"{h['tarif_pct']}%")
            c2.metric("Selisih CBG",      f"Rp {h['selisih_cbg']:,.2f}")
            c2.metric("Jaspel Selisih",   f"Rp {h['jaspel_selisih']:,.2f}")
            c3.metric("Jaspel Total",     f"Rp {h['jaspel_total']:,.2f}")
            c3.metric("Pembayaran %",     f"{h['pembayaran_pct']}%")
            st.divider()
            ca, cb, cc = st.columns(3)
            sel = h["jaspel_final"] - sv
            ca.metric("✅ Jaspel Final (Audit)",   f"Rp {h['jaspel_final']:,.2f}")
            cb.metric("📋 Jaspel Final (Sistem)",  f"Rp {sv:,.2f}")
            cc.metric("Selisih", f"Rp {sel:,.2f}",
                      delta="OK ✅" if abs(sel) < 1 else "BERBEDA ⚠️",
                      delta_color="normal" if abs(sel) < 1 else "inverse")
            with st.expander("🔢 Rumus Step-by-Step"):
                st.code(f"""Tarif            = {h['tarif_pct']}%  ({jr})
Jasa Pelayanan   = {cbg:,.2f} × {h['tarif_pct']/100} = {h['jasa_pelayanan']:,.2f}
Selisih CBG      = {cbg:,.2f} - {tb:,.2f} = {h['selisih_cbg']:,.2f}
Jaspel Selisih   = {h['selisih_cbg']:,.2f} × 5% = {h['jaspel_selisih']:,.2f}
Jaspel Total     = {h['jasa_pelayanan']:,.2f} + {h['jaspel_selisih']:,.2f} + {nk:,.2f} = {h['jaspel_total']:,.2f}
Jaspel Final     = {h['jaspel_total']:,.2f} × {h['pembayaran_pct']/100} = {h['jaspel_final']:,.2f}""", language="text")
    else:
        c1, c2 = st.columns(2)
        with c1:
            tt = st.selectbox("Tipe Transaksi:", ["jasa","rikjang","barang","paket_bhp"], key="sim_tt")
            ij = st.selectbox("Jenis Jaspel (ID):", list(MASTER_JASPEL.keys()),
                              format_func=lambda x: f"ID {x} – {MASTER_JASPEL[x]['info']} ({MASTER_JASPEL[x]['type']})",
                              key="sim_ij")
        with c2:
            jml = st.number_input("Jumlah/Harga Beli (Rp)", min_value=0.0, value=45000.0, step=1000.0, format="%.2f", key="sim_jml")
        if st.button("Hitung ▶", type="primary", key="sim_nbpjs_btn"):
            h = _hitung_jaspel_non_bpjs(jml, tt, ij)
            m = MASTER_JASPEL[ij]
            st.markdown(f"**{m['info']}** | Basis Jaspel: **Rp {h['basis_jaspel']:,.2f}**")
            LBL = {"dr_operator":"dr. Operator","dr_spesialis":"dr. Spesialis","dr_umum":"dr. Umum",
                   "perawat":"Perawat","petugas_khusus":"Petugas Khusus","mgmt_struktural":"Mgmt Struktural",
                   "mgmt_administrasi":"Mgmt Administrasi","farmasi":"Farmasi"}
            rows = [{"Penerima": LBL[k], "% Tarif": m.get(k,0), "Nilai Jaspel (Rp)": h.get(k,0)} for k in KOLOM_PENERIMA]
            df_t = pd.DataFrame(rows)
            df_t.loc[len(df_t)] = {"Penerima":"TOTAL",
                                    "% Tarif": sum(m.get(k,0) for k in KOLOM_PENERIMA),
                                    "Nilai Jaspel (Rp)": sum(h.get(k,0) for k in KOLOM_PENERIMA)}
            st.dataframe(df_t.style.format({"Nilai Jaspel (Rp)": "Rp {:,.2f}", "% Tarif": "{:.0f}%"}),
                         use_container_width=True, hide_index=True)
            with st.expander("🔢 Rumus Step-by-Step"):
                basis_ket = "× 3.85%" if tt in ("barang","paket_bhp") else "(harga beli langsung)"
                lines = "\n".join(f"{LBL[k]:25s}: {h['basis_jaspel']:,.2f} × {m.get(k,0)}% = {h.get(k,0):,.2f}" for k in KOLOM_PENERIMA)
                st.code(f"Basis Jaspel = {jml:,.2f} {basis_ket} = {h['basis_jaspel']:,.2f}\n\n{lines}", language="text")

# ── Sub-tab: Master Jaspel ───────────────────────────────────────

def _subtab_master():
    st.markdown("##### 📚 Referensi Master Persentase Jaspel")
    st.caption("75 ID Jaspel sesuai dokumen SIMRS ICHA.")
    tipe_f = st.multiselect("Filter Tipe:", ["BPJS","NON BPJS","-"], default=["BPJS","NON BPJS"], key="mst_tipe")
    kw     = st.text_input("Cari kata kunci:", "", key="mst_kw")
    rows = []
    for id_, m in MASTER_JASPEL.items():
        if m["type"] not in tipe_f: continue
        if kw and kw.lower() not in m["info"].lower(): continue
        row = {"ID": id_, "Tipe": m["type"], "Info": m["info"]}
        row.update({k: m.get(k,0) for k in KOLOM_PENERIMA})
        rows.append(row)
    df_m = pd.DataFrame(rows)
    st.dataframe(df_m, use_container_width=True, hide_index=True)
    st.caption(f"Menampilkan {len(df_m)} dari {len(MASTER_JASPEL)} ID")

# ═══════════════════════════════════════════════════════════════════
# LAYOUT UTAMA — 2 TAB
# ═══════════════════════════════════════════════════════════════════

tab_fpk, tab_audit = st.tabs(["⚡ FPK Converter", "🔍 Audit Jaspel"])

# ── TAB 1: FPK CONVERTER (kode asli, tidak diubah) ─────────────
with tab_fpk:
    st.markdown("""
        <div class="app-header">
            <div class="badge">⚡ Converter Tools</div>
            <h1>FPK <span>Converter</span></h1>
            <p>Upload PDF FPK, konversi otomatis ke CSV siap pakai</p>
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload PDF FPK di sini",
        type=['pdf'],
        help="Format yang diterima: .pdf"
    )

    if uploaded_file:
        if st.button("⚡ Proses Sekarang"):
            with st.spinner("Lagi dibaca isinya, tunggu bentar..."):
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
                    st.success(f"✅ Berhasil diproses!")

                except Exception as e:
                    st.error(f"Gagal memproses: {e}")

    if 'final_df' in st.session_state:
        st.markdown(f"""
            <div class="file-badge">
                📄 {st.session_state.auto_filename}
            </div>
        """, unsafe_allow_html=True)

        total_rp = f"Rp {st.session_state.final_total:,.0f}".replace(",", ".")

        st.markdown(f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Jumlah Data</div>
                    <div class="stat-value">{st.session_state.final_count}</div>
                    <div class="stat-sub">SEP records</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Nominal</div>
                    <div class="stat-value green">{total_rp}</div>
                    <div class="stat-sub">total disetujui</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.subheader("Preview Data")
        df_preview = st.session_state.final_df.copy()
        df_preview.insert(0, 'No', range(1, 1 + len(df_preview)))
        st.dataframe(
            df_preview,
            use_container_width=True,
            height=320,
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width=50),
                "Disetujui": st.column_config.NumberColumn("Nominal Cair", format="Rp %d")
            }
        )

        st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            csv_data = st.session_state.final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇ Download CSV",
                data=csv_data,
                file_name=st.session_state.auto_filename,
                mime="text/csv"
            )
        with col2:
            with st.container():
                st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
                if st.button("Reset"):
                    for key in ['final_df', 'final_total', 'final_count', 'auto_filename']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 2: AUDIT JASPEL ─────────────────────────────────────────
with tab_audit:
    st.markdown("""
        <div class="app-header" style="padding: 1.5rem 2rem 1rem;">
            <div class="badge">🔍 Audit Jaspel</div>
            <h1>Audit <span>Jaspel</span></h1>
            <p>Verifikasi perhitungan Jasa Pelayanan berdasarkan Dokumentasi Modul Jaspel SIMRS ICHA</p>
        </div>
    """, unsafe_allow_html=True)

    st1, st2, st3, st4 = st.tabs([
        "🏥 Audit BPJS",
        "🏨 Audit Non BPJS",
        "🧮 Simulasi Manual",
        "📚 Master Jaspel",
    ])
    with st1: _subtab_audit_bpjs()
    with st2: _subtab_audit_non_bpjs()
    with st3: _subtab_simulasi()
    with st4: _subtab_master()
