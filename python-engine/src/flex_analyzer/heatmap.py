"""ヒートマップ生成モジュール"""

import pandas as pd
import numpy as np
from typing import List, Optional


def generate_heatmap(score: pd.DataFrame) -> np.ndarray:
    """
    Score DataFrame から N×N ヒートマップを生成（Notebook の行 1387-1398 を再現）

    ポイント:
    - 1-based インデックスを 0-based に変換
    - (i-1, j-1) 位置に score 値を配置
    - 未定義セルは NaN

    Args:
        score: getscore の出力

    Returns:
        N×N numpy array (NaN を含む)
    """
    # 最大インデックスを取得（1-based）
    last_pair = score.iloc[-1, 0]  # 最後のペア "i, j"
    indices = last_pair.split(", ")
    max_index = max(int(indices[0]), int(indices[1]))

    # N×N 行列を NaN で初期化
    hm = np.full((max_index, max_index), np.nan, dtype=np.float64)

    # 各ペアの score を配置
    for _, row in score.iterrows():
        i_str, j_str = row.iloc[0].split(", ")
        i = int(i_str) - 1  # 0-based に変換
        j = int(j_str) - 1
        score_val = row["score"]

        # 対称行列として配置
        hm[i, j] = score_val
        hm[j, i] = score_val

    return hm


def heatmap_to_list(hm: np.ndarray) -> List[List[Optional[float]]]:
    """
    numpy array のヒートマップを JSON 用のリストに変換

    NaN は None に変換

    Args:
        hm: generate_heatmap の出力

    Returns:
        2D list (NaN は None)
    """
    result = []
    for row in hm:
        result.append([None if np.isnan(val) else float(val) for val in row])
    return result
