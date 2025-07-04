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
- Hot storage disimpan di RAM (`OrderedDict`), cepat untuk akses data aktif.
- Cold storage disimpan dalam file biner `data.bin`, dengan indeks offset di `index.bin`.
- Eviction otomatis saat hot penuh dan perintah manual `day_change()`.

### 🔁 Replikasi Semi-Sinkron
- Setiap shard memiliki **2 replika**.
- Penulisan dikirim ke primary (sinkron), kemudian disalurkan ke replika sekunder secara **asinkron** menggunakan thread background.
- Cek konsistensi antar replika dengan perintah `check_consistency`.

### 🧩 Partisi Berdasarkan Hash
- Data dibagi ke dalam beberapa shard menggunakan:
  
  ```python
  shard_id = hash(key) % num_shards
  ```

- Mendukung **load balancing** dan **fault tolerance** antar shard.

### 🔐 Encoding Biner
- Saat data dipindah ke Cold (overwrite / day_change), data di-encode dalam format:

  ```
  [schema:1B][key_len:4B][value_len:4B][key][zlib(value)]
  ```

- Mendukung 4 versi skema dan evolusi field.
- Perintah `show_encoding` akan menampilkan hasil encoding dalam format hex.

### 🔧 Evolusi Skema
- Setiap value memiliki versi skema (v1–v4).
- Perintah `change_data` dapat digunakan untuk:
  - Mengubah tipe field (misal angka jadi string)
  - Menambah field baru (misal `hobi`)
  - Menghapus kolom tertentu

---

## 📁 Struktur Folder

```
fp/
├── core/
│   ├── encoder.py         # Encoding & decoding data biner
│   ├── storage.py         # Engine penyimpanan hybrid
│   ├── shard_manager.py   # Manajemen shard & replikasi
│   ├── schemas.py         # Definisi skema versi 1–4
│   └── measure.py         # Evaluasi performa sistem
├── data/
│   └── cold_store/        # File-file data cold (per shard & replika)
├── main.py                # CLI utama
├── README.md              # Dokumentasi ini
```

---

## 🧪 Cara Menjalankan

```bash
# 1. Jalankan program utama
python3 main.py
```

Di dalam CLI, tersedia perintah berikut:

| Perintah         | Fungsi                                                                 |
|------------------|------------------------------------------------------------------------|
| `put`            | Simpan key dan value ke sistem                                         |
| `get`            | Ambil data berdasarkan key                                             |
| `get_all`        | Ambil semua versi historis untuk key tertentu                          |
| `day_change`     | Pindahkan semua data aktif dari Hot ke Cold Storage                    |
| `change_data`    | Ubah data (versi tertentu), mendukung tambah/hapus field & ubah tipe   |
| `show_encoding`  | Tampilkan hasil encoding biner untuk key tertentu                      |
| `check_key`      | Periksa lokasi (hot/cold) dan histori dari suatu key                   |
| `check_consistency` | Periksa konsistensi antar replika                                    |
| `which_shard`    | Tampilkan shard tempat key disimpan                                    |
| `perf`           | Evaluasi performa sistem                                               |
| `clear`          | Hapus semua data                                                       |
| `exit`           | Keluar dari CLI                                                        |

---

## 📊 Evaluasi Performa

Berikut hasil ujicoba dengan 100 data (`perf` command):

| Jenis Operasi     | Latency Rata-rata | Throughput         |
|-------------------|-------------------|--------------------|
| PUT (Hot)         | 6.18 ms           | 161.65 ops/sec     |
| GET dari Hot      | 3.89 ms           | 257.01 ops/sec     |
| GET dari Cold     | 14.46 ms          | 69.14 ops/sec      |

- ✅ Fault Tolerance: Sistem tetap berjalan saat replika cold sementara dimatikan.
- 📈 Grafik disimpan sebagai `performance_eval.png`.

---

## 💡 Lesson Learned

- 🔥 Hybrid storage sangat efisien untuk data aktif, tetapi perlu cold untuk skalabilitas jangka panjang.
- 🔁 Replikasi meningkatkan ketahanan data, namun menambah overhead saat penulisan.
- 🧩 Partisi memungkinkan sistem diskalakan horizontal (lebih banyak shard).

---

## ⚠️ Batasan & Ide Pengembangan

| Batasan                                  | Ide Pengembangan                      |
|------------------------------------------|----------------------------------------|
| Kapasitas RAM terbatas untuk Hot Storage | Tambahkan cache eviction policy (LRU)  |
| Latency Cold tinggi (~14 ms)             | Gunakan mmap atau database ringan      |
| Belum ada fitur delete langsung          | Tambah command `delete` atau TTL       |
| Replika belum bisa delay sync sepenuhnya | Buat queue persist / retry mechanism   |

---

## 📸 Demo & Laporan

🎬 **Demo Unlisted YouTube**  
[▶️ Tonton Demo](https://youtu.be/PgH_rmn9W7Y?feature=shared)

📊 **PPT Laporan**  
[📄 Lihat di Canva](https://www.canva.com/design/DAGrEH4QHBo/GgWrFAEyomFC9XkPwYphJw/view?utm_content=DAGrEH4QHBo&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=hf832a7bef6)

---

## 🧑‍💻 Dibuat oleh

> [@dwmhr12](https://github.com/dwmhr12)  
> Mahasiswa Sistem Informasi – ITS Surabaya  
> Proyek akademik: Desain sistem penyimpanan key-value berbasis Python
