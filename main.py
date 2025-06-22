import os
import json
import logging
import binascii
import struct
import zlib
from core.shard_manager import ShardManager
from core.schemas import schemas
from core.encoder import Encoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def is_valid_key(k):
    return k.isalnum() and len(k) <= 255

def parse_value(s):
    s = s.strip()
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try: return int(s)
    except: pass
    try: return float(s)
    except: return s

def format_value(value):
    return json.dumps(value, indent=2)

def display_help():
    print("""
=== Perintah ===
put              : Simpan key-value.
get              : Ambil nilai berdasarkan key.
get_all          : Tampilkan semua versi histori dari key tertentu.
list_all         : Tampilkan semua key dan value dari hot & cold storage.
check_key        : Cek lokasi dan keberadaan key.
check_consistency: Periksa konsistensi data antar replika.
list_partitions  : Tampilkan jumlah data di tiap shard dan replica.
which_shard      : Tampilkan shard tempat key disimpan.
change_data      : Ubah data versi tertentu (ubah tipe/hapus kolom).
show_schema      : Tampilkan semua versi skema yang didukung.
perf             : Evaluasi performa (latency & throughput + fault tolerance).
clear            : Hapus semua data atau berdasarkan key.
day_change       : Pindahkan semua data hot ke cold.
test_schema      : Uji simulasi evolusi skema (tambah/hapus kolom).
show_encoding    : Tampilkan format biner dan encoding hex untuk key tertentu.
help             : Panduan ini.
exit             : Keluar.
================
""")

