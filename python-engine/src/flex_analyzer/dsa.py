# src/flex_analyzer/dsa.py
"""
Distance Scoring Analysis (DSA) に相当する解析ロジック。

前提:
    - Cα 座標配列: coords (num_structures, num_residues, 3)
    - 各構造は同じ配列にアラインされている（ギャップ処理済み想定）

このモジュールでは、研究室で使っている Jupyter Notebook
「DSA_Cis_250317.ipynb」のロジックにできるだけ揃えた形で、

    - 全残基ペア (i, j) の距離分布から score_ij = mean_ij / std_ij を計算
        * 標準偏差は母標準偏差 (ddof=0)
        * std_ij == 0 のときは 1e-4 に置き換えて score を計算
    - 全ペア score_ij の平均値 UMF (global DSA 指標) を計算
    - 各残基ごとに関連ペアの score_ij を平均 → per-residue スコア
    - main plot 用の (mean_distance, score) サンプル点を返す
    - 隣接残基の Cα–Cα 距離から cis っぽいペアを簡易検出

を行う。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# dataclass 定義
# ---------------------------------------------------------------------------


@dataclass
class CisSummary:
    """cis っぽいペプチド結合に関する簡易統計。

    Attributes
    ----------
    threshold:
        cis 判定に使った Cα–Cα 距離の閾値 [Å]。
    num_positions:
        cis と判定された位置の数。
    positions:
        0-based index のリスト。i 番目の要素が True なら、
        残基 (i, i+1) のペアが cis っぽい。
    mean_distances:
        各位置での「構造間平均 Cα–Cα 距離」[Å]。
    """

    threshold: float
    num_positions: int
    positions: List[int]
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

    # ⭐ ヒートマップ用のスコア行列（N×N、下三角＆対角は NaN）
    score_heatmap: List[List[float]]

    # per-residue スコア（長さ = num_residues）
    per_residue_scores: List[float]

    # cis 情報
    cis_summary: CisSummary


# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _compute_pairwise_distances(coords: np.ndarray) -> np.ndarray:
    """
    全構造について Cα–Cα 距離行列を計算する。

    Parameters
    ----------
    coords : np.ndarray
        shape = (K, N, 3)

    Returns
    -------
    dists : np.ndarray
        shape = (K, N, N)
        dists[k, i, j] = 第 k 構造での残基 i, j 間の距離 [Å]
    """
    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got shape={coords.shape}")

    # (K, N, 1, 3) - (K, 1, N, 3) -> (K, N, N, 3)
    diff = coords[:, :, np.newaxis, :] - coords[:, np.newaxis, :, :]
    dists = np.linalg.norm(diff, axis=-1)  # (K, N, N)
    return dists


def _compute_dsa_core(coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    DSA の核となる計算:
        - 距離平均 mean_ij
        - 距離標準偏差 std_ij
        - score_ij = mean_ij / std_ij

    Jupyter Notebook 版の実装と揃えるため、
    標準偏差は ddof=0（母標準偏差）を用い、
    std_ij==0 の場合は 1e-4 に置き換えてから score を計算する。

    Parameters
    ----------
    coords : np.ndarray
        shape = (K, N, 3)

    Returns
    -------
    mean_dist : np.ndarray
        shape = (N, N)
    score : np.ndarray
        shape = (N, N)。対角成分は NaN。
    valid : np.ndarray
        shape = (N, N) の bool。score が有限なところが True。
        対角成分は False。
    """
    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got shape={coords.shape}")

    K, N, _ = coords.shape
    if K < 1 or N < 1:
        raise ValueError(f"coords has invalid shape {coords.shape}")

    dists = _compute_pairwise_distances(coords)  # (K, N, N)

    # 平均距離と標準偏差（母標準偏差）
    mean_dist = dists.mean(axis=0)  # (N, N)
    std_dist = dists.std(axis=0, ddof=0)  # (N, N)

    # ゼロ割りを避けるため std==0 を小さい値に置き換える
    std_for_score = std_dist.copy()
    std_for_score[std_for_score == 0.0] = 1e-4

    score = mean_dist / std_for_score

    # 有効マスク: score が有限な場所
    valid = np.isfinite(score)

    # 対角成分は意味がないので NaN / False にする
    np.fill_diagonal(score, np.nan)
    np.fill_diagonal(valid, False)

    return mean_dist, score, valid


