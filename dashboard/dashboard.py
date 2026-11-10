from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns
import streamlit as st

# ---------------------------------------------------------------- Konfigurasi
st.set_page_config(page_title="Dashboard Bike Sharing", page_icon="🚲", layout="wide")
sns.set_theme(style="whitegrid", rc={"axes.grid.axis": "y"})

WARNA_NORMAL, WARNA_SOROT = "#B8C4D0", "#1F6FB2"
WARNA_KERJA, WARNA_LIBUR = "#1F6FB2", "#E07B39"
URUTAN_CUACA = ["Cerah", "Berkabut", "Hujan/Salju"]
URUTAN_SUHU = ["< 10°C", "10-20°C", "20-30°C", "> 30°C"]
NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def ribuan(angka, desimal=0):
    """Format angka dengan pemisah ribuan titik dan desimal koma."""
    teks = f"{angka:,.{desimal}f}"
    return teks.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Data
@st.cache_data
def load_data():
    path = Path(__file__).parent / "main_data.csv"
    df = pd.read_csv(path, parse_dates=["dteday"])
    return df


df = load_data()

# ---------------------------------------------------------------- Sidebar (filter)
with st.sidebar:
    st.header("Filter Data")
    tgl_min, tgl_maks = df["dteday"].min().date(), df["dteday"].max().date()
    rentang = st.date_input("Rentang tanggal", value=(tgl_min, tgl_maks),
                            min_value=tgl_min, max_value=tgl_maks)
    cuaca_dipilih = st.multiselect("Kondisi cuaca", URUTAN_CUACA, default=URUTAN_CUACA)
    st.caption("Filter berlaku untuk seluruh grafik di dashboard.")

# date_input mengembalikan 1 tanggal saat pengguna baru memilih tanggal awal
if isinstance(rentang, (tuple, list)) and len(rentang) == 2:
    awal, akhir = rentang
else:
    st.info("Pilih tanggal akhir pada filter rentang tanggal untuk menampilkan data.")
    st.stop()

data = df[(df["dteday"].dt.date >= awal) & (df["dteday"].dt.date <= akhir)
          & (df["weather_group"].isin(cuaca_dipilih))]

# ---------------------------------------------------------------- Header
st.title("🚲 Dashboard Analisis Bike Sharing")
st.caption("Data penyewaan sepeda per jam, 2011-2012. Gunakan filter di sidebar untuk menyesuaikan tampilan.")

if data.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau kondisi cuaca.")
    st.stop()

# ---------------------------------------------------------------- Ringkasan
total = data["cnt"].sum()
rata_jam = data["cnt"].mean()
persen_casual = data["casual"].sum() / total * 100
jam_puncak = int(data.groupby("hr")["cnt"].mean().idxmax())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total penyewaan", ribuan(total))
k2.metric("Rata-rata per jam", ribuan(rata_jam, 1))
k3.metric("Pengguna casual", f"{ribuan(persen_casual, 1)}%")
k4.metric("Jam puncak", f"{jam_puncak:02d}:00")

st.divider()

# ---------------------------------------------------------------- Pertanyaan 1
st.subheader("1. Pengaruh cuaca dan suhu terhadap penyewaan")
st.write("Rata-rata penyewaan per jam berdasarkan kondisi cuaca dan rentang suhu.")

cuaca = (data.groupby("weather_group")["cnt"].mean()
         .reindex([c for c in URUTAN_CUACA if c in data["weather_group"].unique()]))
suhu = (data.groupby("temp_group", observed=True)["cnt"].mean()
        .reindex([s for s in URUTAN_SUHU if s in data["temp_group"].unique()]))

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

warna = [WARNA_SOROT if v == cuaca.max() else WARNA_NORMAL for v in cuaca]
bars = axes[0].bar(cuaca.index, cuaca.values, color=warna)
axes[0].bar_label(bars, fmt="%.0f", padding=3)
axes[0].set_ylim(0, cuaca.max() * 1.15)
axes[0].set_title("Rata-rata Penyewaan per Jam Berdasarkan Cuaca", fontsize=12)
axes[0].set_xlabel("Kondisi cuaca")
axes[0].set_ylabel("Rata-rata penyewaan per jam")

warna = [WARNA_SOROT if v == suhu.max() else WARNA_NORMAL for v in suhu]
bars = axes[1].bar(suhu.index.astype(str), suhu.values, color=warna)
axes[1].bar_label(bars, fmt="%.0f", padding=3)
axes[1].set_ylim(0, suhu.max() * 1.15)
axes[1].set_title("Rata-rata Penyewaan per Jam Berdasarkan Suhu", fontsize=12)
axes[1].set_xlabel("Rentang suhu")
axes[1].set_ylabel("Rata-rata penyewaan per jam")

sns.despine()
plt.tight_layout()
st.pyplot(fig)
plt.close(fig)

if {"Cerah", "Hujan/Salju"} <= set(cuaca.index):
    selisih = (cuaca["Cerah"] - cuaca["Hujan/Salju"]) / cuaca["Cerah"] * 100
    st.info(f"Penyewaan saat cuaca cerah **{ribuan(selisih)}%** lebih tinggi dibanding saat hujan/salju "
            f"({ribuan(cuaca['Cerah'], 1)} vs {ribuan(cuaca['Hujan/Salju'], 1)} per jam). "
            f"Rentang suhu dengan penyewaan tertinggi: **{suhu.idxmax()}**.")
else:
    st.info(f"Kondisi cuaca dengan penyewaan tertinggi: **{cuaca.idxmax()}**. "
            f"Rentang suhu dengan penyewaan tertinggi: **{suhu.idxmax()}**.")

st.divider()

