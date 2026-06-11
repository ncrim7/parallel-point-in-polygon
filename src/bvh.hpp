#pragma once
#include <vector>
#include <algorithm>
#include <cmath>
#include <omp.h>

#ifndef POINT_STRUCT
#define POINT_STRUCT
struct Point {
    double x;
    double y;
};
#endif

// Bounding Box structure
struct BBox {
    double x_min, x_max;
    double y_min, y_max;

    // Checks if the horizontal ray starting at p and going to x = +inf intersects the bbox
    inline bool intersectsRay(const Point& p) const {
        return (y_min <= p.y) && (p.y <= y_max) && (p.x <= x_max);
    }
};

// BVH Node structure
struct BVHNode {
    BBox bbox;
    int left_child;  // Index in nodes array. -1 if leaf.
    int right_child; // Index in nodes array. -1 if leaf.
    int edge_idx;    // Polygon edge index. Valid only if leaf.
};

// Metadata helper structure used for sorting and partitioning during build
struct EdgeInfo {
    int idx;
    BBox bbox;
    Point center;
};

// Helper function to combine two bboxes
inline BBox unionBBox(const BBox& a, const BBox& b) {
    return BBox{
        std::min(a.x_min, b.x_min),
        std::max(a.x_max, b.x_max),
        std::min(a.y_min, b.y_min),
        std::max(a.y_max, b.y_max)
    };
}

// Sequential BVH construction (using local variable copy to avoid reference aliasing)
inline int buildBVHSeq(std::vector<BVHNode>& nodes, std::vector<EdgeInfo>& edges, int start, int end, int& next_node_idx) {
    int curr_idx = next_node_idx++;
    
    // Compute bounding box containing all edges in this range
    BBox combined = edges[start].bbox;
    for (int i = start + 1; i < end; i++) {
        combined = unionBBox(combined, edges[i].bbox);
    }

    int left_child = -1;
    int right_child = -1;
    int edge_idx = -1;

    int count = end - start;
    if (count == 1) {
        edge_idx = edges[start].idx;
    } else {
        // Sort along axis with larger spread (X or Y)
        double dx = combined.x_max - combined.x_min;
        double dy = combined.y_max - combined.y_min;

        if (dx > dy) {
            std::sort(edges.begin() + start, edges.begin() + end, [](const EdgeInfo& a, const EdgeInfo& b) {
                return a.center.x < b.center.x;
            });
        } else {
            std::sort(edges.begin() + start, edges.begin() + end, [](const EdgeInfo& a, const EdgeInfo& b) {
                return a.center.y < b.center.y;
            });
        }

        int mid = start + count / 2;
        left_child = buildBVHSeq(nodes, edges, start, mid, next_node_idx);
        right_child = buildBVHSeq(nodes, edges, mid, end, next_node_idx);
    }

    // Write to array at the end to avoid pointer aliasing during recursion
    nodes[curr_idx] = BVHNode{combined, left_child, right_child, edge_idx};
    return curr_idx;
}

// Master caller to build BVH tree sequentially (highly optimized, safe and deadlock-free)
inline int buildBVHTree(std::vector<BVHNode>& nodes, const std::vector<Point>& polygon) {
    int N = polygon.size() - 1;
    std::vector<EdgeInfo> edges(N);

    for (int i = 0; i < N; i++) {
        edges[i].idx = i;
        const Point& p1 = polygon[i];
        const Point& p2 = polygon[i + 1];
        edges[i].bbox = BBox{
            std::min(p1.x, p2.x), std::max(p1.x, p2.x),
            std::min(p1.y, p2.y), std::max(p1.y, p2.y)
        };
        edges[i].center = Point{0.5 * (p1.x + p2.x), 0.5 * (p1.y + p2.y)};
    }

    nodes.resize(2 * N);
    int next_node_idx = 0;
    int root = buildBVHSeq(nodes, edges, 0, N, next_node_idx);
    
    // Resize nodes to exact allocated count
    nodes.resize(next_node_idx);
    return root;
}

// High-performance iterative stack-based traversal of the BVH for point inside check
inline bool isInsideBVH(const Point& p, const std::vector<Point>& polygon, const std::vector<BVHNode>& nodes, int root) {
    int intersectCount = 0;
    
    // Traversal stack
    int stack[64];
    int stack_ptr = 0;
    stack[stack_ptr++] = root;

    while (stack_ptr > 0) {
        int curr_idx = stack[--stack_ptr];
        const BVHNode& node = nodes[curr_idx];

        // Pruning: if the query point's ray doesn't intersect the bbox, skip the entire subtree!
        if (!node.bbox.intersectsRay(p)) {
            continue;
        }

        // Leaf Node
        if (node.left_child == -1) {
            int e_idx = node.edge_idx;
            const Point& p1 = polygon[e_idx];
            const Point& p2 = polygon[e_idx + 1];

            if (((p1.y > p.y) != (p2.y > p.y))) {
                double intersectX = p1.x + (p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y);
                if (p.x < intersectX) {
                    intersectCount++;
                }
            }
        } else {
            // Internal Node: push children to stack
            stack[stack_ptr++] = node.left_child;
            stack[stack_ptr++] = node.right_child;
        }
    }

    return (intersectCount % 2) != 0;
}

// Parallel query function for multiple points on the BVH structure
inline std::vector<int> checkPointsBVHParallel(const std::vector<Point>& points, const std::vector<Point>& polygon, const std::vector<BVHNode>& nodes, int root, int numThreads) {
    int m = points.size();
    std::vector<int> results(m);

    // Using dynamic schedule because BVH traversal depth varies between query points
    #pragma omp parallel for num_threads(numThreads) schedule(dynamic, 64)
    for (int i = 0; i < m; i++) {
        results[i] = isInsideBVH(points[i], polygon, nodes, root) ? 1 : 0;
    }
    return results;
}

// Sequential query function for multiple points on the BVH structure
inline std::vector<int> checkPointsBVHSeq(const std::vector<Point>& points, const std::vector<Point>& polygon, const std::vector<BVHNode>& nodes, int root) {
    int m = points.size();
    std::vector<int> results(m);
    for (int i = 0; i < m; i++) {
        results[i] = isInsideBVH(points[i], polygon, nodes, root) ? 1 : 0;
    }
    return results;
}
