# PARALEL PROGRAMLAMA PROJE SUNUM REHBERİ & DEMO SENARYOSU

Bu rehber, projenizin sunumunu (video kaydı veya canlı jüri sunumu) yaparken kullanmanız için hazırlanmıştır. Sunum konuşma metnini ve jüriyi en çok etkileyecek **Canlı Demo Gösterimi** adımlarını içerir.

---

## BÖLÜM 1: SUNUM KONUŞMA METNİ (SLAYT BY SLAYT)

### Giriş ve Proje Amacı (Slayt 1)
> **Ne Söyleyeceksiniz:**  
> "Merhabalar Sayın Hocam / Değerli Jüri Üyeleri. Bugün paralel programlama dersi final projesi kapsamında hazırladığımız 'Poligon İçinde Nokta Tespiti' yani 'Point-in-Polygon' probleminin paralel ve optimize çözümü sunumuna hoş geldiniz. 
> 
> Biz bu projede 4. Grubu seçtik. Amacımız; verilen karmaşık içbükey (concave) veya dışbükey (convex) bir poligon için, bir veya birden fazla noktanın bu poligonun içinde kalıp kalmadığını en yüksek performansla saptamaktır. Bu problem Coğrafi Bilgi Sistemlerinde (GIS), oyun motorlarındaki çarpışma testlerinde ve CAD yazılımlarında her saniye milyonlarca kez çalıştırılan en temel geometrik sorgulardan biridir."

### Algoritma ve Mantık: Ray-Casting (Slayt 2)
> **Ne Söyleyeceksiniz:**  
> "Problemin çözümünde Jordan Eğri Teoremi'ne dayanan **Ray-Casting (Işın Gönderme)** algoritmasını kullandık. Noktadan sağa doğru yatay sonsuz bir ışın çekiyoruz. Eğer ışın poligonun kenarlarını **tek sayıda** kesiyorsa nokta içeridedir, **çift sayıda** kesiyorsa dışarıdadır. 
> 
> Standart bir doğrusal döngüde bu algoritma poligonun tüm kenarlarını tek tek kontrol eder. Yani köşe sayısı $N$ olan bir poligon için arama karmaşıklığı doğrusal, yani $O(N)$'dir. Kenar sayısı milyonlara ulaştığında bu yöntem tek başına yetersiz kalır."

### Optimizasyon ve Paralel Çözüm Mimarisi (Slayt 3)
> **Ne Söyleyeceksiniz:**  
> "Bu doğrusal darboğazı aşmak için projemizde 3 aşamalı hibrit bir yüksek performanslı mimari geliştirdik:
> 
> 1. **Uzamsal İndeksleme (BVH - Bounding Volume Hierarchy):** Poligon kenarlarını sınırlayıcı kutularla ikili bir arama ağacına böldük. Arama sırasında ışının değmediği alt dalları tek seferde eleyerek (pruning) karmaşıklığı $O(N)$'den **$O(\log N)$**'e indirdik. Bellek yönetimini optimize etmek için L1 cache dostu, iteratif yığın tabanlı (stack-based) bir travers kodladık.
> 2. **Donanımsal Vektörleştirme (AVX2 SIMD):** CPU'nun 256-bit genişliğindeki yazmaçlarını kullanarak 4 kenarı aynı anda tek döngüde işleyen C++ intrinsics kodu yazdık.
> 3. **Çoklu Çekirdek Paralelliği (OpenMP):** Tek nokta sorgusunda poligon kenarlarını iş parçacıklarına bölerek reduction yaptık (Senaryo A). Çoklu nokta sorgularında ise noktaları dinamik yük dengelemeli (`schedule(dynamic, 64)`) olarak çekirdeklere dağıttık (Senaryo B)."

