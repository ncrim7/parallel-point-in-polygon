import os
import subprocess
import sys
import multiprocessing
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Matplotlib high-quality config
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#EEEEEE'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['savefig.dpi'] = 200

def compile_cpp():
    print("Compiling C++ code with AVX2 and OpenMP (-fopenmp -mavx2 -O3)...")
    cpp_file = os.path.join("src", "pip_parallel.cpp")
    exe_file = "pip_parallel.exe" if os.name == 'nt' else "pip_parallel"
    
    cmd = ["g++", "-O3", "-fopenmp", "-mavx2", cpp_file, "-o", exe_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Compilation FAILED:")
        print(result.stderr)
        sys.exit(1)
    print("Compilation successful!")
    return exe_file

def run_cmd(exe, args):
    cmd = [os.path.join(".", exe)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        print(result.stderr)
        return None
    return result.stdout.strip()

def run_benchmarks(exe):
    max_cores = multiprocessing.cpu_count()
    print(f"Detected {max_cores} logical CPU cores.")
    
    # Threads to test: 1, 2, 4, 8, 12, 16 (or up to max_cores)
    thread_counts = [1, 2, 4, 8]
    if max_cores >= 12:
        thread_counts.append(12)
    if max_cores >= 16:
        thread_counts.append(16)
    if max_cores not in thread_counts:
        thread_counts.append(max_cores)
    thread_counts = sorted(list(set(thread_counts)))
    
    print(f"Threads to benchmark: {thread_counts}")
    
    repeats = 5
    
    # ----------------------------------------------------
    # BENCHMARK 1: Single Point, Massive Polygon (N=10M)
    # ----------------------------------------------------
    print("\n--- Running Benchmark 1: Single Point, Massive Polygon ---")
    single_results = []
    N_A = 10000000
    print(f"Polygon Size N = {N_A:,} (repeats = {repeats})")
    for t in thread_counts:
        seq_naive_t = []
        omp_naive_t = []
        avx_naive_t = []
        avx_omp_naive_t = []
        bvh_lookup_t = []
        
        for r in range(repeats):
            out = run_cmd(exe, ["--mode", "single", "--N", str(N_A), "--threads", str(t)])
            if out:
                # Output: N, Threads, SeqNaiveMs, OmpNaiveMs, AvxNaiveMs, AvxOmpNaiveMs, BvhLookupMs
                parts = out.split(",")
                if len(parts) == 7:
                    seq_naive_t.append(float(parts[2]))
                    omp_naive_t.append(float(parts[3]))
                    avx_naive_t.append(float(parts[4]))
                    avx_omp_naive_t.append(float(parts[5]))
                    bvh_lookup_t.append(float(parts[6]))
        
        avg_seq = np.mean(seq_naive_t)
        avg_omp = np.mean(omp_naive_t)
        avg_avx = np.mean(avx_naive_t)
        avg_avx_omp = np.mean(avx_omp_naive_t)
        avg_bvh = np.mean(bvh_lookup_t)
        
        print(f"  Threads: {t:2d} | Seq: {avg_seq:7.2f}ms | OMP: {avg_omp:7.2f}ms | AVX: {avg_avx:7.2f}ms | AVX+OMP: {avg_avx_omp:7.2f}ms | BVH: {avg_bvh:9.5f}ms")
        
        single_results.append({
            'N': N_A, 'Threads': t, 
            'SeqNaiveMs': avg_seq, 'OmpNaiveMs': avg_omp, 
            'AvxNaiveMs': avg_avx, 'AvxOmpNaiveMs': avg_avx_omp, 'BvhLookupMs': avg_bvh
        })
    df_single = pd.DataFrame(single_results)
    df_single.to_csv("benchmark_single_results.csv", index=False)

    # ----------------------------------------------------
    # BENCHMARK 2: Multiple Points Query (N=100k, M=100k)
    # ----------------------------------------------------
    print("\n--- Running Benchmark 2: Multiple Points Query ---")
    multi_results = []
    N_B = 100000
    M_B = 100000
    repeats_B = 3
    print(f"Polygon N = {N_B:,}, Query Points M = {M_B:,} (repeats = {repeats_B})")
    for t in thread_counts:
        seq_naive_t = []
        omp_naive_t = []
        seq_bvh_t = []
        omp_bvh_t = []
        
        for r in range(repeats_B):
            out = run_cmd(exe, ["--mode", "multi", "--N", str(N_B), "--M", str(M_B), "--threads", str(t)])
            if out:
                # Output: N, M, Threads, SeqNaiveMs, OmpNaiveMs, SeqBvhMs, OmpBvhMs
                parts = out.split(",")
                if len(parts) == 7:
                    seq_naive_t.append(float(parts[3]))
                    omp_naive_t.append(float(parts[4]))
                    seq_bvh_t.append(float(parts[5]))
                    omp_bvh_t.append(float(parts[6]))
        
        avg_seq = np.mean(seq_naive_t)
        avg_omp = np.mean(omp_naive_t)
        avg_seq_bvh = np.mean(seq_bvh_t)
        avg_omp_bvh = np.mean(omp_bvh_t)
        
        print(f"  Threads: {t:2d} | Seq Naive: {avg_seq:8.2f}ms | OMP Naive: {avg_omp:8.2f}ms | Seq BVH: {avg_seq_bvh:6.2f}ms | OMP BVH: {avg_omp_bvh:6.2f}ms")
        
        multi_results.append({
            'N': N_B, 'M': M_B, 'Threads': t,
            'SeqNaiveMs': avg_seq, 'OmpNaiveMs': avg_omp,
            'SeqBvhMs': avg_seq_bvh, 'OmpBvhMs': avg_omp_bvh
        })
    df_multi = pd.DataFrame(multi_results)
    df_multi.to_csv("benchmark_multi_results.csv", index=False)

    # ----------------------------------------------------
    # BENCHMARK 3: BVH Build Parallelism (N=10M)
    # ----------------------------------------------------
    print("\n--- Running Benchmark 3: BVH Parallel Build ---")
    build_results = []
    N_C = 10000000
    print(f"Polygon N = {N_C:,} for BVH build")
    for t in thread_counts:
        out = run_cmd(exe, ["--mode", "build", "--N", str(N_C), "--threads", str(t)])
        if out:
            # Output: N, Threads, SeqBuildMs, ParBuildMs, BuildSpeedup
            parts = out.split(",")
            if len(parts) == 5:
                seq_b = float(parts[2])
                par_b = float(parts[3])
                sp = float(parts[4])
                print(f"  Threads: {t:2d} | Seq Build: {seq_b:8.2f}ms | Parallel Build: {par_b:8.2f}ms | Speedup: {sp:.2f}x")
                build_results.append({
                    'N': N_C, 'Threads': t,
                    'SeqBuildMs': seq_b, 'ParBuildMs': par_b, 'BuildSpeedup': sp
                })
    df_build = pd.DataFrame(build_results)
    df_build.to_csv("benchmark_build_results.csv", index=False)
    
    return df_single, df_multi, df_build

def generate_plots(df_single, df_multi, df_build):
    os.makedirs("plots", exist_ok=True)
    threads = sorted(df_single['Threads'].unique())
    
    # 1. Plot: Speedups for Single Query (Massive Polygon)
    plt.figure()
    plt.plot(threads, threads, '--', color='gray', alpha=0.7, label='İdeal Hızlanma (Lineer)')
    
    # Calculate speedup relative to SeqNaiveMs
    seq_naive_time = df_single['SeqNaiveMs'].iloc[0]
    
    omp_speedup = seq_naive_time / df_single['OmpNaiveMs']
    avx_speedup = seq_naive_time / df_single['AvxNaiveMs']
    avx_omp_speedup = seq_naive_time / df_single['AvxOmpNaiveMs']
    
    plt.plot(df_single['Threads'], omp_speedup, 'o-', color='#3498DB', linewidth=2, label='OpenMP Naive (Kenar)')
    plt.plot(df_single['Threads'], avx_speedup, 's-', color='#E67E22', linewidth=2, label='AVX2 SIMD Naive')
    plt.plot(df_single['Threads'], avx_omp_speedup, 'd-', color='#2ECC71', linewidth=2, label='AVX2 + OpenMP Naive')
    
    plt.title("Kenar Seviyesi Paralelleştirme Hızlanma Grafiği (N = 10,000,000)")
    plt.xlabel("İş Parçacığı Sayısı (Threads)")
    plt.ylabel("Hızlanma Katsayısı (Speedup vs Sıralı)")
    plt.xticks(threads)
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join("plots", "speedup_single_query.png"))
    plt.close()
    
    # 2. Plot: Speedups for Multiple Queries (N=100k, M=100k)
    plt.figure()
    plt.plot(threads, threads, '--', color='gray', alpha=0.7, label='İdeal Hızlanma (Lineer)')
    
    seq_naive_m = df_multi['SeqNaiveMs'].iloc[0]
    seq_bvh_m = df_multi['SeqBvhMs'].iloc[0]
    
    omp_naive_speedup = seq_naive_m / df_multi['OmpNaiveMs']
    omp_bvh_speedup = seq_bvh_m / df_multi['OmpBvhMs']
    
    plt.plot(df_multi['Threads'], omp_naive_speedup, 'o-', color='#D9534F', linewidth=2, label='OpenMP Naive (Nokta)')
    plt.plot(df_multi['Threads'], omp_bvh_speedup, '^-', color='#9B59B6', linewidth=2, label='OpenMP BVH İndeksli (Nokta)')
    
    plt.title("Çoklu Nokta Sorgusu Hızlanma Grafiği (N=100,000, M=100,000)")
    plt.xlabel("İş Parçacığı Sayısı (Threads)")
    plt.ylabel("Hızlanma Katsayısı (Speedup)")
    plt.xticks(threads)
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join("plots", "speedup_multi_query.png"))
    plt.close()

    # 3. Plot: Logarithmic Execution Time comparison (Single Point query)
    plt.figure()
    # We display time for 8 threads
    row_8 = df_single[df_single['Threads'] == 8].iloc[0] if 8 in threads else df_single.iloc[-1]
    
    labels = ['Sıralı Naive', 'OpenMP Naive (8T)', 'AVX2 Naive', 'AVX2+OMP (8T)', 'BVH İndeks Lookup']
    times = [row_8['SeqTime'] if 'SeqTime' in row_8 else row_8['SeqNaiveMs'], 
             row_8['OmpNaiveMs'], 
             row_8['AvxNaiveMs'], 
             row_8['AvxOmpNaiveMs'], 
             row_8['BvhLookupMs']]
    
    bars = plt.bar(labels, times, color=['#E74C3C', '#3498DB', '#E67E22', '#2ECC71', '#9B59B6'])
    plt.yscale('log')
    plt.ylabel("Çalışma Süresi (milisaniye) - Logaritmik Ölçek")
    plt.title("Tek Nokta Sorgusu Yöntem Karşılaştırması (N = 10,000,000)")
    plt.grid(axis='y', which='both', linestyle='--', alpha=0.5)
    
    # Annotate times on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height * 1.1,
                 f"{height:.4f} ms" if height < 0.1 else f"{height:.2f} ms",
                 ha='center', va='bottom', fontsize=9)
                 
    plt.tight_layout()
    plt.savefig(os.path.join("plots", "time_comparison_single.png"))
    plt.close()

    # 4. Plot: Logarithmic Execution Time comparison (Multi Point query M=100k, N=100k)
    plt.figure()
    row_m_8 = df_multi[df_multi['Threads'] == 8].iloc[0] if 8 in threads else df_multi.iloc[-1]
    
    labels_m = ['Sıralı Naive', 'OpenMP Naive (8T)', 'Sıralı BVH İndeks', 'OpenMP BVH (8T)']
    times_m = [row_m_8['SeqNaiveMs'], row_m_8['OmpNaiveMs'], row_m_8['SeqBvhMs'], row_m_8['OmpBvhMs']]
    
    bars_m = plt.bar(labels_m, times_m, color=['#E74C3C', '#D9534F', '#1ABC9C', '#9B59B6'])
    plt.yscale('log')
    plt.ylabel("Çalışma Süresi (milisaniye) - Logaritmik Ölçek")
    plt.title("Çoklu Nokta Sorgusu Yöntem Karşılaştırması (N=100k, M=100k)")
    plt.grid(axis='y', which='both', linestyle='--', alpha=0.5)
    
    for bar in bars_m:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height * 1.1,
                 f"{height:.2f} ms", ha='center', va='bottom', fontsize=9)
                 
    plt.tight_layout()
    plt.savefig(os.path.join("plots", "time_comparison_multi.png"))
    plt.close()

    # 5. Plot: BVH parallel build speedup
    plt.figure()
    plt.plot(threads, threads, '--', color='gray', alpha=0.7, label='İdeal Hızlanma (Lineer)')
    plt.plot(df_build['Threads'], df_build['BuildSpeedup'], 'o-', color='#1ABC9C', linewidth=2, label='Görev Tabanlı (Task) Paralel İnşa')
    
    plt.title("Görev Tabanlı (OMP Task) Paralel BVH İnşa Hızlanması (N = 10,000,000)")
    plt.xlabel("İş Parçacığı Sayısı (Threads)")
    plt.ylabel("Hızlanma Katsayısı (Speedup)")
    plt.xticks(threads)
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join("plots", "bvh_build_speedup.png"))
    plt.close()
    
    print("\nBenchmark grafikleri 'plots/' dizinine kaydedildi:")
    print("  - plots/speedup_single_query.png")
    print("  - plots/speedup_multi_query.png")
    print("  - plots/time_comparison_single.png")
    print("  - plots/time_comparison_multi.png")
    print("  - plots/bvh_build_speedup.png")