def _symmetrize_score(
    score: np.ndarray,
    valid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    距離行列は本来対称なので、score/valid も対称化しておく。
    単純に (A + A.T) / 2 で平均をとり、valid は AND をとる。
    """
    if score.shape != valid.shape:
        raise ValueError("score and valid must have the same shape")

    # 対称化
    score_sym = np.where(
        np.isnan(score) | np.isnan(score.T),
        np.nan,
        (score + score.T) / 2.0,
    )
    valid_sym = valid & valid.T

    # 対角は NaN / False のまま
    np.fill_diagonal(score_sym, np.nan)
    np.fill_diagonal(valid_sym, False)

    return score_sym, valid_sym


def _compute_umf_and_per_residue(
    score: np.ndarray,
    valid: np.ndarray,
) -> Tuple[float, np.ndarray]:
    """
    UMF と per-residue スコアを計算する。

    - UMF = 上三角 (i < j) における score_ij の平均
    - per-residue スコア:
        残基 i に対し、行 i の score_ij（valid=True なもの）を平均した値
    """
    if score.shape != valid.shape:
        raise ValueError("score and valid must have the same shape")

    N = score.shape[0]

    # UMF: 上三角 (i<j) の有効な score を平均
    iu = np.triu_indices(N, k=1)
    scores_flat = score[iu]
    valid_flat = valid[iu]

    if np.any(valid_flat):
        umf = float(np.nanmean(scores_flat[valid_flat]))
    else:
        umf = float("nan")

    # per-residue: 各 i について行 i の score_ij を平均
    per_residue = np.full(N, np.nan, dtype=float)
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
    max_points: int = 2000,
) -> List[Tuple[float, float]]:
    """
    main plot 用に (mean_distance, score) のサンプル点を作成する。

    Notebook では距離平均 vs score の散布図を描いているので、
    ここでもそのためのサンプル点を返す。

    - 上三角 (i<j) の有効なペアのみ使用
    - ペア数が多い場合はランダムサンプリングで max_points 件に絞る
    """
    if not (mean_dist.shape == score.shape == valid.shape):
        raise ValueError("mean_dist, score, valid must have the same shape")

    N = mean_dist.shape[0]
    iu = np.triu_indices(N, k=1)

    md_flat = mean_dist[iu]
    sc_flat = score[iu]
    valid_flat = valid[iu]

    mask = valid_flat & np.isfinite(md_flat) & np.isfinite(sc_flat)
    md_valid = md_flat[mask]
    sc_valid = sc_flat[mask]

    if md_valid.size == 0:
        return []

    if md_valid.size > max_points:
        idx = np.random.choice(md_valid.size, size=max_points, replace=False)
        md_valid = md_valid[idx]
        sc_valid = sc_valid[idx]

    return [(float(d), float(s)) for d, s in zip(md_valid, sc_valid)]


def _detect_cis_from_ca(
    coords: np.ndarray,
    threshold: float = 3.8,
) -> CisSummary:
    """
    隣接残基の Cα–Cα 距離に基づいて、cis っぽいペプチド結合を簡易検出する。

    ※ Notebook 版では距離と閾値から cis 判定をしているので、
       ここでは Cα(i)–Cα(i+1) の平均距離が threshold 以下なら「cis っぽい」とみなす。

    Parameters
    ----------
    coords : np.ndarray
        shape = (K, N, 3)
    threshold : float, default 3.8
        cis 判定に使う Cα–Cα 距離の閾値 [Å]。

    Returns
    -------
    CisSummary
        検出された位置と、その位置での平均距離をまとめたもの。
    """
    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got shape={coords.shape}")

    K, N, _ = coords.shape
    if N < 2:
        return CisSummary(threshold=threshold, num_positions=0, positions=[], mean_distances=[])

    # (K, N-1, 3): i+1 - i
    diffs = coords[:, 1:, :] - coords[:, :-1, :]
    dists = np.linalg.norm(diffs, axis=-1)  # (K, N-1)
    mean_dists = dists.mean(axis=0)  # (N-1,)

    positions = [int(i) for i, d in enumerate(mean_dists) if np.isfinite(d) and d <= threshold]
    mean_list = [float(mean_dists[i]) for i in positions]

    return CisSummary(
        threshold=float(threshold),
        num_positions=len(positions),
        positions=positions,
        mean_distances=mean_list,
    )


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------


def compute_dsa_stats(
    coords: np.ndarray,
    cis_threshold: float = 3.3,
    main_plot_max_points: int = 5000,
) -> DsaGlobalStats:
    """
    Cα 座標配列から DSA/UMF 風の統計をまとめて計算する。
    """

    if coords.ndim != 3:
        raise ValueError(f"coords must be (K, N, 3), got {coords.shape}")

    K, N, _ = coords.shape

    # DSA コア計算
    mean_dist, score_raw, valid_raw = _compute_dsa_core(coords)
    score_sym, valid_sym = _symmetrize_score(score_raw, valid_raw)

    # UMF & per-residue
    umf, per_residue = _compute_umf_and_per_residue(score_sym, valid_sym)

    # main plot 用サンプル
    main_points = _sample_main_plot_points(
        mean_dist=mean_dist,
        score=score_sym,
        valid=valid_sym,
        max_points=main_plot_max_points,
    )

    # ⭐ ヒートマップ行列を作成（上三角だけ値を入れて、他は NaN）
    heatmap = np.full((N, N), np.nan, dtype=float)
    iu = np.triu_indices(N, k=1)
    heatmap[iu] = score_sym[iu]

    # cis 近似
    cis_summary = _detect_cis_from_ca(coords, threshold=cis_threshold)

    # ペアスコアの全体分布
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
        score_heatmap=heatmap.tolist(),  # ⭐ ここで list 化
        per_residue_scores=[float(x) if np.isfinite(x) else float("nan") for x in per_residue],
        cis_summary=cis_summary,
    )


def dsa_stats_to_dict(stats: DsaGlobalStats) -> Dict[str, Any]:
    """
    API で JSON にしやすい dict に変換。
    """
    return {
        "num_structures": stats.num_structures,
        "num_residues": stats.num_residues,
        "umf": stats.umf,
        "pair_score_mean": stats.pair_score_mean,
        "pair_score_std": stats.pair_score_std,
        "main_plot_points": [{"mean_distance": d, "score": s} for d, s in stats.main_plot_points],
        # ⭐ ヒートマップ（N×N、NaN 含む）
        "score_heatmap": stats.score_heatmap,
        "per_residue_scores": stats.per_residue_scores,
        "cis": {
            "threshold": stats.cis_summary.threshold,
            "num_positions": stats.cis_summary.num_positions,
            "positions": stats.cis_summary.positions,
            "mean_distances": stats.cis_summary.mean_distances,
        },
    }