### Deneysel Bulgular ve Performans (Slayt 4)
> **Ne Söyleyeceksiniz:**  
> "Geliştirdiğimiz çözümleri 16 thread'li bir işlemci üzerinde benchmark testlerine tabi tuttuk ve çok çarpıcı sonuçlar elde ettik:
> 
> - **Tek Nokta Sorgusunda (N = 10.000.000 kenar):** Naive sıralı kod 14.30 ms sürerken, BVH indeks yapımız arama süresini **13.5 mikrosaniyeye** indirdi. Yani tam **1059 kat ($1059x$)** hızlanma elde ettik.
> - **Çoklu Nokta Sorgusunda (N = 100.000 kenar, M = 100.000 nokta):** Naive sıralı çözüm **8.68 saniye** sürerken, OpenMP + BVH paralel çözümümüz görevi sadece **3.78 milisaniyede** tamamladı.
> - Böylece paralel arama ve algoritmik indeks birleştiğinde en temel koda kıyasla **2296 kat ($2296x$) toplam hızlanma** elde ettik.
> - Ayrıca testlerde gördük ki; devasa veri setleri RAM bant genişliği darboğazına (Memory Wall) takılırken, önbelleğe sığan BVH sorguları OpenMP ile **15.05x** doğrusal ölçeklenerek mükemmele yakın bir paralel verim sunmaktadır."

---

## BÖLÜM 2: CANLI DEMO GÖSTERİM SENARYOSU (ADIM ADIM)

Sunumun sonunda jüriye uygulamayı canlı göstermek için şu adımları takip edin. Bu gösterim jüride büyük bir izlenim bırakacaktır:

### Adım 1: Arayüzü Başlatın ve Sandbox Çizimini Gösterin
1. Terminalden `python gui.py` yazarak arayüzü açın.
2. Ekranda sol tıklar ile **içbükey (concave) karmaşık bir yıldız veya labirent benzeri poligon** çizin (5-10 köşe yeterlidir).
3. Poligonu kapatmak için son köşe üzerinde **çift tıklayın** (Poligon sınır çizgileri kalınlaşacaktır).
4. **Jüriye Açıklama yapın:**  
   *"Şu anda Sandbox (Çizim) modundayız. Ekrana elle serbest içbükey bir poligon çizdik."*

### Adım 2: Canlı Nokta Sorgusu Yapın
1. Çizdiğiniz poligonun hem **içine** hem de **dışına** rastgele tıklamalar yapın.
2. Tıkladığınız noktalar anında poligonun içindeyse **Yeşil**, dışındaysa **Kırmızı** renge boyanacaktır.
3. Sağ alttaki durum çubuğunda test sürelerinin anlık (0.01 ms gibi) yazıldığını gösterin.
4. Sunucu yükü oluşturmadan anlık çizimi görselleştirin.

### Adım 3: Çoklu Nokta Serpiştirme (Scatter Testi)
1. Alt taraftaki **"1000 Nokta Serpiştir"** butonuna basın.
2. Saniyeler içinde poligonun etrafına 1000 adet renkli nokta serpilecektir. Noktalar poligon sınırını kusursuz şekilde çizecektir (içindekiler yeşil, dışındakiler kırmızı).
3. **Jüriye Açıklama yapın:**  
   *"1000 noktayı poligon sınırlarına göre milisaniyeler içinde sınıflandırdık. Bu, Ray-Casting algoritmamızın matematiksel ve geometrik doğruluğunun görsel bir kanıtıdır."*

### Adım 4: Performans Dashboard ve Grafik Gösterimi
1. Sol taraftaki "Çalışma Modu" seçeneğinden **"Performans Dashboard"** moduna geçin.
2. Parametreleri ayarlayın (örneğin varsayılan olarak $N = 1.000.000$, $M = 100.000$ ve Thread Sayısı = 8 olsun).
3. **"Benchmark Çalıştır"** butonuna basın.
4. Program arka planda derlenecek, testleri koşacak ve süreleri log ekranına yazacaktır:
   - Naive sürelerin saniyeler sürdüğünü, paralel BVH sürümünün ise milisaniyeler içinde (örn. 3-5 ms) tamamlandığını log ekranından jüriye okuyun.
5. Arayüzün sekmelerinden **"Hızlanma Eğrileri"** ve **"Zaman Karşılaştırma"** sekmelerine tıklayın.
6. CPU çekirdeklerimizin benchmark süresince nasıl ölçeklendiğini gösteren grafikleri arayüzün içinden jüriye sunarak sunumunuzu tamamlayın.
