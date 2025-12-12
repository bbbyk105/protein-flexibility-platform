"""DSA Score 計算モジュール - Notebook DSA_Cis_250317.ipynb 準拠（NaN 安全版）"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd


def getscore(distance: pd.DataFrame, ddof: int = 0) -> pd.DataFrame:
    """
    DSA Score = mean / std を計算（Notebook の行 622-635 ベース）

    Args:
        distance: getdistance2 の出力 DataFrame
        ddof: 0 (母標準偏差) or 1 (標本標準偏差)

    Returns:
        score DataFrame:
            - 列0: UniProt ID のペア (distance の 1 列目をそのまま使う想定)
            - 列1: "residue pair"
            - 列2: "distance mean"
            - 列3: "distance std"
            - 列4: "score" (mean / std)
    """
    # 距離データ部分（3 列目以降）
    dis = distance.iloc[:, 2:]

    # NaN は無視して平均・標準偏差を計算
    means = dis.mean(axis="columns", skipna=True)
    stds = dis.std(axis="columns", ddof=ddof, skipna=True)

    # std が 0 の場合は 0.0001 に置換（Notebook 準拠）
    stds = stds.replace(0, 0.0001)

    # score 計算（mean or std が NaN の行は NaN のまま残す）
    scores = means / stds

    column0 = distance.columns[0]

    score_df = pd.DataFrame(
        {
            column0: distance[column0],
            "residue pair": distance["residue pair"],
            "distance mean": means,
            "distance std": stds,
            "score": scores,
        }
    )

    return score_df


def getscore_cis(distance: pd.DataFrame, ddof: int = 0) -> pd.DataFrame:
    """
    getscore と同じ（cis 専用）

    Args:
        distance: cis ペアのみの distance DataFrame
        ddof: 0 (母標準偏差) or 1 (標本標準偏差)

    Returns:
        cis_score DataFrame
    """
    return getscore(distance, ddof=ddof)


def _get_valid_scores(score: pd.DataFrame) -> pd.Series:
    """
    有効なスコアを抽出する共通関数（内部使用）

    Args:
        score: getscore の出力 DataFrame

    Returns:
        有効なスコアの Series（inf と NaN を除外）

    有効なスコアが 1 つも無い場合は RuntimeError を投げる。
    """
    s = score["score"].replace([np.inf, -np.inf], np.nan).dropna()

    if s.empty:
        raise RuntimeError(
            "No valid DSA scores could be computed "
            "(all distance means/stds are NaN or infinite). "
            "Sequence alignment / trimming may have removed almost all variation."
        )

    return s


def compute_pair_statistics(score: pd.DataFrame) -> Tuple[float, float]:
    """
    ペアスコアの統計量を計算（文献定義準拠）

    文献定義:
        - 全残基ペアのスコア（mean distance / std）の統計量を計算
        - UMF はこの平均値として定義される

    Returns:
        (pair_score_mean, pair_score_std)
        - pair_score_mean: ペアスコアの平均（= UMF）
        - pair_score_std: ペアスコアの標準偏差

    有効なスコアが 1 つも無い場合は RuntimeError を投げる。
    """
    s = _get_valid_scores(score)
    return float(s.mean()), float(s.std(ddof=1))


def compute_umf(score: pd.DataFrame) -> float:
    """
    UMF (Unified Mobility Factor) を計算（文献定義準拠）

    文献定義:
        UMF = 「そのタンパク質について得られた全てのペアスコアの収束した平均値」
        (converged average score of all pair scores for the protein)

    実装:
        UMF = ペアスコアの平均 = compute_pair_statistics()[0]

    この関数は compute_pair_statistics() と同じ母集団を使用し、
    同じ平均値を返すことを保証する。

    有効なスコアが 1 つも無い場合は RuntimeError を投げる。
    """
    # 文献定義に従い、ペアスコアの平均として計算
    # compute_pair_statistics() と同じロジックを使用して一貫性を保証
    pair_score_mean, _ = compute_pair_statistics(score)
    return pair_score_mean
