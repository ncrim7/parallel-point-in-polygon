import os
import sys
import subprocess
import random
import customtkinter as ctk
from PIL import Image, ImageTk

# Set theme and color options
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class PIPSolverGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Parallel Point-in-Polygon (PIP) GIS Solver")
        self.geometry("1100x750")
        
        # State variables for Sandbox Mode
        self.poly_vertices = []
        self.poly_closed = False
        self.canvas_width = 700
        self.canvas_height = 500
        
        # Grid layout configuration: 2 columns, 1 row
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. Sidebar (Left panel)
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PIP GIS SOLVER", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.sub_label = ctk.CTkLabel(self.sidebar_frame, text="OpenMP & AVX2 SIMD Core", font=ctk.CTkFont(size=11, slant="italic"))
        self.sub_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Sidebar Mode selector
        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text="Çalışma Modu:", anchor="w")
        self.mode_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.mode_option = ctk.CTkOptionMenu(self.sidebar_frame, values=["İnteraktif Çizim (Sandbox)", "Performans Dashboard"], command=self.change_mode)
        self.mode_option.grid(row=3, column=0, padx=20, pady=10)
        
        # Thread slider
        self.threads_label = ctk.CTkLabel(self.sidebar_frame, text="Thread Sayısı: 4", anchor="w")
        self.threads_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")
        max_cores = os.cpu_count() or 4
        self.threads_slider = ctk.CTkSlider(self.sidebar_frame, from_=1, to=max_cores, number_of_steps=max_cores-1, command=self.update_threads_label)
        self.threads_slider.set(4)
        self.threads_slider.grid(row=5, column=0, padx=20, pady=10)
        
        # Footer
        self.footer_label = ctk.CTkLabel(self.sidebar_frame, text="Parallel Programming Term Project\nVersion 2.0 (V2)", font=ctk.CTkFont(size=10))
        self.footer_label.grid(row=7, column=0, padx=20, pady=20)
        
        # 2. Main Content Frame (Right panel)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Initialize the Modes
        self.init_sandbox_mode()
        self.init_dashboard_mode()
        
        # Show default Sandbox Mode
        self.change_mode("İnteraktif Çizim (Sandbox)")

    def change_mode(self, mode):
        if mode == "İnteraktif Çizim (Sandbox)":
            self.dashboard_container.grid_forget()
            self.sandbox_container.grid(row=0, column=0, sticky="nsew")
        else:
            self.sandbox_container.grid_forget()
            self.dashboard_container.grid(row=0, column=0, sticky="nsew")

    def update_threads_label(self, val):
        self.threads_label.configure(text=f"Thread Sayısı: {int(val)}")

    # -------------------------------------------------------------------------
    # SANDBOX MODE (Interactive Canvas)
    # -------------------------------------------------------------------------
    def init_sandbox_mode(self):
        self.sandbox_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.sandbox_container.grid_columnconfigure(0, weight=1)
        self.sandbox_container.grid_rowconfigure(1, weight=1)
        
        # Top banner info
        self.info_lbl = ctk.CTkLabel(self.sandbox_container, text="Tuvale tıklayarak poligon çizin. Kapatmak için çift tıklayın. Kapandıktan sonra tıklayarak nokta sorgulayın.", font=ctk.CTkFont(size=12))
        self.info_lbl.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Canvas frame
        self.canvas_frame = ctk.CTkFrame(self.sandbox_container, corner_radius=10)
        self.canvas_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        
        # Actual Tkinter Canvas
        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="#212529", bd=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Mouse Bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        
        # Control Buttons under canvas
        self.sandbox_ctrl = ctk.CTkFrame(self.sandbox_container, fg_color="transparent")
        self.sandbox_ctrl.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        self.btn_clear = ctk.CTkButton(self.sandbox_ctrl, text="Temizle", command=self.clear_sandbox, width=120)
        self.btn_clear.pack(side="left", padx=5)
        
        self.btn_scatter = ctk.CTkButton(self.sandbox_ctrl, text="1000 Nokta Serpiştir", command=self.scatter_points, width=180, state="disabled")
        self.btn_scatter.pack(side="left", padx=5)
        
        self.status_lbl = ctk.CTkLabel(self.sandbox_ctrl, text="Durum: Çizim yapılıyor...", font=ctk.CTkFont(weight="bold"))
        self.status_lbl.pack(side="right", padx=10)

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        
        if not self.poly_closed:
            # Drawing mode
            self.poly_vertices.append((x, y))
            # Draw point
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="#3498DB", outline="")
            
            # Connect with line
            n = len(self.poly_vertices)
            if n > 1:
                p1 = self.poly_vertices[n-2]
                p2 = self.poly_vertices[n-1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#3498DB", width=2, tags="poly_line")
        else:
            # Test Point mode
            inside = self.point_in_polygon_test(x, y, self.poly_vertices)
            color = "#2ECC71" if inside else "#E74C3C" # Green if inside, Red if outside
            self.canvas.create_oval(x-4, y-4, x+4, y+4, fill=color, outline="white", width=1)
            
            status = "İÇİNDE" if inside else "DIŞINDA"
            self.status_lbl.configure(text=f"Nokta ({x}, {y}): {status}")

    def on_canvas_double_click(self, event):
        if len(self.poly_vertices) >= 3 and not self.poly_closed:
            # Close polygon
            p1 = self.poly_vertices[-1]
            p2 = self.poly_vertices[0]
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#2C3E50", width=3, tags="poly_line")
            self.poly_closed = True
            
            # Redraw entire border with thick closed color
            for idx in range(len(self.poly_vertices)):
                pt1 = self.poly_vertices[idx]
                pt2 = self.poly_vertices[(idx + 1) % len(self.poly_vertices)]
                self.canvas.create_line(pt1[0], pt1[1], pt2[0], pt2[1], fill="#2C3E50", width=3, tags="closed_poly_line")
                
            self.btn_scatter.configure(state="normal")
            self.status_lbl.configure(text="Durum: Poligon Kapatıldı! Nokta test edebilirsiniz.")

    def clear_sandbox(self):
        self.canvas.delete("all")
        self.poly_vertices = []
        self.poly_closed = False
        self.btn_scatter.configure(state="disabled")
        self.status_lbl.configure(text="Durum: Çizim yapılıyor...")

    def scatter_points(self):
        if not self.poly_closed or not self.poly_vertices:
            return
            
        # Find Bounding Box
        xs = [pt[0] for pt in self.poly_vertices]
        ys = [pt[1] for pt in self.poly_vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        import time
        start_t = time.perf_counter()
        
        # Test 1000 random points inside BBox
        for _ in range(1000):
            rx = random.uniform(min_x - 10, max_x + 10)
            ry = random.uniform(min_y - 10, max_y + 10)
            inside = self.point_in_polygon_test(rx, ry, self.poly_vertices)
            color = "#2ECC71" if inside else "#E74C3C"
            self.canvas.create_oval(rx-2, ry-2, rx+2, ry+2, fill=color, outline="")
            
        end_t = time.perf_counter()
        dur_ms = (end_t - start_t) * 1000.0
        self.status_lbl.configure(text=f"1000 Nokta Serpiştirildi | Süre: {dur_ms:.2f} ms")

    def point_in_polygon_test(self, px, py, poly):
        # Ray casting in Python for instant Sandbox visualization
        inside = False
        n = len(poly)
        for i in range(n):
            p1 = poly[i]
            p2 = poly[(i + 1) % n]
            if ((p1[1] > py) != (p2[1] > py)):
                intersectX = p1[0] + (py - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                if px < intersectX:
                    inside = not inside
        return inside

    # -------------------------------------------------------------------------
    # PERFORMANCE DASHBOARD MODE
    # -------------------------------------------------------------------------
    def init_dashboard_mode(self):
        self.dashboard_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.dashboard_container.grid_columnconfigure(0, weight=1)
        self.dashboard_container.grid_rowconfigure(1, weight=1)
        
        # Controls panel top
        self.ctrl_panel = ctk.CTkFrame(self.dashboard_container)
        self.ctrl_panel.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # N input
        self.lbl_N = ctk.CTkLabel(self.ctrl_panel, text="Poligon Kenarı (N):")
        self.lbl_N.grid(row=0, column=0, padx=10, pady=10)
        self.entry_N = ctk.CTkEntry(self.ctrl_panel, placeholder_text="1000000", width=120)
        self.entry_N.insert(0, "1000000")
        self.entry_N.grid(row=0, column=1, padx=10, pady=10)
        
        # M input
        self.lbl_M = ctk.CTkLabel(self.ctrl_panel, text="Nokta Sayısı (M):")
        self.lbl_M.grid(row=0, column=2, padx=10, pady=10)
        self.entry_M = ctk.CTkEntry(self.ctrl_panel, placeholder_text="100000", width=120)
        self.entry_M.insert(0, "100000")
        self.entry_M.grid(row=0, column=3, padx=10, pady=10)
        
        # Start button
        self.btn_run_bench = ctk.CTkButton(self.ctrl_panel, text="Benchmark Çalıştır", command=self.run_benchmark_gui, width=150, fg_color="#1ABC9C", hover_color="#16A085")
        self.btn_run_bench.grid(row=0, column=4, padx=20, pady=10)
        
        # Display Panel for results
        self.display_panel = ctk.CTkFrame(self.dashboard_container, corner_radius=10)
        self.display_panel.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.display_panel.grid_columnconfigure(0, weight=1)
        self.display_panel.grid_rowconfigure(0, weight=1)
        
        # Log Output / Chart Display Area
        self.tabview = ctk.CTkTabview(self.display_panel)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Ölçüm Sonuçları")
        self.tabview.add("Hızlanma Eğrileri")
        self.tabview.add("Zaman Karşılaştırma")
        
        # Textbox for logs
        self.log_txt = ctk.CTkTextbox(self.tabview.tab("Ölçüm Sonuçları"), font=ctk.CTkFont(size=12, family="Consolas"))
        self.log_txt.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_txt.insert("0.0", "Benchmark sonuçları burada görüntülenecektir.\nParametreleri seçip 'Benchmark Çalıştır' butonuna tıklayınız.\nGrafikler test sonrasında otomatik yüklenecektir.\n")
        
        # Labels for embedded PNG charts
        self.chart1_label = ctk.CTkLabel(self.tabview.tab("Hızlanma Eğrileri"), text="Önce testi çalıştırın")
        self.chart1_label.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.chart2_label = ctk.CTkLabel(self.tabview.tab("Zaman Karşılaştırma"), text="Önce testi çalıştırın")
        self.chart2_label.pack(fill="both", expand=True, padx=5, pady=5)

    def log(self, text):
        self.log_txt.insert("end", text + "\n")
        self.log_txt.see("end")

    def run_benchmark_gui(self):
        # Run execution in a separate background thread/process or just run with loading label
        self.btn_run_bench.configure(state="disabled", text="Çalışıyor...")
        self.log_txt.delete("0.0", "end")
        self.log("Benchmark başlatıldı. Lütfen bekleyiniz...")
        
        N_val = self.entry_N.get()
        M_val = self.entry_M.get()
        T_val = int(self.threads_slider.get())
        
        # We will run this sequentially or spawn thread. Let's use root.after to run it synchronously but keep window alive, or just run subprocess.
        self.after(100, lambda: self.execute_benchmark(N_val, M_val, T_val))

    def execute_benchmark(self, N, M, T):
        exe_file = "pip_parallel.exe" if os.name == 'nt' else "pip_parallel"
        
        if not os.path.exists(exe_file):
            self.log(f"Hata: {exe_file} derlenmiş dosyası bulunamadı. Derleniyor...")
            # Attempt to compile
            cmd = ["g++", "-O3", "-fopenmp", "-mavx2", "src/pip_parallel.cpp", "-o", exe_file]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                self.log(f"Derleme FAILED:\n{res.stderr}")
                self.btn_run_bench.configure(state="normal", text="Benchmark Çalıştır")
                return
            self.log("Derleme Başarılı!")
            
        # 1. Benchmark Single Point (N vertices)
        self.log(f"--- Senaryo A: Tek Nokta Sorgusu (N = {N}) ---")
        cmd_a = [f"./{exe_file}", "--mode", "single", "--N", str(N), "--threads", str(T)]
        res_a = subprocess.run(cmd_a, capture_output=True, text=True, shell=True)
        if res_a.returncode == 0 and res_a.stdout:
            # Output: N, Threads, SeqNaiveMs, OmpNaiveMs, AvxNaiveMs, AvxOmpNaiveMs, BvhLookupMs
            parts = res_a.stdout.strip().split(",")
            if len(parts) == 7:
                self.log(f"  Sıralı Naive Süre  : {float(parts[2]):.2f} ms")
                self.log(f"  OpenMP Naive Süre  : {float(parts[3]):.2f} ms")
                self.log(f"  AVX2 SIMD Süre     : {float(parts[4]):.2f} ms")
                self.log(f"  AVX2+OMP Naive Süre: {float(parts[5]):.2f} ms")
                self.log(f"  BVH Lookup Süre    : {float(parts[6]):.6f} ms  <-- EN HIZLI (O(log N))")
        else:
            self.log(f"Senaryo A başarısız: {res_a.stderr}")

        # 2. Benchmark Multiple Points
        self.log(f"\n--- Senaryo B: Çoklu Nokta Sorgusu (N = {N}, M = {M}) ---")
        cmd_b = [f"./{exe_file}", "--mode", "multi", "--N", str(N), "--M", str(M), "--threads", str(T)]
        res_b = subprocess.run(cmd_b, capture_output=True, text=True, shell=True)
        if res_b.returncode == 0 and res_b.stdout:
            # Output: N, M, Threads, SeqNaiveMs, OmpNaiveMs, SeqBvhMs, OmpBvhMs
            parts = res_b.stdout.strip().split(",")
            if len(parts) == 7:
                self.log(f"  Sıralı Naive Süre : {float(parts[3]):.2f} ms")
                self.log(f"  OpenMP Naive Süre : {float(parts[4]):.2f} ms")
                self.log(f"  Sıralı BVH Süre   : {float(parts[5]):.2f} ms")
                self.log(f"  OpenMP BVH Süre   : {float(parts[6]):.2f} ms  <-- EN HIZLI (O(M log N) + Omp)")
                
                seq_naive = float(parts[3])
                omp_bvh = float(parts[6])
                if omp_bvh > 0:
                    total_speedup = seq_naive / omp_bvh
                    self.log(f"\n  Toplam Paralel+İndeks Hızlanması: {total_speedup:.2f}x")
        else:
            self.log(f"Senaryo B başarısız: {res_b.stderr}")
            
        # Re-run benchmark plotting to update graphs for these specific parameters!
        self.log("\nGrafikler güncelleniyor...")
        subprocess.run([sys.executable, "benchmark.py"])
        
        # Load and display the generated PNG plots in GUI tabs
        self.load_charts_to_gui()
        
        self.log("\nBenchmark tamamlandı! 'Hızlanma Eğrileri' ve 'Zaman Karşılaştırma' sekmelerine tıklayarak grafikleri inceleyebilirsiniz.")
        self.btn_run_bench.configure(state="normal", text="Benchmark Çalıştır")

    def load_charts_to_gui(self):
        # Load plots/speedup_multi_query.png and plots/time_comparison_multi.png
        path1 = os.path.join("plots", "speedup_multi_query.png")
        path2 = os.path.join("plots", "time_comparison_multi.png")
        
        # Limit image size to fit tab frame
        w, h = 650, 400
        
        if os.path.exists(path1):
            img1 = Image.open(path1).resize((w, h), Image.Resampling.LANCZOS)
            ctk_img1 = ctk.CTkImage(light_image=img1, dark_image=img1, size=(w, h))
            self.chart1_label.configure(image=ctk_img1, text="")
            self.chart1_label.image = ctk_img1 # Keep reference
            
        if os.path.exists(path2):
            img2 = Image.open(path2).resize((w, h), Image.Resampling.LANCZOS)
            ctk_img2 = ctk.CTkImage(light_image=img2, dark_image=img2, size=(w, h))
            self.chart2_label.configure(image=ctk_img2, text="")
            self.chart2_label.image = ctk_img2 # Keep reference


if __name__ == "__main__":
    app = PIPSolverGUI()
    app.mainloop()
