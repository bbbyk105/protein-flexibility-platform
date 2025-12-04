"""Cis ペプチド結合検出モジュール - Notebook DSA_Cis_250317.ipynb 準拠"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from .score import getscore_cis


def detect_cis_pairs(
    distance: pd.DataFrame, cis_threshold: float = 3.8
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cis ペプチド結合の検出（Notebook の行 892-924 を再現）

    処理フロー:
    1. 全 PDB+Chain ごとに距離 <= 閾値のペアを列挙
    2. 重複除去
    3. cis_cnt / trans_cnt を計算
    4. 全構造で cis のペアのみ抽出 (trans_cnt == 0)
    5. mix (cis と trans 混在) をカウント
    6. cis 統計を計算

    Args:
        distance: getdistance2 の出力
        cis_threshold: 距離閾値 (Å)

    Returns:
        (cis_dist, cis_info)
        - cis_dist: cis ペアの距離データ
        - cis_info: cis 統計の辞書
    """
    # 全 PDB Chain ごとに距離が閾値以下のペアを列挙
    cis_index = []
    for col in distance.columns.values.tolist()[2:]:  # 列名（PDB Chain）のみ
        tmp = distance.query(f"`{col}` <= @cis_threshold").index.to_list()
        cis_index.extend(tmp)

    # cis ペアが1つもない場合
    if not cis_index:
        return pd.DataFrame(), {
            "cis_dist_mean": 0.0,
            "cis_dist_std": 0.0,
            "cis_score_mean": 0.0,
            "cis_num": 0,
            "mix": 0,
            "cis_pairs": [],
            "threshold": cis_threshold,
        }

    # 重複除去
    cis_index = sorted(set(cis_index))
    cis_dist = distance.iloc[cis_index, :].copy()

    # cis / trans のカウント
    cis_cnt = cis_dist.iloc[:, 2:].apply(lambda row: (row <= cis_threshold).sum(), axis=1)
    trans_cnt = cis_dist.iloc[:, 2:].apply(lambda row: (row > cis_threshold).sum(), axis=1)

    cnt = pd.DataFrame({"cis_cnt": cis_cnt, "trans_cnt": trans_cnt})

    # 全構造で cis のペアのみ抽出
    all_cis_dist = cis_dist[(cnt["trans_cnt"] == 0)]

    # mix: cis と trans が混在するペア数
    mix = ((cnt["cis_cnt"] >= 1) & (cnt["trans_cnt"] >= 1)).sum()

    # cis score を計算
    cis_score = getscore_cis(cis_dist, 0)

    # cis_dist と cis_score を連結
    cis_dist = pd.concat([cis_dist, cis_score.iloc[:, 2:]], axis=1)
    cis_dist = pd.concat([cis_dist, cnt], axis=1)

    # cis 統計
    cis_dist_mean = float(cis_dist["distance mean"].mean())

    if len(cis_dist["distance mean"]) == 1:
        cis_dist_std = 0.0
    else:
        cis_dist_std = float(cis_dist["distance mean"].std())

    cis_score_mean = float(cis_dist["score"].mean())
    cis_num = len(all_cis_dist)

    # cis ペアのインデックスリスト
    cis_pairs = cis_dist[distance.columns[0]].tolist()

    cis_info = {
        "cis_dist_mean": cis_dist_mean,
        "cis_dist_std": cis_dist_std,
        "cis_score_mean": cis_score_mean,
        "cis_num": cis_num,
        "mix": int(mix),
        "cis_pairs": cis_pairs,
        "threshold": cis_threshold,
    }

    return cis_dist, cis_info
