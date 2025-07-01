import streamlit as st
import pandas as pd
import os
import requests
import time
from datetime import datetime
import pytz
import shutil
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression

# ========== SETUP FOLDER & ZONA ==========
os.makedirs("log", exist_ok=True)
os.makedirs("rekap", exist_ok=True)
os.makedirs("backup", exist_ok=True)
zona = pytz.timezone("Asia/Makassar")
sekarang = datetime.now(zona)
minggu_ini = sekarang.strftime("%Y-W%U")

# ========== INISIALISASI ==========
st.set_page_config(page_title="Soferklēsia", layout="centered")
st.title("🕊️ SOFERKLĒSIA 🕊️")
st.caption("“Di mana satu, dua orang berkumpul, di situ Allah hadir.”")

# ========== INPUT PETUGAS DAN GEREJA ==========
if "petugas" not in st.session_state:
    st.session_state.petugas = ""
if "lokasi" not in st.session_state:
    if os.path.exists("lokasi.txt"):
        with open("lokasi.txt", "r") as f:
            st.session_state.lokasi = f.read().strip()
    else:
        st.session_state.lokasi = ""

with st.form("form_identitas"):
    st.session_state.petugas = st.text_input("Nama Petugas", st.session_state.petugas)
    st.session_state.lokasi = st.text_input("Nama Gereja", st.session_state.lokasi)
    submitted = st.form_submit_button("Simpan Identitas")
    if submitted:
        with open("lokasi.txt", "w") as f:
            f.write(st.session_state.lokasi)
        st.success("Identitas disimpan.")

# ========== JUMLAH JEMAAT ==========
jumlah_file = "jumlah.txt"
if os.path.exists(jumlah_file):
    with open(jumlah_file, "r") as f:
        try:
            pria, wanita = map(int, f.read().strip().split(","))
        except:
            pria, wanita = 0, 0
else:
    pria, wanita = 0, 0

# ========== FUNGSI ==========
def simpan_jumlah(pria, wanita):
    with open(jumlah_file, "w") as f:
        f.write(f"{pria},{wanita}")

def log(aksi, pria, wanita):
    total = pria + wanita
    waktu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    log_file = f"log/log-{minggu_ini}.txt"
    with open(log_file, "a") as f:
        f.write(f"[{waktu}] {st.session_state.petugas} di {st.session_state.lokasi}: {aksi} → total: {total}\n")

def ambil_ai():
    ENDPOINTS = [
        "http://localhost:5000/deteksi",
        "http://192.168.1.10:5000/deteksi",
        "https://ai.soferklesia.com/deteksi"
    ]
    for url in ENDPOINTS:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                return r.json(), url
        except:
            continue
    return None, None

# ========== TAMPILAN JUMLAH ==========
st.subheader("Jumlah Kehadiran")
total = pria + wanita
col1, col2, col3 = st.columns(3)
col1.metric("Pria", pria)
col2.metric("Wanita", wanita)
col3.metric("Total", total)

# ========== FORM INPUT MANUAL ==========
with st.form("form_kehadiran"):
    tambah_pria = st.number_input("Tambah Pria", min_value=0, step=1, format="%d")
    tambah_wanita = st.number_input("Tambah Wanita", min_value=0, step=1, format="%d")
    if st.form_submit_button("Catat Kehadiran Manual"):
        pria += int(tambah_pria)
        wanita += int(tambah_wanita)
        simpan_jumlah(pria, wanita)
        log(f"Manual: +{int(tambah_pria)} pria, +{int(tambah_wanita)} wanita", pria, wanita)
        st.experimental_rerun()

# ========== DETEKSI OTOMATIS ==========
st.subheader("Deteksi Otomatis")
data_ai, server_aktif = ambil_ai()
if data_ai:
    st.success(f"Terhubung ke AI: {server_aktif}")
else:
    st.warning("Tidak ada koneksi ke server AI.")

# ========== LOG ==========
with st.expander("📄 Lihat Log Mingguan"):
    log_path = f"log/log-{minggu_ini}.txt"
    if os.path.exists(log_path):
        with open(log_path) as f:
            st.text(f.read())
    else:
        st.info("Belum ada log minggu ini.")

# ========== GRAFIK BULANAN & TAHUNAN ==========
st.subheader("📊 Grafik Kehadiran")
rekap_folder = "rekap"
data = []
if os.path.exists(rekap_folder):
    for file in sorted(os.listdir(rekap_folder)):
        if file.endswith(".txt"):
            minggu = file.replace("rekap-", "").replace(".txt", "")
            with open(os.path.join(rekap_folder, file)) as f:
                for line in f:
                    if "Total jemaat:" in line:
                        try:
                            total = int(line.split(":")[-1])
                            data.append((minggu, total))
                        except:
                            continue

if data:
    df = pd.DataFrame(data, columns=["Minggu", "Total"])
    df = df[df["Minggu"].str.contains(r"^\d{4}-W\d{2}$", na=False)]
    df["Minggu"] = pd.to_datetime(df["Minggu"].str.replace("W", "-"), format="%Y-%W", errors="coerce")
    df = df.dropna(subset=["Minggu"])
    df = df.sort_values("Minggu")
    st.line_chart(df.set_index("Minggu"))
else:
    st.info("Belum ada data grafik.")

# ========== ANALISIS AI ==========
st.subheader("🤖 Analisis AI")
if data and not df.empty:
    x = np.arange(len(df)).reshape(-1, 1)
    y = df["Total"].values
    model = LinearRegression().fit(x, y)
    pred = model.predict(np.array([[len(df)]]))[0]
    if not np.isnan(pred):
        st.write(f"📈 Prediksi jumlah jemaat minggu depan: **{int(pred)}**")
    else:
        st.warning("Prediksi tidak valid (NaN). Cek data rekap.")
    perubahan = y[-1] - y[-2] if len(y) > 1 else 0
    if abs(perubahan) > 30:
        st.warning("⚠️ Terdeteksi perubahan besar dalam jumlah kehadiran!")
else:
    st.info("Belum cukup data untuk analisis AI.")

# ========== AUTO BACKUP & REKAP ==========
minggu_file = "minggu.txt"
if os.path.exists(minggu_file):
    with open(minggu_file, "r") as f:
        minggu_lalu = f.read().strip()
else:
    minggu_lalu = minggu_ini

if minggu_ini != minggu_lalu:
    total_minggu_lalu = 0
    log_lama = f"log/log-{minggu_lalu}.txt"
    if os.path.exists(log_lama):
        shutil.copy(log_lama, f"backup/log-{minggu_lalu}.txt")
        with open(log_lama) as f:
            for line in f:
                if "total:" in line:
                    try:
                        total_minggu_lalu += int(line.split("total:")[-1])
                    except:
                        continue
        with open(f"rekap/rekap-{minggu_lalu}.txt", "w") as f:
            f.write(f"Rekap Kehadiran Minggu {minggu_lalu}\n")
            f.write(f"Total jemaat: {total_minggu_lalu}\n")
    with open(jumlah_file, "w") as f:
        f.write("0,0")
    with open(minggu_file, "w") as f:
        f.write(minggu_ini)
