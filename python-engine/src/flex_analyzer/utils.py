"""ユーティリティ関数"""

import numpy as np
from typing import Tuple


def calculate_distance_matrix(coords: np.ndarray) -> np.ndarray:
    """
    3D座標から距離行列を計算（ベクトル化版）

    Args:
        coords: 形状 (N, 3) の座標配列

    Returns:
        形状 (N, N) の距離行列
    """
    # coords: (N, 3)
    # diff: (N, 1, 3) - (1, N, 3) = (N, N, 3)
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    # ユークリッド距離: sqrt(sum(diff^2))
    distances = np.sqrt(np.sum(diff**2, axis=-1))
    return distances


def safe_divide(
    numerator: np.ndarray, denominator: np.ndarray, epsilon: float = 1e-8
) -> np.ndarray:
    """
    ゼロ割りを安全に処理する除算

    Args:
        numerator: 分子
        denominator: 分母
        epsilon: ゼロ割り回避用の微小値

    Returns:
        numerator / (denominator + epsilon)
    """
    return numerator / (denominator + epsilon)
