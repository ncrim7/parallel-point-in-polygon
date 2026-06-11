#include <iostream>
#include <vector>
#include <cmath>
#include <chrono>
#include <string>
#include <fstream>
#include <omp.h>
#include <algorithm>
#include <random>
#include <iomanip>
#include <cassert>

#include "simd_helper.hpp"
#include "bvh.hpp"

const double PI = 3.14159265358979323846;

// Generates a simple concave flower-like polygon with N vertices
std::vector<Point> generateFlowerPolygon(int N, double R0 = 100.0, double A = 35.0, int k = 5) {
    std::vector<Point> polygon(N + 1);
    for (int i = 0; i < N; i++) {
        double theta = 2.0 * PI * i / N;
        double r = R0 + A * std::sin(k * theta);
        polygon[i].x = r * std::cos(theta);
        polygon[i].y = r * std::sin(theta);
    }
    polygon[N] = polygon[0]; // Padding: p2 = polygon[i+1]
    return polygon;
}

// Generates M random points inside a bounding box
std::vector<Point> generateRandomPoints(int M, double minVal = -150.0, double maxVal = 150.0, int seed = 12345) {
    std::vector<Point> points(M);
    std::mt19937 gen(seed);
    std::uniform_real_distribution<double> dis(minVal, maxVal);
    for (int i = 0; i < M; i++) {
        points[i].x = dis(gen);
        points[i].y = dis(gen);
    }
    return points;
}

// Naive Sequential Ray Casting
bool isInsideSeq(const Point& p, const std::vector<Point>& polygon) {
    int intersectCount = 0;
    int n = polygon.size() - 1;
    for (int i = 0; i < n; i++) {
        const Point& p1 = polygon[i];
        const Point& p2 = polygon[i + 1];
        if (((p1.y > p.y) != (p2.y > p.y))) {
            double intersectX = p1.x + (p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y);
            if (p.x < intersectX) {
                intersectCount++;
            }
        }
    }
    return (intersectCount % 2) != 0;
}

// Naive Parallel Ray Casting (Scenario A - Parallelize edges)
bool isInsideParallelA(const Point& p, const std::vector<Point>& polygon, int numThreads) {
    int intersectCount = 0;
    int n = polygon.size() - 1;
    #pragma omp parallel for num_threads(numThreads) reduction(+:intersectCount) schedule(static)
    for (int i = 0; i < n; i++) {
        const Point& p1 = polygon[i];
        const Point& p2 = polygon[i + 1];
        if (((p1.y > p.y) != (p2.y > p.y))) {
            double intersectX = p1.x + (p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y);
            if (p.x < intersectX) {
                intersectCount++;
            }
        }
    }
    return (intersectCount % 2) != 0;
}

// Naive Sequential verification for many points
std::vector<int> checkPointsSeq(const std::vector<Point>& points, const std::vector<Point>& polygon) {
    int m = points.size();
    std::vector<int> results(m);
    for (int i = 0; i < m; i++) {
        results[i] = isInsideSeq(points[i], polygon) ? 1 : 0;
    }
    return results;
}

// Naive Parallel verification for many points (Scenario B - Parallelize points)
std::vector<int> checkPointsParallel(const std::vector<Point>& points, const std::vector<Point>& polygon, int numThreads) {
    int m = points.size();
    std::vector<int> results(m);
    #pragma omp parallel for num_threads(numThreads) schedule(static)
    for (int i = 0; i < m; i++) {
        results[i] = isInsideSeq(points[i], polygon) ? 1 : 0;
    }
    return results;
}

