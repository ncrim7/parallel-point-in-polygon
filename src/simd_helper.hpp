#pragma once
#include <vector>
#include <immintrin.h>
#include <omp.h>

// Struct definition to keep compiler happy if not included
#ifndef POINT_STRUCT
#define POINT_STRUCT
struct Point {
    double x;
    double y;
};
#endif

// AVX2 Vectorized Ray-Casting for a single point (processes 4 edges in parallel)
inline bool isInsideAVX2(const Point& p, const std::vector<Point>& polygon) {
    int intersectCount = 0;
    int n = polygon.size() - 1; // Actual number of vertices
    int n_simd = n - (n % 4);

    __m256d px_vec = _mm256_set1_pd(p.x);
    __m256d py_vec = _mm256_set1_pd(p.y);

    for (int i = 0; i < n_simd; i += 4) {
        // Load 4 edges' start coordinates (P1)
        __m256d p1x = _mm256_setr_pd(polygon[i].x, polygon[i+1].x, polygon[i+2].x, polygon[i+3].x);
        __m256d p1y = _mm256_setr_pd(polygon[i].y, polygon[i+1].y, polygon[i+2].y, polygon[i+3].y);

        // Load 4 edges' end coordinates (P2)
        __m256d p2x = _mm256_setr_pd(polygon[i+1].x, polygon[i+2].x, polygon[i+3].x, polygon[i+4].x);
        __m256d p2y = _mm256_setr_pd(polygon[i+1].y, polygon[i+2].y, polygon[i+3].y, polygon[i+4].y);

        // 1. Check if Y is crossed: (p1y > py) != (p2y > py)
        __m256d cmp1 = _mm256_cmp_pd(p1y, py_vec, _CMP_GT_OQ);
        __m256d cmp2 = _mm256_cmp_pd(p2y, py_vec, _CMP_GT_OQ);
        __m256d y_crossing = _mm256_xor_pd(cmp1, cmp2);

        // 2. Compute intersectX = p1x + (py - p1y) * (p2x - p1x) / (p2y - p1y)
        __m256d dy = _mm256_sub_pd(py_vec, p1y);
        __m256d dx = _mm256_sub_pd(p2x, p1x);
        __m256d p2y_sub_p1y = _mm256_sub_pd(p2y, p1y);
        __m256d num = _mm256_mul_pd(dy, dx);
        __m256d ratio = _mm256_div_pd(num, p2y_sub_p1y);
        __m256d intersect_x = _mm256_add_pd(p1x, ratio);

        // 3. Check if X is to the left: px < intersectX
        __m256d x_crossing = _mm256_cmp_pd(px_vec, intersect_x, _CMP_LT_OQ);

        // 4. Combine mask and popcount
        __m256d intersect_mask = _mm256_and_pd(y_crossing, x_crossing);
        int mask = _mm256_movemask_pd(intersect_mask);
        intersectCount += __builtin_popcount(mask);
    }

    // Remainder loop
    for (int i = n_simd; i < n; i++) {
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

// AVX2 SIMD Ray-Casting combined with OpenMP parallel reduction
inline bool isInsideAVX2Parallel(const Point& p, const std::vector<Point>& polygon, int numThreads) {
    int intersectCount = 0;
    int n = polygon.size() - 1;
    int n_simd = n - (n % 4);

    __m256d px_vec = _mm256_set1_pd(p.x);
    __m256d py_vec = _mm256_set1_pd(p.y);

    #pragma omp parallel for num_threads(numThreads) reduction(+:intersectCount) schedule(static)
    for (int i = 0; i < n_simd; i += 4) {
        __m256d p1x = _mm256_setr_pd(polygon[i].x, polygon[i+1].x, polygon[i+2].x, polygon[i+3].x);
        __m256d p1y = _mm256_setr_pd(polygon[i].y, polygon[i+1].y, polygon[i+2].y, polygon[i+3].y);
        __m256d p2x = _mm256_setr_pd(polygon[i+1].x, polygon[i+2].x, polygon[i+3].x, polygon[i+4].x);
        __m256d p2y = _mm256_setr_pd(polygon[i+1].y, polygon[i+2].y, polygon[i+3].y, polygon[i+4].y);

        __m256d cmp1 = _mm256_cmp_pd(p1y, py_vec, _CMP_GT_OQ);
        __m256d cmp2 = _mm256_cmp_pd(p2y, py_vec, _CMP_GT_OQ);
        __m256d y_crossing = _mm256_xor_pd(cmp1, cmp2);

        __m256d dy = _mm256_sub_pd(py_vec, p1y);
        __m256d dx = _mm256_sub_pd(p2x, p1x);
        __m256d p2y_sub_p1y = _mm256_sub_pd(p2y, p1y);
        __m256d num = _mm256_mul_pd(dy, dx);
        __m256d ratio = _mm256_div_pd(num, p2y_sub_p1y);
        __m256d intersect_x = _mm256_add_pd(p1x, ratio);

        __m256d x_crossing = _mm256_cmp_pd(px_vec, intersect_x, _CMP_LT_OQ);
        __m256d intersect_mask = _mm256_and_pd(y_crossing, x_crossing);

        int mask = _mm256_movemask_pd(intersect_mask);
        intersectCount += __builtin_popcount(mask);
    }

    // Remainder loop (not parallelized, typically < 3 iterations)
    for (int i = n_simd; i < n; i++) {
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
