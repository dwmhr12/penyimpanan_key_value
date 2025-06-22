# ===== File: core/measure.py =====
import time
import os
import matplotlib.pyplot as plt

def measure_performance(store):
    put_latencies = []
    get_latencies_hot = []
    get_latencies_cold = []
    keys = [f"perf{i}" for i in range(100)]

    # Measure PUT
    start_total = time.perf_counter()
    for k in keys:
        start = time.perf_counter()
        store.put(k, {"value": k}, write_to_cold=False)
        put_latencies.append((time.perf_counter() - start) * 1000)
    put_time = time.perf_counter() - start_total
    put_throughput = len(keys) / put_time

    # Measure GET (Hot)
    start_total = time.perf_counter()
    for k in keys:
        start = time.perf_counter()
        store.get(k)
        get_latencies_hot.append((time.perf_counter() - start) * 1000)
    get_hot_time = time.perf_counter() - start_total
    get_hot_throughput = len(keys) / get_hot_time

    # Simulasi day change → pindahkan ke cold
    store.day_change()
    for shard in store.shards:
        for replica in shard:
            replica.hot.clear()

    # Measure GET (Cold)
    start_total = time.perf_counter()
    for k in keys:
        start = time.perf_counter()
        store.get(k)
        get_latencies_cold.append((time.perf_counter() - start) * 1000)
    get_cold_time = time.perf_counter() - start_total
    get_cold_throughput = len(keys) / get_cold_time

    # Hitung rata-rata latency
    avg_put = sum(put_latencies) / len(put_latencies)
    avg_get_hot = sum(get_latencies_hot) / len(get_latencies_hot)
    avg_get_cold = sum(get_latencies_cold) / len(get_latencies_cold)

    # Simulasi fault tolerance (hapus sementara cold file)
    success = True
    target_file = "data/cold_store/shard0_rep0/data.bin"
    temp_file = target_file + ".bak"
    if os.path.exists(target_file):
        os.rename(target_file, temp_file)
        try:
            val = store.get("perf0")
            if not val:
                success = False
        except:
            success = False
        os.rename(temp_file, target_file)

    # Tampilkan hasil evaluasi
    print("\n--- Evaluasi Performa ---")
    print(f"Rata-rata PUT latency     : {avg_put:.2f} ms")
    print(f"Throughput PUT            : {put_throughput:.2f} ops/sec")
    print(f"Rata-rata GET dari HOT    : {avg_get_hot:.2f} ms")
    print(f"Throughput GET (Hot)      : {get_hot_throughput:.2f} ops/sec")
    print(f"Rata-rata GET dari COLD   : {avg_get_cold:.2f} ms")
    print(f"Throughput GET (Cold)     : {get_cold_throughput:.2f} ops/sec")
    check_icon = "✅ Berhasil" if success else "❌ Gagal"
    print(f"Fault tolerance           : {check_icon}")

    # Buat grafik perbandingan
    fig, ax1 = plt.subplots()
    ax1.bar(['Put', 'Get (Hot)', 'Get (Cold)'],
            [avg_put, avg_get_hot, avg_get_cold],
            color='b', alpha=0.5)
    ax1.set_ylabel("Latency (ms)", color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(['Put', 'Get (Hot)', 'Get (Cold)'],
             [put_throughput, get_hot_throughput, get_cold_throughput],
             color='r', marker='o')
    ax2.set_ylabel("Throughput (ops/sec)", color='r')
    ax2.tick_params(axis='y', labelcolor='r')

    plt.title("Perbandingan Latency dan Throughput")
    fig.tight_layout()
    plt.savefig("performance_eval.png")
    print("✓ Grafik disimpan sebagai performance_eval.png")
