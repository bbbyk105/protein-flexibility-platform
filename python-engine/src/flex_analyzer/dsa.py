# src/flex_analyzer/dsa.py

"""
Distance Scoring Analysis (DSA) 風の評価ロジック。

前提:
    - Cα 座標配列: coords (num_structures, num_residues, 3)
    - 各構造は同じ配列にアラインされている（ギャップ処理済み想定）

機能:
    - 全残基ペア (i, j) の距離分布から score_ij = mean_ij / std_ij を計算
    - 全ペア score_ij の平均値 UMF (global DSA 指標) を返す
    - 各残基ごとに関連ペアの score_ij を平均 → per-residue スコア
    - main plot 用の (mean_distance, score) サンプル点を返す
    - 隣接残基の Cα–Cα 距離から cis っぽいペアを簡易検出
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import numpy as np


@dataclass
class CisSummary:
    """cis っぽいペプチド結合に関する簡易統計。"""

    threshold: float
    num_positions: int
    positions: List[int]  # 0-based index (i: pair of i and i+1)
    mean_distances: List[float]


@dataclass
class DsaGlobalStats:
    """DSA 全体統計・可視化用情報。"""

    num_structures: int
    num_residues: int

    umf: float  # 全ペア score_ij の平均
    pair_score_mean: float
    pair_score_std: float

    # main plot 用に (平均距離, score) のサンプルを保持
    main_plot_points: List[Tuple[float, float]]

    # per-residue スコア（長さ = num_residues）
    per_residue_scores: List[float]

    # cis 情報
    cis_summary: CisSummary


def _compute_pairwise_distances(coords: np.ndarray) -> np.ndarray:
    """
    coords: shape = (K, N, 3)
    Returns:
        dists: shape = (K, N, N)
    """
    # (K, N, 1, 3) - (K, 1, N, 3) -> (K, N, N, 3)
    diff = coords[:, :, None, :] - coords[:, None, :, :]
    dists = np.linalg.norm(diff, axis=-1)
    return dists


def _compute_dsa_core(coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    DSA の核となる計算:
        - 距離平均 mean_ij
        - 距離標準偏差 std_ij
        - score_ij = mean_ij / std_ij (std_ij > 0 のみ)

    Returns:
        mean_dist: (N, N)
        score: (N, N)  NaN を含む（std=0 など）
        valid_mask: (N, N) bool
    """
    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got shape={coords.shape}")

    K, N, _ = coords.shape

    # K 構造分の距離行列
    dists = _compute_pairwise_distances(coords)  # (K, N, N)

    mean_dist = dists.mean(axis=0)  # (N, N)
    std_dist = dists.std(axis=0, ddof=1)  # (N, N)

    valid = std_dist > 0.0
    score = np.full_like(mean_dist, np.nan, dtype=np.float64)
    score[valid] = mean_dist[valid] / std_dist[valid]

    # 対角成分（i==j）は意味がないので無効化
    np.fill_diagonal(valid, False)
    np.fill_diagonal(score, np.nan)

    return mean_dist, score, valid