def generate_visualization(exe):
    vis_file = "vis_data.txt"
    run_cmd(exe, ["--mode", "export", "--N", "200", "--M", "500", "--export", vis_file])
    
    if not os.path.exists(vis_file):
        return

    polygon_pts = []
    inside_pts = []
    outside_pts = []
    
    with open(vis_file, "r") as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        if line.startswith("POLYGON"):
            n = int(line.split()[1])
            for _ in range(n):
                i += 1
                pt_parts = lines[i].strip().split()
                polygon_pts.append((float(pt_parts[0]), float(pt_parts[1])))
        elif line.startswith("POINTS"):
            m = int(line.split()[1])
            for _ in range(m):
                i += 1
                pt_parts = lines[i].strip().split()
                x = float(pt_parts[0])
                y = float(pt_parts[1])
                inside = int(pt_parts[2])
                if inside:
                    inside_pts.append((x, y))
                else:
                    outside_pts.append((x, y))
        i += 1
        
    try:
        os.remove(vis_file)
    except OSError:
        pass

    plt.figure(figsize=(8, 8))
    poly_x = [pt[0] for pt in polygon_pts] + [polygon_pts[0][0]]
    poly_y = [pt[1] for pt in polygon_pts] + [polygon_pts[0][1]]
    
    plt.plot(poly_x, poly_y, '-', color='#2C3E50', linewidth=2, label='Poligon Sınırı (Concave)')
    plt.fill(poly_x, poly_y, color='#ECF0F1', alpha=0.4)
    
    if inside_pts:
        in_x = [pt[0] for pt in inside_pts]
        in_y = [pt[1] for pt in inside_pts]
        plt.scatter(in_x, in_y, color='#2ECC71', s=30, edgecolors='none', label='Poligonun İÇİNDEKİ Noktalar')
        
    if outside_pts:
        out_x = [pt[0] for pt in outside_pts]
        out_y = [pt[1] for pt in outside_pts]
        plt.scatter(out_x, out_y, color='#E74C3C', s=30, edgecolors='none', label='Poligonun DIŞINDAKİ Noktalar')
        
    plt.title("Ray-Casting Algoritması ile Nokta Tespiti Görselleştirmesi", fontsize=12, pad=15)
    plt.xlabel("X Koordinatı")
    plt.ylabel("Y Koordinatı")
    plt.axhline(0, color='gray', linestyle=':', linewidth=0.5)
    plt.axvline(0, color='gray', linestyle=':', linewidth=0.5)
    plt.legend(loc='upper right')
    plt.axis('equal')
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.savefig(os.path.join("plots", "polygon_visualization.png"), bbox_inches='tight')
    plt.close()
    print("Poligon görselleştirmesi kaydedildi: plots/polygon_visualization.png")

if __name__ == "__main__":
    exe = compile_cpp()
    df_single, df_multi, df_build = run_benchmarks(exe)
    generate_plots(df_single, df_multi, df_build)
    generate_visualization(exe)
    print("\nAll V2 tasks completed successfully! Ready to generate the updated report.")
