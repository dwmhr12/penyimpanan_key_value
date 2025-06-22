# 🧠 Penyimpanan Key-Value: Hybrid Storage Engine dengan Replikasi & Partisi

Sistem ini adalah implementasi sederhana dari penyimpanan key-value **tanpa database eksternal**, yang menggabungkan:

- ✅ **Hybrid Storage** (Hot: RAM, Cold: File)
- 🔁 **Replikasi** (Sinkron / Semi-Synchronous)
- 🧩 **Partisi Data** berdasarkan hash key
- 📦 **Encoding Biner** (zlib + skema versioning)
- 🔄 **Evolusi Skema** (tambah, ubah, hapus field)

---

## 🛠️ Fitur Utama

### 💾 Hybrid Storage (Hot & Cold)
- Hot storage disimpan di RAM (OrderedDict), cepat tapi terbatas kapasitas.
- Cold storage disimpan dalam file biner (`data.bin`) + indeks (`index.bin`).

### 🔁 Replikasi Semi-Sinkron
- Setiap shard punya 2 replika.
- Penulisan dikirim ke primary (sinkron), dilanjutkan ke secondary via thread async.

### 🧩 Partisi Berdasarkan Hash
- Menggunakan SHA-256(key) % num_shards untuk menentukan shard tujuan.

### 🔐 Encoding Biner
- Format biner: `[schema][key_len][val_len][key][compressed_value]`
- Kompresi menggunakan zlib.
- Mendukung evolusi skema (versi 1–4).

### 🔧 Evolusi Skema
- Mendukung perubahan struktur data: ubah tipe, tambah kolom, hapus kolom.

---
## 📁 Struktur Folder

```
fp/
├── core/
│   ├── encoder.py
│   ├── storage.py
│   ├── shard_manager.py
│   ├── schemas.py
│   └── measure.py
├── data/
│   └── cold_store/
├── main.py
├── README.md
```

---

## 🧪 Cara Menjalankan

```bash
# Jalankan program
python3 main.py

# Evaluasi performa
> perf

# Lihat hasil encoding biner
> show_encoding
```

---

## 💡 Lesson Learned

- Hybrid storage meningkatkan performa untuk data aktif.
- Replikasi menjaga redundansi, tapi bisa menambah beban write.
- Partisi membagi beban ke beberapa shard secara otomatis.

---

## ⚠️ Batasan & Ide Pengembangan

| Batasan                                  | Ide Pengembangan                      |
|------------------------------------------|----------------------------------------|
| Kapasitas RAM terbatas untuk Hot Storage | Tambahkan cache eviction policy        |
| Latency Cold tinggi (~14 ms)             | Gunakan mmap atau database ringan      |
| Belum ada fitur delete langsung          | Tambah command `delete` atau TTL       |

---

## 📸 Demo

📺 [Tonton di YouTube (Unlisted)](https://youtu.be/PgH_rmn9W7Y?feature=shared)

---

## 🧑‍💻 Dibuat oleh

> [@dwmhr12](https://github.com/dwmhr12) – Proyek akademik penyimpanan key-value berbasis Python (ITS)
