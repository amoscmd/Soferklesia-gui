# Streamlit versi Soferklēsia
import streamlit as st
import threading
import os
import json
import shutil
import requests
import time
import pytz
from datetime import datetime

zona = pytz.timezone("Asia/Makassar")
sekarang = datetime.now(zona)
minggu_ini = sekarang.strftime("%Y-W%U")

os.makedirs("log", exist_ok=True)
os.makedirs("rekap", exist_ok=True)
os.makedirs("backup", exist_ok=True)

hasil_deteksi = {"male": 0, "female": 0}
lock = threading.Lock()

try:
    with open("config.json") as f:
        config = json.load(f)
        DETEKSI_HOST = config.get("host", "localhost")
        DETEKSI_PORT = config.get("port", 5000)
except:
    DETEKSI_HOST = "localhost"
    DETEKSI_PORT = 5000

# Ambil lokasi
if os.path.exists("lokasi.txt"):
    with open("lokasi.txt", "r") as f:
        lokasi = f.read().strip()
else:
    lokasi = "-"

# Minggu lalu dan rekap otomatis
if os.path.exists("minggu.txt"):
    with open("minggu.txt", "r") as f:
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
    with open("jumlah.txt", "w") as f:
        f.write("0,0")
    with open("minggu.txt", "w") as f:
        f.write(minggu_ini)

if os.path.exists("jumlah.txt"):
    try:
        with open("jumlah.txt", "r") as f:
            pria, wanita = map(int, f.read().strip().split(","))
    except:
        pria = wanita = 0
else:
    pria = wanita = 0

# Fungsi bantu
def simpan():
    with open("jumlah.txt", "w") as f:
        f.write(f"{pria},{wanita}")

def log(aksi):
    waktu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    total = pria + wanita
    with open(f"log/log-{minggu_ini}.txt", "a") as f:
        f.write(f"[{waktu}] {petugas} di {lokasi}: {aksi} → total: {total}\n")

def proses_ai():
    global pria, wanita
    while True:
        try:
            response = requests.get(f"http://{DETEKSI_HOST}:{DETEKSI_PORT}/deteksi")
            hasil = response.json()
            with lock:
                if hasil.get("male") is not None:
                    pria = hasil["male"]
                    log("AI: Deteksi pria")
                if hasil.get("female") is not None:
                    wanita = hasil["female"]
                    log("AI: Deteksi wanita")
                simpan()
        except:
            pass
        time.sleep(10)

threading.Thread(target=proses_ai, daemon=True).start()

# Tampilan Streamlit
st.set_page_config(page_title="Soferklesia", layout="centered")
st.title("\U0001F54A\ufe0f SOFERKLĒSIA")
st.markdown("Di mana satu, dua orang berkumpul, di situ Allah hadir.")

if "petugas" not in st.session_state:
    st.session_state.petugas = st.text_input("Masukkan nama petugas")
    st.stop()
else:
    petugas = st.session_state.petugas

if lokasi == "-":
    lokasi = st.text_input("Masukkan nama gereja/lokasi")
    if lokasi:
        with open("lokasi.txt", "w") as f:
            f.write(lokasi)
        st.experimental_rerun()
    st.stop()

st.info("Mode: AI Online (Lokal & Sensor)")
total = pria + wanita
st.metric("\U0001F468 Pria", pria)
st.metric("\U0001F469 Wanita", wanita)
st.metric("\U0001F9D0 Total", total)

col1, col2 = st.columns(2)
with col1:
    if st.button("Tambah Pria"):
        pria += 1
        simpan()
        log("Tambah pria: +1")
with col2:
    if st.button("Tambah Wanita"):
        wanita += 1
        simpan()
        log("Tambah wanita: +1")

col3, col4 = st.columns(2)
with col3:
    if st.button("Kurangi Pria"):
        pria = max(0, pria - 1)
        simpan()
        log("Kurangi pria: -1")
with col4:
    if st.button("Kurangi Wanita"):
        wanita = max(0, wanita - 1)
        simpan()
        log("Kurangi wanita: -1")

st.markdown("---")
if st.button("Lihat Grafik Bulanan"):
    st.subheader("📊 Grafik Bulanan")
    rekap_data = {}
    for nama_file in os.listdir("rekap"):
        if nama_file.endswith(".txt"):
            bagian = nama_file.replace("rekap-", "").replace(".txt", "")
            with open(f"rekap/{nama_file}") as f:
                for baris in f:
                    if "Total jemaat:" in baris:
                        total = int(baris.strip().split(":")[-1])
                        rekap_data[bagian] = total
    for minggu, total in sorted(rekap_data.items()):
        bar = "#" * (total // 10)
        st.text(f"{minggu:>10} | {bar} ({total})")

if st.button("Lihat Grafik Tahunan"):
    st.subheader("📊 Grafik Tahunan")
    tahunan = {}
    for nama_file in os.listdir("rekap"):
        if nama_file.endswith(".txt"):
            tahun = nama_file[6:10]
            with open(f"rekap/{nama_file}") as f:
                for baris in f:
                    if "Total jemaat:" in baris:
                        total = int(baris.strip().split(":")[-1])
                        tahunan[tahun] = tahunan.get(tahun, 0) + total
    for tahun, total in sorted(tahunan.items()):
        bar = "#" * (total // 50)
        st.text(f"{tahun} | {bar} ({total})")

if st.button("Analisis AI"):
    st.subheader("🤖 Analisis AI")
    total = pria + wanita
    if total == 0:
        st.warning("Belum ada data kehadiran.")
    else:
        persentase_pria = pria / total * 100
        persentase_wanita = wanita / total * 100
        st.write(f"Total Jemaat : {total}")
        st.write(f"Pria         : {pria} ({persentase_pria:.1f}%)")
        st.write(f"Wanita       : {wanita} ({persentase_wanita:.1f}%)")

if st.button("Tampilkan Log Minggu Ini"):
    st.subheader(f"📄 Log Minggu Ini ({minggu_ini})")
    log_file = f"log/log-{minggu_ini}.txt"
    if os.path.exists(log_file):
        with open(log_file) as f:
            st.text(f.read())
    else:
        st.warning("Belum ada log minggu ini.")
        