def _symmetrize_score(score: np.ndarray, valid: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    上三角/下三角の情報を対称にして扱いやすくする。
    """
    N = score.shape[0]
    if score.shape != (N, N):
        raise ValueError("score must be square")

    score_sym = np.full_like(score, np.nan)
    valid_sym = np.zeros_like(valid, dtype=bool)

    iu = np.triu_indices(N, k=1)

    vals = score[iu]
    valids = valid[iu]

    score_sym[iu] = vals
    score_sym[(iu[1], iu[0])] = vals  # 対称コピー

    valid_sym[iu] = valids
    valid_sym[(iu[1], iu[0])] = valids

    return score_sym, valid_sym


def _compute_umf_and_per_residue(
    score: np.ndarray,
    valid: np.ndarray,
) -> Tuple[float, np.ndarray]:
    """
    全ペアの score_ij から UMF と per-residue スコアを計算する。

    Returns:
        umf: float
        per_residue: shape = (N,)
    """
    N = score.shape[0]
    # i < j のペアのみで UMF を計算
    iu = np.triu_indices(N, k=1)
    scores_flat = score[iu]
    valid_flat = valid[iu]

    if np.any(valid_flat):
        umf = float(np.nanmean(scores_flat[valid_flat]))
    else:
        umf = float("nan")

    # per-residue: 各残基 i に関わる score_ij を平均
    per_residue = np.full(N, np.nan, dtype=np.float64)

    # 対称化されている前提で、行ごとに平均
    for i in range(N):
        row_scores = score[i]
        row_valid = valid[i]
        if np.any(row_valid):
            per_residue[i] = float(np.nanmean(row_scores[row_valid]))

    return umf, per_residue


def _sample_main_plot_points(
    mean_dist: np.ndarray,
    score: np.ndarray,
    valid: np.ndarray,
    max_points: int = 5000,
) -> List[Tuple[float, float]]:
    """
    main plot (平均距離 vs score) を描くためのサンプル点を返す。
    """
    iu = np.triu_indices(mean_dist.shape[0], k=1)

    dist_flat = mean_dist[iu]
    score_flat = score[iu]
    valid_flat = valid[iu]

    dist_valid = dist_flat[valid_flat]
    score_valid = score_flat[valid_flat]

    if dist_valid.size == 0:
        return []

    if dist_valid.size <= max_points:
        return [(float(d), float(s)) for d, s in zip(dist_valid, score_valid)]

    # ランダムにサンプリング
    idx = np.random.choice(dist_valid.size, size=max_points, replace=False)
    dist_sample = dist_valid[idx]
    score_sample = score_valid[idx]

    return [(float(d), float(s)) for d, s in zip(dist_sample, score_sample)]


def _detect_cis_from_ca(
    coords: np.ndarray,
    threshold: float = 3.3,
) -> CisSummary:
    """
    Cα–Cα 距離の平均が threshold 未満の隣接残基ペアを cis っぽいとみなす簡易検出。

    本来の cis 判定は C–N 距離などを見るべきだが、ここでは
    DSA_Cis ノートブックの “ざっくり cis 域を見たい” 用途の近似として実装。

    Returns:
        CisSummary
    """
    K, N, _ = coords.shape
    if N < 2:
        return CisSummary(threshold=threshold, num_positions=0, positions=[], mean_distances=[])

    # 隣接ペアごとに、全構造での CA–CA 距離の平均を取る
    positions: List[int] = []
    mean_dists: List[float] = []

    for i in range(N - 1):
        v1 = coords[:, i, :]
        v2 = coords[:, i + 1, :]
        diffs = v1 - v2  # (K, 3)
        dists = np.linalg.norm(diffs, axis=-1)  # (K,)
        mean_d = float(np.mean(dists))

        if mean_d < threshold:
            positions.append(i)  # ペア (i, i+1)
            mean_dists.append(mean_d)

    return CisSummary(
        threshold=threshold,
        num_positions=len(positions),
        positions=positions,
        mean_distances=mean_dists,
    )


def compute_dsa_stats(
    coords: np.ndarray,
    cis_threshold: float = 3.3,
    main_plot_max_points: int = 5000,
) -> DsaGlobalStats:
    """
    エントリポイント:
        Cα 座標配列から DSA/UMF 風の統計をまとめて計算する。

    Args:
        coords: shape = (num_structures, num_residues, 3)
        cis_threshold: cis 判定に使う CA–CA 距離閾値
        main_plot_max_points: main plot 用に返すサンプル点の最大数

    Returns:
        DsaGlobalStats
    """
    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got {coords.shape}")

    K, N, _ = coords.shape

    mean_dist, score_raw, valid_raw = _compute_dsa_core(coords)
    score_sym, valid_sym = _symmetrize_score(score_raw, valid_raw)
    umf, per_residue = _compute_umf_and_per_residue(score_sym, valid_sym)

    # main plot 用サンプル
    main_points = _sample_main_plot_points(
        mean_dist=mean_dist,
        score=score_sym,
        valid=valid_sym,
        max_points=main_plot_max_points,
    )

    # cis 近似
    cis_summary = _detect_cis_from_ca(coords, threshold=cis_threshold)

    # ペアスコアの全体分布
    iu = np.triu_indices(N, k=1)
    scores_flat = score_sym[iu]
    valid_flat = valid_sym[iu]
    if np.any(valid_flat):
        pair_mean = float(np.nanmean(scores_flat[valid_flat]))
        pair_std = float(np.nanstd(scores_flat[valid_flat], ddof=1))
    else:
        pair_mean = float("nan")
        pair_std = float("nan")

    return DsaGlobalStats(
        num_structures=K,
        num_residues=N,
        umf=float(umf),
        pair_score_mean=pair_mean,
        pair_score_std=pair_std,
        main_plot_points=main_points,
        per_residue_scores=[float(x) if np.isfinite(x) else float("nan") for x in per_residue],
        cis_summary=cis_summary,
    )


def dsa_stats_to_dict(stats: DsaGlobalStats) -> Dict[str, Any]:
    """
    API で JSON に流しやすいように、DsaGlobalStats を素の dict に変換する。
    """
    return {
        "num_structures": stats.num_structures,
        "num_residues": stats.num_residues,
        "umf": stats.umf,
        "pair_score_mean": stats.pair_score_mean,
        "pair_score_std": stats.pair_score_std,
        "main_plot_points": [{"mean_distance": d, "score": s} for d, s in stats.main_plot_points],
        "per_residue_scores": stats.per_residue_scores,
        "cis": {
            "threshold": stats.cis_summary.threshold,
            "num_positions": stats.cis_summary.num_positions,
            "positions": stats.cis_summary.positions,
            "mean_distances": stats.cis_summary.mean_distances,
        },
    }