# ---------------------------------------------------------------- Pertanyaan 2
st.subheader("2. Jam puncak penyewaan: hari kerja vs hari libur")
st.write("Rata-rata penyewaan per jam dan proporsi tipe pengguna pada hari kerja dan hari libur.")

jam_df = data.groupby(["day_type", "hr"])["cnt"].mean().reset_index()
proporsi = data.groupby("day_type")[["casual", "registered"]].sum()
proporsi = proporsi.div(proporsi.sum(axis=1), axis=0) * 100

fig, axes = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [2, 1]})

y_maks = jam_df["cnt"].max()
for tipe, warna in [("Hari Kerja", WARNA_KERJA), ("Hari Libur", WARNA_LIBUR)]:
    d = jam_df[jam_df["day_type"] == tipe]
    if d.empty:
        continue
    axes[0].plot(d["hr"], d["cnt"], marker="o", linewidth=2, color=warna, label=tipe)
    puncak = d.loc[d["cnt"].idxmax()]
    geser = (2.5, y_maks * 0.06) if tipe == "Hari Kerja" else (0, y_maks * 0.14)
    axes[0].annotate(f"Puncak {int(puncak['hr']):02d}:00 ({puncak['cnt']:.0f})",
                     xy=(puncak["hr"], puncak["cnt"]),
                     xytext=(puncak["hr"] + geser[0], puncak["cnt"] + geser[1]),
                     ha="center", arrowprops=dict(arrowstyle="->", color=warna), color=warna)
axes[0].set_ylim(0, y_maks * 1.25)
axes[0].set_xticks(range(0, 24))
axes[0].set_title("Rata-rata Penyewaan per Jam", fontsize=12)
axes[0].set_xlabel("Jam")
axes[0].set_ylabel("Rata-rata penyewaan")
axes[0].legend(loc="upper left")

proporsi[["casual", "registered"]].plot(kind="bar", stacked=True, ax=axes[1],
                                        color=[WARNA_LIBUR, WARNA_KERJA], rot=0)
for container in axes[1].containers:
    axes[1].bar_label(container, fmt="%.1f%%", label_type="center", color="white")
axes[1].set_title("Proporsi Tipe Pengguna", fontsize=12)
axes[1].set_xlabel("")
axes[1].set_ylabel("Persentase (%)")
axes[1].legend(["Casual", "Registered"], loc="upper center", bbox_to_anchor=(0.5, -0.08),
               ncol=2, frameon=False)

sns.despine()
plt.tight_layout()
st.pyplot(fig)
plt.close(fig)

ringkas = []
for tipe in ["Hari Kerja", "Hari Libur"]:
    d = jam_df[jam_df["day_type"] == tipe]
    if not d.empty:
        ringkas.append(f"{tipe.lower()} pukul **{int(d.loc[d['cnt'].idxmax(), 'hr']):02d}:00**")
if ringkas:
    st.info("Puncak penyewaan: " + " dan ".join(ringkas) + ".")

st.divider()

# ---------------------------------------------------------------- Pertanyaan 3
st.subheader("3. Pertumbuhan penyewaan bulanan 2012 vs 2011")
st.write("Total penyewaan per bulan dan persentase pertumbuhan 2012 terhadap bulan yang sama di 2011.")

bulanan = data.groupby(["yr", "mnth"])["cnt"].sum().unstack(0)

fig, axes = plt.subplots(1, 2, figsize=(15, 5))

for tahun, warna in [(2011, WARNA_NORMAL), (2012, WARNA_SOROT)]:
    if tahun in bulanan.columns:
        seri = bulanan[tahun].dropna()
        axes[0].plot([NAMA_BULAN[b - 1] for b in seri.index], seri.values,
                     marker="o", linewidth=2, color=warna, label=str(tahun))
axes[0].set_title("Total Penyewaan Bulanan", fontsize=12)
axes[0].set_xlabel("Bulan")
axes[0].set_ylabel("Total penyewaan")
axes[0].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: ribuan(v)))
axes[0].legend()

punya_dua_tahun = {2011, 2012} <= set(bulanan.columns)
if punya_dua_tahun:
    lengkap = bulanan.dropna(subset=[2011, 2012])
else:
    lengkap = pd.DataFrame()

if not lengkap.empty:
    pert = (lengkap[2012] / lengkap[2011] - 1) * 100
    warna = [WARNA_SOROT if v == pert.max() else WARNA_NORMAL for v in pert]
    bars = axes[1].bar([NAMA_BULAN[b - 1] for b in pert.index], pert.values, color=warna)
    axes[1].bar_label(bars, fmt="%.0f%%", padding=3)
    axes[1].set_ylim(0, pert.max() * 1.15)
    axes[1].set_title("Pertumbuhan Penyewaan 2012 terhadap 2011", fontsize=12)
    axes[1].set_xlabel("Bulan")
    axes[1].set_ylabel("Pertumbuhan (%)")
else:
    axes[1].axis("off")
    axes[1].text(0.5, 0.5, "Pertumbuhan membutuhkan data bulan yang sama\npada 2011 dan 2012.\n"
                 "Perluas rentang tanggal di sidebar.", ha="center", va="center", fontsize=11)

sns.despine()
plt.tight_layout()
st.pyplot(fig)
plt.close(fig)

if not lengkap.empty:
    total_pert = (lengkap[2012].sum() / lengkap[2011].sum() - 1) * 100
    st.info(f"Pertumbuhan total pada bulan-bulan yang dibandingkan: **{ribuan(total_pert, 1)}%**. "
            f"Pertumbuhan tertinggi pada bulan **{NAMA_BULAN[int(pert.idxmax()) - 1]}** "
            f"({ribuan(pert.max(), 1)}%).")

st.caption("Sumber data: Bike Sharing Dataset (2011-2012).")