def main():
    store = ShardManager(num_shards=2, replica_count=2)
    display_help()

    while True:
        cmd = input("\n> ").strip().lower()

        if cmd == "put":
            key = input("Key   : ").strip()
            if not is_valid_key(key):
                print("✗ Key hanya alfanumerik & max 255 karakter"); continue

            name = input("Name  : ").strip()
            if not name or len(name) > 255:
                print("✗ Name wajib & max 255 karakter"); continue

            try:
                age = int(input("Age   : ").strip())
            except:
                print("✗ Age harus berupa angka"); continue

            try:
                version = int(input("Skema versi (1-4): ").strip())
                if version not in schemas:
                    raise ValueError
            except:
                print("✗ Versi skema tidak valid"); continue

            extra_fields = {}
            for field in schemas[version]:
                val = input(f"  {field}: ").strip()
                extra_fields[field] = parse_value(val)

            value = {"name": name, "age": age}
            value.update(extra_fields)

            sid = store._get_shard_id(key)
            for replica in store.shards[sid]:
                if key in replica.hot:
                    old_value = replica.hot[key]
                    hist_key = f"{key}::hist"
                    replica._write_cold(hist_key, old_value, schema_version=version, extra_field=None)

            store.put(key, value, write_to_cold=False, schema_version=version, extra_field=None)
            print(f"✓ Data '{key}' disimpan")

        elif cmd == "get":
            key = input("Key: ").strip()
            if not is_valid_key(key):
                print("✗ Key tidak valid"); continue
            v = store.get(key)
            print(f"✓ Value:\n{format_value(v)}" if v else f"✗ '{key}' tidak ditemukan")

        elif cmd == "get_all":
            key = input("Key: ").strip()
            if not is_valid_key(key): continue
            res = store.shards[store._get_shard_id(key)][0].get_all_versions(key)
            if not res: print("✗ Tidak ditemukan")
            else:
                print("Versi terbaru:\n", format_value(res.get("latest", {})))
                print("Histori:")
                for k, v in res.items():
                    if k != "latest": print(f"{k} → {json.dumps(v)}")

        elif cmd == "change_data":
            key = input("Key: ").strip()
            sid = store._get_shard_id(key)
            replica = store.shards[sid][0]

            versions = replica.get_all_versions(key)
            if key in replica.hot:
                versions['HOT'] = replica.hot[key]

            if not versions:
                print("✗ Tidak ditemukan versi manapun"); continue

            all_keys = list(versions.keys())
            for i, k in enumerate(all_keys):
                print(f"{i+1}. {k}: {json.dumps(versions[k], indent=2)}")

            try:
                idx = int(input("Pilih versi (nomor): ").strip()) - 1
                base_key = all_keys[idx]
                base_value = versions[base_key]
            except:
                print("✗ Pilihan tidak valid"); continue

            print("Field saat ini:", json.dumps(base_value, indent=2))

            if input("Edit field? (y/n): ").strip().lower() == "y":
                f = input("Field name: ").strip()
                if f in base_value:
                    new_val = input("Nilai baru: ")
                    base_value[f] = parse_value(new_val)

            if input("Hapus field? (y/n): ").strip().lower() == "y":
                to_del = input("Kolom yang dihapus (pisah koma): ").strip().split(",")
                for col in to_del:
                    base_value.pop(col.strip(), None)

            if input("Tambah field? (y/n): ").strip().lower() == "y":
                col = input("Kolom baru: ").strip()
                val = input("Nilai: ")
                base_value[col] = parse_value(val)

            store.put(key, base_value, write_to_cold=True)
            print("✓ Perubahan disimpan sebagai versi baru")

        elif cmd == "check_key":
            key = input("Key: ").strip()
            sid = store._get_shard_id(key)
            hot = any(key in r.hot for r in store.shards[sid])
            cold = any(key in r.index for r in store.shards[sid])
            hist = [k for k in store.shards[sid][0].index if k.startswith(f"{key}::")]
            print(f"Key:{key},Shard:{sid},HOT:{hot},COLD:{cold},Histori:{len(hist)}")
            if hist: print("  " + "\n  ".join(hist))

        elif cmd == "check_consistency":
            key = input("Key: ").strip()
            ok = store.check_replica_consistency(key)
            print("✓ Konsisten" if ok else "✗ Tidak konsisten")

        elif cmd == "which_shard":
            key = input("Key: ").strip()
            sid = store._get_shard_id(key)
            print(f"✓ Key '{key}' masuk ke shard {sid}")

        elif cmd == "list_all":
            print("=== Data di HOT storage ===")
            for i, shard in enumerate(store.shards):
                for j, replica in enumerate(shard):
                    print(f"[Shard {i} Replica {j}]")
                    for k, v in replica.hot.items():
                        print(f"  {k}: {v}")
            print("\n=== Data di COLD storage (index) ===")
            for i, shard in enumerate(store.shards):
                for j, replica in enumerate(shard):
                    print(f"[Shard {i} Replica {j}]")
                    for k, v in replica.index.items():
                        if "::" not in k:
                            print(f"  {k}: {v}")

        elif cmd == "list_partitions":
            for i, shard in enumerate(store.shards):
                for j, replica in enumerate(shard):
                    h, c = len(replica.hot), len(replica.index)
                    print(f"Shard {i} Replica {j}: HOT={h}, COLD={c}")

        elif cmd == "day_change":
            res = store.day_change()
            total = sum(sum(v) for v in res.values())
            print(f"✓ Day change: {total} data dipindah")

        elif cmd == "perf":
            from core.measure import measure_performance
            measure_performance(store)

        elif cmd == "test_schema":
            print("🚀 Testing schema evolution...")
            for ver, fields in schemas.items():
                dummy = {"name": f"user{ver}", "age": 20 + ver}
                for f in fields:
                    dummy[f] = f"val_{f}"
                key = f"test{ver}"
                store.put(key, dummy, write_to_cold=True, schema_version=ver)
                print(f"✓ Simpan {key} dengan skema {ver}")
            print("✅ Semua skema diuji")

        elif cmd == "clear":
            sub = input("all atau key? ").strip()
            if sub == "all":
                for shard in store.shards:
                    for r in shard:
                        r.hot.clear()
                        if os.path.exists(r.cold_file): os.remove(r.cold_file)
                        idx = os.path.join(r.cold_path, "index.bin")
                        if os.path.exists(idx): os.remove(idx)
                print("✓ Semua data dihapus")
            else:
                key = sub
                sid = store._get_shard_id(key)
                for r in store.shards[sid]:
                    r.hot.pop(key, None); r.index.pop(key, None)
                print(f"✓ '{key}' dihapus dari shard {sid}")

        elif cmd == "show_schema":
            print("Skema yang tersedia:")
            for k in sorted(schemas):
                print(f"  Skema {k}: {schemas[k]}")

        elif cmd == "show_encoding":
            key = input("Key: ").strip()
            if not is_valid_key(key):
                print("✗ Key tidak valid"); continue
            sid = store._get_shard_id(key)
            for replica in store.shards[sid]:
                if key in replica.index:
                    with open(replica.cold_file, "rb") as f:
                        f.seek(replica.index[key])
                        data = f.read(100)
                        hex_output = binascii.hexlify(data).decode("utf-8")
                        print(f"✓ Format Biner (Schema v1): [schema:1B][key_len:4B][value_len:4B][key][value_compressed]")
                        print(f"✓ Output Encoding (hex): {hex_output}")
                        key_len = struct.unpack('!I', data[1:5])[0]
                        value_len = struct.unpack('!I', data[5:9])[0]
                        print(f"✓ Penjelasan: 01 (schema v1), {key_len} (key_len), {value_len} (value_len), diikuti key dan value terkompresi")
                        break
                elif key in replica.hot:
                    value = replica.hot[key]
                    encoded = Encoder.encode(key, value)
                    hex_output = binascii.hexlify(encoded).decode("utf-8")
                    print(f"✓ Format Biner (Schema v1): [schema:1B][key_len:4B][value_len:4B][key][value_compressed]")
                    print(f"✓ Output Encoding (simulasi hex): {hex_output}")
                    print(f"✓ Penjelasan: 01 (schema v1), {len(key.encode('utf-8'))} (key_len), {len(zlib.compress(json.dumps(value).encode('utf-8')))} (value_len), diikuti key dan value terkompresi")
                    break
            else:
                print(f"✗ '{key}' tidak ditemukan")

        elif cmd == "help":
            display_help()

        elif cmd == "exit":
            break

        else:
            print("✗ Perintah tidak dikenal")

if __name__ == "__main__":
    main()
