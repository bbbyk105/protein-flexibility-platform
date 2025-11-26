"""参照実装（forループ版）- 正確性検証用"""

import numpy as np
from typing import Tuple


def compute_dsa_and_flex_reference(
    ca_coords: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    DSAスコアとflex_scoreを計算（素朴なforループ版）

    高速版との比較検証用の参照実装。
    ロジックは同じだが、意図的にベクトル化せずforループで実装。

    Args:
        ca_coords: 形状 (M, N, 3) のCα座標配列

    Returns:
        (dsa_matrix, std_matrix, flex_scores)
    """
    M, N, _ = ca_coords.shape

    # 各構造・各ペアの距離を計算
    distance_matrices = np.zeros((M, N, N), dtype=np.float64)

    for k in range(M):
        for i in range(N):
            for j in range(N):
                if i == j:
                    distance_matrices[k, i, j] = 0.0
                else:
                    diff = ca_coords[k, i, :] - ca_coords[k, j, :]
                    distance_matrices[k, i, j] = np.sqrt(np.sum(diff**2))

    # 各ペアの平均と標準偏差
    mean_distances = np.zeros((N, N), dtype=np.float64)
    std_distances = np.zeros((N, N), dtype=np.float64)

    for i in range(N):
        for j in range(N):
            distances_across_structures = distance_matrices[:, i, j]
            mean_distances[i, j] = np.mean(distances_across_structures)
            std_distances[i, j] = np.std(distances_across_structures, ddof=1 if M > 1 else 0)

    # DSAスコア
    dsa_matrix = np.zeros((N, N), dtype=np.float64)
    for i in range(N):
        for j in range(N):
            if i == j:
                dsa_matrix[i, j] = 0.0
            else:
                dsa_matrix[i, j] = mean_distances[i, j] / (std_distances[i, j] + 1e-8)

    # flex_score
    flex_scores = np.zeros(N, dtype=np.float64)
    for i in range(N):
        row_sum = 0.0
        col_sum = 0.0
        for j in range(N):
            row_sum += std_distances[i, j]
            col_sum += std_distances[j, i]
        row_mean = row_sum / N
        col_mean = col_sum / N
        flex_scores[i] = (row_mean + col_mean) / 2.0

    return dsa_matrix, std_distances, flex_scores
