import streamlit as st
import pandas as pd
import io

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FPK Converter + Audit Jaspel ICHA",
    page_icon="🏥",
    layout="wide",
)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("## 🔐 Login")
    pin = st.text_input("Masukkan PIN:", type="password")
    if st.button("Login"):
        if pin == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("PIN salah!")
    st.stop()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_rp(n):
    if n is None:
        return "—"
    return f"Rp {n:,.0f}".replace(",", ".")

def load_csv(uploaded_file):
    """Load CSV dan normalize kolom No.SEP + Disetujui"""
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        return None, f"Error membaca file: {e}"

    # Normalize nama kolom
    df.columns = df.columns.str.strip()

    # Cari kolom No.SEP
    sep_col = None
    for c in df.columns:
        if "SEP" in c.upper() or "NO" in c.upper():
            sep_col = c
            break

    # Cari kolom Disetujui
    dis_col = None
    for c in df.columns:
        if "DISETUJUI" in c.upper() or "SETUJU" in c.upper():
            dis_col = c
            break

    if sep_col is None or dis_col is None:
        return None, f"Kolom tidak ditemukan. Kolom yang ada: {list(df.columns)}\n\nCSV harus punya kolom: No.SEP dan Disetujui"

    df = df[[sep_col, dis_col]].copy()
    df.columns = ["No.SEP", "Disetujui"]
    df["Disetujui"] = pd.to_numeric(df["Disetujui"].astype(str).str.replace(",", "").str.replace(".", ""), errors="coerce").fillna(0).astype(int)
    df = df[df["Disetujui"] > 0].reset_index(drop=True)

    return df, None

# ─── TARIF BPJS ───────────────────────────────────────────────────────────────
TARIF = {
    "Rawat Inap (RITL)": 0.30,
    "Rawat Jalan (RJTL)": 0.35,
    "Rawat Jalan Rehabilitasi Medik": 0.45,
    "Rawat Jalan Hemodialisa": 0.30,
    "IGD": 0.35,
}

# ─── KANTONG BESAR ────────────────────────────────────────────────────────────
KANTONG_RI = {
    "dr. Operator & dr. Spesialis": 34.3,
    "dr. Umum": 6.1,
    "Perawat": 25.5,
    "Management Struktural": 14.8,
    "Petugas Khusus": 8.9,
    "Farmasi": 1.6,
    "Management Administrasi": 8.8,
}
KANTONG_RJ = {
    "dr. Operator & dr. Spesialis": 50.4,
    "dr. Umum": 2.0,
    "Perawat": 15.0,
    "Management Struktural": 11.0,
    "Petugas Khusus": 9.0,
    "Farmasi": 4.0,
    "Management Administrasi": 8.6,
}