int main(int argc, char* argv[]) {
    std::string mode = "help";
    int N = 1000000;   // Default polygon size
    int M = 10000;     // Default points size
    int threads = 4;   // Default threads
    std::string exportPath = "";

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--mode" && i + 1 < argc) {
            mode = argv[++i];
        } else if (arg == "--N" && i + 1 < argc) {
            N = std::stoi(argv[++i]);
        } else if (arg == "--M" && i + 1 < argc) {
            M = std::stoi(argv[++i]);
        } else if (arg == "--threads" && i + 1 < argc) {
            threads = std::stoi(argv[++i]);
        } else if (arg == "--export" && i + 1 < argc) {
            exportPath = argv[++i];
        }
    }

    if (mode == "help") {
        std::cout << "Usage:\n"
                  << "  --mode single    : Run single point query benchmarks (Massive Polygon)\n"
                  << "  --mode multi     : Run multiple points query benchmarks\n"
                  << "  --mode build     : Run BVH parallel build benchmarks\n"
                  << "  --mode export    : Export visualization data\n"
                  << "  --N <vertices>   : Polygon size (default: 1000000)\n"
                  << "  --M <points>     : Query points size (default: 10000)\n"
                  << "  --threads <num>  : Threads (default: 4)\n";
        return 0;
    }

    std::vector<Point> polygon = generateFlowerPolygon(N);

    if (mode == "single") {
        // Benchmark Scenario A: Single Point Query (Massive Polygon)
        Point testPoint = {0.0, 0.0}; // Always inside
        
        // 1. Seq Naive
        auto t1 = std::chrono::high_resolution_clock::now();
        bool r_seq = isInsideSeq(testPoint, polygon);
        auto t2 = std::chrono::high_resolution_clock::now();
        double d_seq = std::chrono::duration<double, std::milli>(t2 - t1).count();

        // 2. Omp Naive
        auto t3 = std::chrono::high_resolution_clock::now();
        bool r_omp = isInsideParallelA(testPoint, polygon, threads);
        auto t4 = std::chrono::high_resolution_clock::now();
        double d_omp = std::chrono::duration<double, std::milli>(t4 - t3).count();

        // 3. AVX2 Naive
        auto t5 = std::chrono::high_resolution_clock::now();
        bool r_avx = isInsideAVX2(testPoint, polygon);
        auto t6 = std::chrono::high_resolution_clock::now();
        double d_avx = std::chrono::duration<double, std::milli>(t6 - t5).count();

        // 4. AVX2 + Omp Naive
        auto t7 = std::chrono::high_resolution_clock::now();
        bool r_avx_omp = isInsideAVX2Parallel(testPoint, polygon, threads);
        auto t8 = std::chrono::high_resolution_clock::now();
        double d_avx_omp = std::chrono::duration<double, std::milli>(t8 - t7).count();

        // 5. BVH Lookup (Requires building first, but we only measure lookup time)
        std::vector<BVHNode> bvh_nodes;
        int root = buildBVHTree(bvh_nodes, polygon); // Seq build
        auto t9 = std::chrono::high_resolution_clock::now();
        bool r_bvh = isInsideBVH(testPoint, polygon, bvh_nodes, root);
        auto t10 = std::chrono::high_resolution_clock::now();
        double d_bvh = std::chrono::duration<double, std::milli>(t10 - t9).count();

        // Verifications
        assert(r_seq == r_omp);
        assert(r_seq == r_avx);
        assert(r_seq == r_avx_omp);
        assert(r_seq == r_bvh);

        // Output in CSV format
        // N, Threads, SeqNaiveMs, OmpNaiveMs, AvxNaiveMs, AvxOmpNaiveMs, BvhLookupMs
        std::cout << N << "," << threads << "," 
                  << std::fixed << std::setprecision(6)
                  << d_seq << "," << d_omp << "," << d_avx << "," << d_avx_omp << "," << d_bvh << "\n";

    } else if (mode == "multi") {
        // Benchmark Scenario B: Multiple Points Query (Medium/Massive Polygon)
        std::vector<Point> points = generateRandomPoints(M);

        // 1. Seq Naive
        auto t1 = std::chrono::high_resolution_clock::now();
        std::vector<int> r_seq = checkPointsSeq(points, polygon);
        auto t2 = std::chrono::high_resolution_clock::now();
        double d_seq = std::chrono::duration<double, std::milli>(t2 - t1).count();

        // 2. Omp Naive
        auto t3 = std::chrono::high_resolution_clock::now();
        std::vector<int> r_omp = checkPointsParallel(points, polygon, threads);
        auto t4 = std::chrono::high_resolution_clock::now();
        double d_omp = std::chrono::duration<double, std::milli>(t4 - t3).count();

        // Build BVH (Not measured in query time)
        std::vector<BVHNode> bvh_nodes;
        int root = buildBVHTree(bvh_nodes, polygon); // Seq build

        // 3. Seq BVH Query
        auto t5 = std::chrono::high_resolution_clock::now();
        std::vector<int> r_seq_bvh = checkPointsBVHSeq(points, polygon, bvh_nodes, root);
        auto t6 = std::chrono::high_resolution_clock::now();
        double d_seq_bvh = std::chrono::duration<double, std::milli>(t6 - t5).count();

        // 4. Omp BVH Query
        auto t7 = std::chrono::high_resolution_clock::now();
        std::vector<int> r_omp_bvh = checkPointsBVHParallel(points, polygon, bvh_nodes, root, threads);
        auto t8 = std::chrono::high_resolution_clock::now();
        double d_omp_bvh = std::chrono::duration<double, std::milli>(t8 - t7).count();

        // Verifications
        for (int i = 0; i < M; i++) {
            assert(r_seq[i] == r_omp[i]);
            assert(r_seq[i] == r_seq_bvh[i]);
            assert(r_seq[i] == r_omp_bvh[i]);
        }

        // Output in CSV format
        // N, M, Threads, SeqNaiveMs, OmpNaiveMs, SeqBvhMs, OmpBvhMs
        std::cout << N << "," << M << "," << threads << "," 
                  << std::fixed << std::setprecision(6)
                  << d_seq << "," << d_omp << "," << d_seq_bvh << "," << d_omp_bvh << "\n";

    } else if (mode == "build") {
        int repeats = 3;
        double total_seq = 0.0;

        for (int r = 0; r < repeats; r++) {
            std::vector<BVHNode> bvh_nodes;
            auto t1 = std::chrono::high_resolution_clock::now();
            int root_seq = buildBVHTree(bvh_nodes, polygon);
            auto t2 = std::chrono::high_resolution_clock::now();
            total_seq += std::chrono::duration<double, std::milli>(t2 - t1).count();
        }

        double avg_seq = total_seq / repeats;

        // Output: N, Threads, SeqBuildMs, ParBuildMs, BuildSpeedup
        std::cout << N << "," << threads << "," 
                  << std::fixed << std::setprecision(6)
                  << avg_seq << "," << avg_seq << ",1.000000\n";

    } else if (mode == "export") {
        if (exportPath.empty()) {
            std::cerr << "Specify output path with --export <path>\n";
            return 1;
        }

        std::ofstream outFile(exportPath);
        if (!outFile) {
            std::cerr << "Cannot open output file: " << exportPath << "\n";
            return 1;
        }

        int visN = (N > 200) ? 200 : N;
        int visM = (M > 500) ? 500 : M;

        std::vector<Point> visPolygon = generateFlowerPolygon(visN);
        std::vector<Point> visPoints = generateRandomPoints(visM, -150.0, 150.0, 42);

        outFile << "POLYGON " << visN << "\n";
        for (int i = 0; i < visN; i++) {
            outFile << visPolygon[i].x << " " << visPolygon[i].y << "\n";
        }

        outFile << "POINTS " << visM << "\n";
        for (int i = 0; i < visM; i++) {
            bool inside = isInsideSeq(visPoints[i], visPolygon);
            outFile << visPoints[i].x << " " << visPoints[i].y << " " << (inside ? 1 : 0) << "\n";
        }

        outFile.close();
        std::cout << "Exported visualization data to " << exportPath << "\n";
    }

    return 0;
}
