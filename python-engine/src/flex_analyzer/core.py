"""NumPyベクトル化による高速実装"""

import numpy as np
from typing import Tuple
from .utils import calculate_distance_matrix, safe_divide


def compute_dsa_and_flex_fast(ca_coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    DSAスコアとflex_scoreを高速計算（NumPyベクトル化版）

    Args:
        ca_coords: 形状 (M, N, 3) のCα座標配列
                   M = 構造数、N = 残基数

    Returns:
        (dsa_matrix, std_matrix, flex_scores)
        - dsa_matrix: 形状 (N, N) のDSAスコア行列
        - std_matrix: 形状 (N, N) の距離標準偏差行列
        - flex_scores: 形状 (N,) の残基ごとの可変性スコア
    """
    M, N, _ = ca_coords.shape

    # 全構造の全ペア距離を一括計算
    # distance_matrices: (M, N, N)
    distance_matrices = np.zeros((M, N, N), dtype=np.float64)
    for k in range(M):
        distance_matrices[k] = calculate_distance_matrix(ca_coords[k])

    # 各ペアの平均距離と標準偏差を計算（構造間での統計量）
    mean_distances = np.mean(distance_matrices, axis=0)  # (N, N)
    std_distances = np.std(distance_matrices, axis=0, ddof=1 if M > 1 else 0)  # (N, N)

    # DSAスコア = 平均距離 / 標準偏差
    dsa_matrix = safe_divide(mean_distances, std_distances, epsilon=1e-8)

    # 対角成分は0にする
    np.fill_diagonal(dsa_matrix, 0.0)
    np.fill_diagonal(std_distances, 0.0)

    # flex_score: 各残基について、関連するペアの標準偏差の平均
    # row_mean: i行目の平均（残基iから他への距離の標準偏差）
    # col_mean: i列目の平均（他から残基iへの距離の標準偏差）
    row_mean = np.mean(std_distances, axis=1)  # (N,)
    col_mean = np.mean(std_distances, axis=0)  # (N,)
    flex_scores = (row_mean + col_mean) / 2.0  # (N,)

    return dsa_matrix, std_distances, flex_scores
