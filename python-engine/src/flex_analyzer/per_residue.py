"""Per-residue スコア計算モジュール"""

import pandas as pd
import numpy as np
from typing import List


def compute_per_residue_scores(score: pd.DataFrame, num_residues: int) -> List[float]:
    """
    各残基に関連する全ペアの Score を平均

    定義: 残基 i の per-residue score = mean(score[i,j] for all j != i)

    用途: Mol* 3D 可視化のカラーリング

    Args:
        score: getscore の出力
        num_residues: 残基数

    Returns:
        List of per-residue scores (長さ num_residues)
    """
    per_residue = [float("nan")] * num_residues

    for idx in range(num_residues):
        residue_idx = idx + 1  # 1-based
        related_scores = []

        # 残基 idx に関連するペア (i, j) を抽出
        for _, row in score.iterrows():
            i, j = map(int, row.iloc[0].split(", "))

            if i == residue_idx or j == residue_idx:
                score_val = row["score"]
                if not np.isnan(score_val) and np.isfinite(score_val):
                    related_scores.append(score_val)

        # 平均を計算
        if related_scores:
            per_residue[idx] = float(np.mean(related_scores))
        else:
            per_residue[idx] = float("nan")

    return per_residue


def per_residue_scores_fast(score: pd.DataFrame, num_residues: int) -> np.ndarray:
    """
    compute_per_residue_scores の高速化版

    NumPy のベクトル演算を使用
    """
    per_residue = np.full(num_residues, np.nan, dtype=np.float64)

    # ペアインデックスと score 値を一括取得
    pairs = score.iloc[:, 0].str.split(", ", expand=True).astype(int).values  # (N, 2)
    scores = score["score"].values

    # 各残基ごとに関連するペアの score を平均
    for idx in range(num_residues):
        residue_idx = idx + 1  # 1-based

        # このの残基に関連するペアのマスク
        mask = (pairs[:, 0] == residue_idx) | (pairs[:, 1] == residue_idx)
        related_scores = scores[mask]

        # NaN と inf を除外
        valid_scores = related_scores[np.isfinite(related_scores)]

        if len(valid_scores) > 0:
            per_residue[idx] = np.mean(valid_scores)

    return per_residue
