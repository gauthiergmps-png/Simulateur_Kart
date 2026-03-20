import numpy as np
import math

def calculate_curv_and_dist(p1, p2, p3):
    v1 = p2 - p1
    v2 = p3 - p2
    dist = np.linalg.norm(p3 - p2)
    # Produit vectoriel et produit scalaire
    cross_product = v1[0] * v2[1] - v1[1] * v2[0]
    dot_product = np.dot(v1, v2)
    if abs(dot_product) > 1e-10:
        return math.atan2(cross_product, dot_product) / dist, dist 
    else:
        return math.pi/2 / dist, dist

p1 = np.array([0, 0])
p2 = np.array([1, 0])
p3 = np.array([2, 1])
curv, dist = calculate_curv_and_dist(p1, p2, p3)
print("curv=", curv, "dist=", dist)