def hitung_jaspel(total_cbg, tarif_pct, total_billing, naik_kelas=0):
    jasa_pelayanan = total_cbg * tarif_pct
    selisih_cbg = total_cbg - total_billing
    jaspel_selisih = max(0, selisih_cbg) * 0.05
    jaspel_total = jasa_pelayanan + jaspel_selisih + naik_kelas
    jaspel_final = jaspel_total  # Pembayaran % = 100% diasumsikan
    return {
        "jasa_pelayanan": jasa_pelayanan,
        "selisih_cbg": selisih_cbg,
        "jaspel_selisih": jaspel_selisih,
        "naik_kelas": naik_kelas,
        "jaspel_total": jaspel_total,
        "jaspel_final": jaspel_final,
    }

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["⚡ FPK Converter", "🔍 Audit Jaspel"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FPK CONVERTER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("## ⚡ FPK Converter")
    st.markdown("Upload PDF FPK → ekstrak **No.SEP** + **Disetujui** → download CSV")

    st.info("💡 Fitur konversi PDF membutuhkan file PDF FPK dari BPJS Kesehatan (format Rincian Data Hasil Verifikasi)")

    uploaded_pdf = st.file_uploader("Upload PDF FPK", type=["pdf"], key="fpk_pdf")

    if uploaded_pdf:
        try:
            import pdfplumber
            rows = []
            with pdfplumber.open(uploaded_pdf) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row and len(row) >= 5:
                                try:
                                    no = row[0]
                                    if no and str(no).strip().isdigit():
                                        sep = str(row[1]).strip()
                                        disetujui_raw = str(row[4]).strip().replace(",", "").replace(".", "")
                                        if sep.startswith("1028") and disetujui_raw.isdigit():
                                            rows.append({"No.SEP": sep, "Disetujui": int(disetujui_raw)})
                                except:
                                    pass

            if rows:
                df_out = pd.DataFrame(rows)
                st.success(f"✅ {len(df_out)} SEP berhasil diekstrak")
                st.dataframe(df_out.head(20), use_container_width=True)

                csv_bytes = df_out.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=f"FPK_{uploaded_pdf.name.replace('.pdf','')}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Tidak ada data SEP yang ditemukan di PDF ini.")
        except ImportError:
            st.error("Library pdfplumber belum tersedia. Install dengan: pip install pdfplumber")
        except Exception as e:
            st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AUDIT JASPEL
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 🔍 Audit Jaspel")
    st.markdown("Verifikasi perhitungan Jasa Pelayanan berdasarkan Dokumentasi Modul Jaspel SIMRS ICHA")

    sub1, sub2, sub3, sub4 = st.tabs(["🏥 Audit BPJS", "🏪 Audit Non BPJS", "🧮 Simulasi Manual", "📋 Master Jaspel"])

    # ─────────────────────────────────────────────────────────────────────────
    # SUB-TAB 1: AUDIT BPJS
    # ─────────────────────────────────────────────────────────────────────────
    with sub1:
        st.markdown("### 🏥 Audit Jaspel BPJS")
        st.caption("Upload CSV tagihan BPJS → sistem hitung ulang & bandingkan dengan nilai di ICHA.")

        col_ri, col_rj = st.columns(2)

        # ── RI ──────────────────────────────────────────────
        with col_ri:
            st.markdown("#### 🏥 Rawat Inap (RI)")

            # Upload CSV RI
            csv_ri = st.file_uploader(
                "Upload CSV BPJS RI",
                type=["csv"],
                key="csv_ri",
                help="Format: No.SEP, Disetujui"
            )

            df_ri = None
            if csv_ri:
                df_ri, err_ri = load_csv(csv_ri)
                if err_ri:
                    st.error(f"❌ {err_ri}")
                else:
                    total_cbg_ri = df_ri["Disetujui"].sum()
                    st.success(f"✅ {len(df_ri):,} SEP | Total CBG: {fmt_rp(total_cbg_ri)}")
            else:
                st.info("👆 Upload CSV RI (kolom: No.SEP, Disetujui)")

            # Parameter RI
            jenis_ri = st.selectbox("Jenis Rawat RI", list(TARIF.keys()), index=0, key="jenis_ri")
            tarif_ri = TARIF[jenis_ri]

            billing_ri = st.number_input(
                "Total Biaya Riil RS / Total Billing RI (Rp)",
                min_value=0,
                value=3490013065,
                step=1000000,
                key="billing_ri",
                help="Dari PDF Rekap FPK RI: 3,490,013,065"
            )
            st.caption(f"📄 Dari PDF Jan 2026: Rp 3.490.013.065")

            naik_kelas_ri = st.number_input("Jaspel Naik Kelas RI (Rp)", min_value=0, value=0, step=100000, key="naik_ri")
            icha_ri = st.number_input("Nilai Jaspel di ICHA RI (Rp) — untuk perbandingan", min_value=0, value=0, step=100000, key="icha_ri")

        # ── RJ ──────────────────────────────────────────────
        with col_rj:
            st.markdown("#### 🏪 Rawat Jalan (RJ)")

            csv_rj = st.file_uploader(
                "Upload CSV BPJS RJ",
                type=["csv"],
                key="csv_rj",
                help="Format: No.SEP, Disetujui"
            )

            df_rj = None
            if csv_rj:
                df_rj, err_rj = load_csv(csv_rj)
                if err_rj:
                    st.error(f"❌ {err_rj}")
                else:
                    total_cbg_rj = df_rj["Disetujui"].sum()
                    st.success(f"✅ {len(df_rj):,} SEP | Total CBG: {fmt_rp(total_cbg_rj)}")
            else:
                st.info("👆 Upload CSV RJ (kolom: No.SEP, Disetujui)")

            jenis_rj = st.selectbox("Jenis Rawat RJ", list(TARIF.keys()), index=1, key="jenis_rj")
            tarif_rj = TARIF[jenis_rj]

            billing_rj = st.number_input(
                "Total Biaya Riil RS / Total Billing RJ (Rp)",
                min_value=0,
                value=0,
                step=1000000,
                key="billing_rj",
                help="Isi dari Rekap FPK RJ"
            )

            naik_kelas_rj = st.number_input("Jaspel Naik Kelas RJ (Rp)", min_value=0, value=0, step=100000, key="naik_rj")
            icha_rj = st.number_input("Nilai Jaspel di ICHA RJ (Rp) — untuk perbandingan", min_value=0, value=0, step=100000, key="icha_rj")

        # ── HASIL ─────────────────────────────────────────────
        st.markdown("---")
        hitung = st.button("🧮 Hitung Jaspel BPJS", type="primary", use_container_width=True)

        if hitung or df_ri is not None or df_rj is not None:
            if df_ri is None and df_rj is None:
                st.warning("⚠️ Upload minimal satu CSV (RI atau RJ) terlebih dahulu.")
            else:
                hasil_ri = None
                hasil_rj = None

                if df_ri is not None:
                    total_cbg_ri = df_ri["Disetujui"].sum()
                    hasil_ri = hitung_jaspel(total_cbg_ri, tarif_ri, billing_ri, naik_kelas_ri)

                if df_rj is not None:
                    total_cbg_rj = df_rj["Disetujui"].sum()
                    hasil_rj = hitung_jaspel(total_cbg_rj, tarif_rj, billing_rj, naik_kelas_rj)

                # ── SUMMARY CARDS ──
                total_jaspel_final = (hasil_ri["jaspel_final"] if hasil_ri else 0) + (hasil_rj["jaspel_final"] if hasil_rj else 0)
                total_icha = (icha_ri if icha_ri > 0 else 0) + (icha_rj if icha_rj > 0 else 0)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("📋 SEP RI", f"{len(df_ri):,}" if df_ri is not None else "—")
                with c2:
                    st.metric("📋 SEP RJ", f"{len(df_rj):,}" if df_rj is not None else "—")
                with c3:
                    st.metric("💰 Total Jaspel Final (Hitung)", fmt_rp(total_jaspel_final))
                with c4:
                    if total_icha > 0:
                        selisih = total_jaspel_final - total_icha
                        st.metric("⚖️ Selisih vs ICHA", fmt_rp(selisih), delta=f"{selisih/total_icha*100:.2f}%" if total_icha else None)
                    else:
                        st.metric("📊 ICHA (belum diisi)", "—")

                # ── DETAIL RI ──
                if hasil_ri:
                    st.markdown("#### 📊 Detail Perhitungan — Rawat Inap (RI)")
                    total_cbg_ri = df_ri["Disetujui"].sum()

                    col_a, col_b = st.columns(2)
                    with col_a:
                        data_ri = {
                            "Komponen": [
                                "Jumlah SEP",
                                f"Total Klaim INA CBGs",
                                f"Total Biaya Riil RS",
                                f"Tarif BPJS ({jenis_ri})",
                                "Jasa Pelayanan (CBG × Tarif)",
                                "Selisih INA CBGs (CBG − Billing)",
                                "Jaspel Selisih (× 5%)",
                                "Jaspel Naik Kelas",
                                "🟣 Jaspel Total",
                                "✅ Jaspel Final",
                            ],
                            "Nilai": [
                                f"{len(df_ri):,} SEP",
                                fmt_rp(total_cbg_ri),
                                fmt_rp(billing_ri),
                                f"{tarif_ri*100:.0f}%",
                                fmt_rp(hasil_ri["jasa_pelayanan"]),
                                fmt_rp(hasil_ri["selisih_cbg"]),
                                fmt_rp(hasil_ri["jaspel_selisih"]),
                                fmt_rp(hasil_ri["naik_kelas"]),
                                fmt_rp(hasil_ri["jaspel_total"]),
                                fmt_rp(hasil_ri["jaspel_final"]),
                            ]
                        }
                        st.dataframe(pd.DataFrame(data_ri), use_container_width=True, hide_index=True)

                        if hasil_ri["selisih_cbg"] <= 0:
                            st.info(f"ℹ️ Selisih CBG = {fmt_rp(hasil_ri['selisih_cbg'])} (NEGATIF) → Jaspel Selisih = Rp 0")
                        else:
                            st.success(f"✅ Selisih CBG POSITIF = {fmt_rp(hasil_ri['selisih_cbg'])} → Jaspel Selisih = {fmt_rp(hasil_ri['jaspel_selisih'])}")

                    with col_b:
                        if icha_ri > 0:
                            selisih_ri = hasil_ri["jaspel_final"] - icha_ri
                            st.markdown("**⚖️ Perbandingan vs ICHA**")
                            st.dataframe(pd.DataFrame({
                                "": ["Hitung Manual", "Sistem ICHA", "Selisih"],
                                "Nilai": [fmt_rp(hasil_ri["jaspel_final"]), fmt_rp(icha_ri), fmt_rp(selisih_ri)]
                            }), use_container_width=True, hide_index=True)
                            if abs(selisih_ri) < 1000:
                                st.success("✅ COCOK dengan ICHA!")
                            else:
                                st.warning(f"⚠️ Selisih {fmt_rp(selisih_ri)} — periksa data Non-BPJS, IGD, atau naik kelas")

                        # Kantong Besar Estimasi RI
                        st.markdown("**📊 Estimasi Kantong Besar RI**")
                        kb_data = []
                        for nama, pct in KANTONG_RI.items():
                            kb_data.append({"Jenis": nama, "%": f"{pct:.1f}%", "Estimasi": fmt_rp(hasil_ri["jaspel_final"] * pct / 100)})
                        st.dataframe(pd.DataFrame(kb_data), use_container_width=True, hide_index=True)
                        st.caption("*Estimasi distribusi berdasarkan rata-rata RS umum. Nilai aktual dari SIMRS ICHA.")

                # ── DETAIL RJ ──
                if hasil_rj:
                    st.markdown("#### 📊 Detail Perhitungan — Rawat Jalan (RJ)")
                    total_cbg_rj = df_rj["Disetujui"].sum()

                    col_c, col_d = st.columns(2)
                    with col_c:
                        data_rj = {
                            "Komponen": [
                                "Jumlah SEP",
                                "Total Klaim INA CBGs",
                                "Total Biaya Riil RS",
                                f"Tarif BPJS ({jenis_rj})",
                                "Jasa Pelayanan (CBG × Tarif)",
                                "Selisih INA CBGs (CBG − Billing)",
                                "Jaspel Selisih (× 5%)",
                                "Jaspel Naik Kelas",
                                "🟣 Jaspel Total",
                                "✅ Jaspel Final",
                            ],
                            "Nilai": [
                                f"{len(df_rj):,} SEP",
                                fmt_rp(total_cbg_rj),
                                fmt_rp(billing_rj) if billing_rj > 0 else "Belum diisi",
                                f"{tarif_rj*100:.0f}%",
                                fmt_rp(hasil_rj["jasa_pelayanan"]),
                                fmt_rp(hasil_rj["selisih_cbg"]) if billing_rj > 0 else "—",
                                fmt_rp(hasil_rj["jaspel_selisih"]) if billing_rj > 0 else "—",
                                fmt_rp(hasil_rj["naik_kelas"]),
                                fmt_rp(hasil_rj["jaspel_total"]),
                                fmt_rp(hasil_rj["jaspel_final"]),
                            ]
                        }
                        st.dataframe(pd.DataFrame(data_rj), use_container_width=True, hide_index=True)

                        if billing_rj == 0:
                            st.info("ℹ️ Total Billing RJ belum diisi — Jaspel Selisih tidak dihitung. Isi dari PDF Rekap FPK RJ.")

                    with col_d:
                        if icha_rj > 0:
                            selisih_rj = hasil_rj["jaspel_final"] - icha_rj
                            st.markdown("**⚖️ Perbandingan vs ICHA**")
                            st.dataframe(pd.DataFrame({
                                "": ["Hitung Manual", "Sistem ICHA", "Selisih"],
                                "Nilai": [fmt_rp(hasil_rj["jaspel_final"]), fmt_rp(icha_rj), fmt_rp(selisih_rj)]
                            }), use_container_width=True, hide_index=True)

                        # Kantong Besar Estimasi RJ
                        st.markdown("**📊 Estimasi Kantong Besar RJ**")
                        kb_data_rj = []
                        for nama, pct in KANTONG_RJ.items():
                            kb_data_rj.append({"Jenis": nama, "%": f"{pct:.1f}%", "Estimasi": fmt_rp(hasil_rj["jaspel_final"] * pct / 100)})
                        st.dataframe(pd.DataFrame(kb_data_rj), use_container_width=True, hide_index=True)
                        st.caption("*Estimasi distribusi berdasarkan rata-rata RS umum. Nilai aktual dari SIMRS ICHA.")

                # ── REKAP GABUNGAN ──
                if hasil_ri and hasil_rj:
                    st.markdown("---")
                    st.markdown("#### 📊 Rekap Gabungan RI + RJ")
                    gabungan = pd.DataFrame({
                        "Jenis": ["Rawat Inap (RI)", "Rawat Jalan (RJ)", "TOTAL"],
                        "Jumlah SEP": [f"{len(df_ri):,}", f"{len(df_rj):,}", f"{len(df_ri)+len(df_rj):,}"],
                        "Total CBG": [fmt_rp(df_ri['Disetujui'].sum()), fmt_rp(df_rj['Disetujui'].sum()), fmt_rp(df_ri['Disetujui'].sum()+df_rj['Disetujui'].sum())],
                        "Tarif": [f"{tarif_ri*100:.0f}%", f"{tarif_rj*100:.0f}%", "—"],
                        "Jaspel Final": [fmt_rp(hasil_ri["jaspel_final"]), fmt_rp(hasil_rj["jaspel_final"]), fmt_rp(total_jaspel_final)],
                    })
                    st.dataframe(gabungan, use_container_width=True, hide_index=True)

                    if total_icha > 0:
                        selisih_total = total_jaspel_final - total_icha
                        col_x, col_y = st.columns(2)
                        with col_x:
                            st.metric("💰 Total Jaspel Hitung", fmt_rp(total_jaspel_final))
                        with col_y:
                            st.metric("🏥 Total ICHA", fmt_rp(total_icha), delta=fmt_rp(selisih_total))
                        if abs(selisih_total) > 0:
                            st.info(f"💡 Selisih {fmt_rp(selisih_total)} kemungkinan dari: Non-BPJS, IGD, naik kelas, atau tarif RJ khusus (Rehab Medik 45%, HD 30%)")

                # ── FORMULA LENGKAP ──
                with st.expander("📋 Rumus Perhitungan ICHA (klik untuk lihat)"):
                    st.code("""
BPJS — Formula SIMRS ICHA:

Tarif:
  Rawat Jalan Rehabilitasi Medik = 45%
  Rawat Jalan Hemodialisa        = 30%
  Rawat Jalan (lainnya)          = 35%
  Rawat Inap                     = 30%
  IGD                            = 35%

Jasa Pelayanan   = Klaim INA CBGs × Tarif
Selisih CBGs     = Klaim INA CBGs − Total Biaya Riil RS
Jaspel Selisih   = max(0, Selisih CBGs) × 5%
Jaspel Naik Kelas = dari pasien BPJS naik kelas (input manual)

Jaspel Total     = Jasa Pelayanan + Jaspel Selisih + Jaspel Naik Kelas
Pembayaran %     = (Pembayaran / Total Billing) × 100
Jaspel Final     = Jaspel Total × Pembayaran %
                    """, language="text")

                # ── DOWNLOAD HASIL ──
                if hasil_ri or hasil_rj:
                    rows_out = []
                    if hasil_ri:
                        rows_out.append({"Jenis": "Rawat Inap (RI)", "SEP": len(df_ri), "Total CBG": df_ri['Disetujui'].sum(),
                                         "Tarif": f"{tarif_ri*100:.0f}%", "Jasa Pelayanan": round(hasil_ri['jasa_pelayanan']),
                                         "Selisih CBG": round(hasil_ri['selisih_cbg']), "Jaspel Selisih": round(hasil_ri['jaspel_selisih']),
                                         "Naik Kelas": hasil_ri['naik_kelas'], "Jaspel Total": round(hasil_ri['jaspel_total']),
                                         "Jaspel Final": round(hasil_ri['jaspel_final'])})
                    if hasil_rj:
                        rows_out.append({"Jenis": "Rawat Jalan (RJ)", "SEP": len(df_rj), "Total CBG": df_rj['Disetujui'].sum(),
                                         "Tarif": f"{tarif_rj*100:.0f}%", "Jasa Pelayanan": round(hasil_rj['jasa_pelayanan']),
                                         "Selisih CBG": round(hasil_rj['selisih_cbg']), "Jaspel Selisih": round(hasil_rj['jaspel_selisih']),
                                         "Naik Kelas": hasil_rj['naik_kelas'], "Jaspel Total": round(hasil_rj['jaspel_total']),
                                         "Jaspel Final": round(hasil_rj['jaspel_final'])})
                    df_out = pd.DataFrame(rows_out)
                    csv_out = df_out.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Download Hasil Audit CSV", data=csv_out, file_name="hasil_audit_jaspel_bpjs.csv", mime="text/csv")

    # ─────────────────────────────────────────────────────────────────────────
    # SUB-TAB 2: AUDIT NON-BPJS
    # ─────────────────────────────────────────────────────────────────────────
    with sub2:
        st.markdown("### 🏪 Audit Jaspel Non BPJS")
        st.info("💡 Fitur Audit Non-BPJS menggunakan data transaksi dari SIMRS. Upload CSV transaksi Non-BPJS untuk menghitung Jaspel.")

        st.markdown("""
**Formula Non-BPJS (SIMRS ICHA):**
- **Barang/Paket BHP:** Basis = Jumlah × 3.85%
- **Jasa/Rikjang:** Basis = Harga Beli
- **Nilai per penerima:** Basis × (% dari Master Jaspel ID)
        """)

        csv_non_bpjs = st.file_uploader("Upload CSV Transaksi Non-BPJS", type=["csv"], key="non_bpjs_csv")
        if csv_non_bpjs:
            df_nb, err_nb = load_csv(csv_non_bpjs)
            if err_nb:
                st.error(f"❌ {err_nb}")
            else:
                st.success(f"✅ {len(df_nb):,} baris terbaca")
                st.dataframe(df_nb.head(20), use_container_width=True)
        else:
            st.caption("Format CSV: No.SEP, Disetujui (atau sesuaikan kolom Non-BPJS)")

    # ─────────────────────────────────────────────────────────────────────────
    # SUB-TAB 3: SIMULASI MANUAL
    # ─────────────────────────────────────────────────────────────────────────
    with sub3:
        st.markdown("### 🧮 Simulasi Manual")
        st.caption("Hitung Jaspel untuk 1 SEP secara manual")

        c1, c2 = st.columns(2)
        with c1:
            sim_cbg = st.number_input("Klaim INA CBGs (Rp)", min_value=0, value=5000000, step=100000, key="sim_cbg")
            sim_billing = st.number_input("Total Biaya Riil RS (Rp)", min_value=0, value=6000000, step=100000, key="sim_billing")
            sim_jenis = st.selectbox("Jenis Rawat", list(TARIF.keys()), key="sim_jenis")
            sim_naik = st.number_input("Jaspel Naik Kelas (Rp)", min_value=0, value=0, step=10000, key="sim_naik")

        with c2:
            sim_tarif = TARIF[sim_jenis]
            sim_hasil = hitung_jaspel(sim_cbg, sim_tarif, sim_billing, sim_naik)

            st.markdown("**📊 Hasil Simulasi:**")
            st.code(f"""
Klaim INA CBGs    = {fmt_rp(sim_cbg)}
Total Billing     = {fmt_rp(sim_billing)}
Tarif             = {sim_tarif*100:.0f}%

Jasa Pelayanan    = {fmt_rp(sim_cbg)} × {sim_tarif}
                  = {fmt_rp(sim_hasil['jasa_pelayanan'])}

Selisih CBGs      = {fmt_rp(sim_cbg)} − {fmt_rp(sim_billing)}
                  = {fmt_rp(sim_hasil['selisih_cbg'])}
                  {'→ NEGATIF, Jaspel Selisih = Rp 0' if sim_hasil['selisih_cbg'] <= 0 else '→ POSITIF'}

Jaspel Selisih    = {fmt_rp(sim_hasil['jaspel_selisih'])}
Jaspel Naik Kelas = {fmt_rp(sim_naik)}

Jaspel Total      = {fmt_rp(sim_hasil['jaspel_total'])}
✅ Jaspel Final   = {fmt_rp(sim_hasil['jaspel_final'])}
            """, language="text")

    # ─────────────────────────────────────────────────────────────────────────
    # SUB-TAB 4: MASTER JASPEL
    # ─────────────────────────────────────────────────────────────────────────
    with sub4:
        st.markdown("### 📋 Master Jaspel ICHA")
        st.caption("Referensi tarif dan distribusi Kantong Besar")

        st.markdown("#### Tarif BPJS")
        df_tarif = pd.DataFrame([
            {"Jenis Rawat": k, "Tarif (%)": f"{v*100:.0f}%", "Tarif Desimal": v}
            for k, v in TARIF.items()
        ])
        st.dataframe(df_tarif, use_container_width=True, hide_index=True)

        st.markdown("#### Estimasi Kantong Besar")
        col_kb1, col_kb2 = st.columns(2)
        with col_kb1:
            st.markdown("**Rawat Inap (RI)**")
            st.dataframe(pd.DataFrame([
                {"Jenis": k, "% Est.": f"{v:.1f}%"}
                for k, v in KANTONG_RI.items()
            ]), use_container_width=True, hide_index=True)

        with col_kb2:
            st.markdown("**Rawat Jalan (RJ)**")
            st.dataframe(pd.DataFrame([
                {"Jenis": k, "% Est.": f"{v:.1f}%"}
                for k, v in KANTONG_RJ.items()
            ]), use_container_width=True, hide_index=True)

        st.info("💡 Nilai aktual kantong besar tergantung pada mix tindakan per pasien di SIMRS ICHA.")
