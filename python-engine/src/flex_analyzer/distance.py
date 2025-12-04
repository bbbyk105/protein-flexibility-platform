"""距離計算モジュール - Notebook DSA_Cis_250317.ipynb 準拠"""

import numpy as np
import pandas as pd
from numba import jit
from itertools import combinations
from typing import Tuple


@jit(nopython=True)
def calculat(atom1: np.ndarray, atom2: np.ndarray) -> float:
    """
    2つの原子間距離を計算（Notebook の行 578-584 を再現）

    11桁まで正確な距離計算:
    1. 座標差分を 1000倍
    2. 四捨五入 (np.rint)
    3. 2乗和の平方根
    4. 1000で割る

    この丸め処理が Notebook との数値一致に必須

    Args:
        atom1: 原子1の座標 (x, y, z)
        atom2: 原子2の座標 (x, y, z)

    Returns:
        距離 (Å)
    """
    xyz = atom1 - atom2
    xyz = np.rint(xyz * 1000)  # 1000倍して四捨五入
    dis = np.sqrt(np.sum(xyz**2))
    return dis / 1000


def getdistance2(atomcoord: pd.DataFrame) -> pd.DataFrame:
    """
    全残基ペア (i, j) の距離を計算（Notebook の行 601-620 を再現）

    Args:
        atomcoord: 座標 DataFrame
            - 列0: UniProt ID (残基名)
            - 列1〜: [PDB Chain, x, y, z, PDB Chain, x, y, z, ...]

    Returns:
        distance DataFrame:
            - 列0: UniProt ID のペア "i+1, j+1" (1-based)
            - 列1: "residue pair" (残基名ペア)
            - 列2〜: 各 PDB Chain の距離値
    """
    uniprot_id = atomcoord.iloc[:, 0].name  # UniProt ID (列名)
    N = len(atomcoord)

    # すべての残基インデックスペア (i < j)
    index_pairs = list(combinations(range(N), 2))

    # 残基名（NaN を "NA" に置換して文字列化）
    residues = atomcoord.iloc[:, 0].fillna("NA").astype(str)

    # 距離用の列名: PDB/Chain 名は 4列おきに入っている想定 (PDB, x, y, z)
    cols = atomcoord.iloc[:, 1::4].columns.tolist()

    distance = pd.DataFrame(
        {
            # 残基番号ペア (1-based)
            uniprot_id: [f"{i + 1}, {j + 1}" for i, j in index_pairs],
            # 残基名ペア (全部 str にしてから連結する)
            "residue pair": [f"{residues.iloc[i]}, {residues.iloc[j]}" for i, j in index_pairs],
            # 各 PDB/Chain 距離列を NaN で初期化
            **{col: np.nan for col in cols},
        }
    )

    # 各 PDB Chain ごとに距離を計算
    for i, col in enumerate(cols):
        col_index = (i * 4) + 2  # x, y, z の開始位置
        atoms = atomcoord.iloc[:, col_index : col_index + 3].to_numpy()

        # 全ペアの距離を計算
        distance[col] = [calculat(atoms[i_idx], atoms[j_idx]) for i_idx, j_idx in index_pairs]

    return distance


def calculat_vectorized(atoms: np.ndarray) -> np.ndarray:
    """
    calculat のベクトル化版（高速化）

    全ペアの距離を一括計算

    Args:
        atoms: (N, 3) の座標配列

    Returns:
        (N*(N-1)/2,) の距離配列 (上三角のみ)
    """
    N = len(atoms)

    # ペアワイズ距離行列を一括計算
    diff = atoms[:, np.newaxis, :] - atoms[np.newaxis, :, :]  # (N, N, 3)
    diff = np.rint(diff * 1000)  # 丸め処理
    dists = np.sqrt(np.sum(diff**2, axis=-1)) / 1000  # (N, N)

    # 上三角のみ取得（i < j）
    iu = np.triu_indices(N, k=1)
    return dists[iu]


def getdistance2_fast(atomcoord: pd.DataFrame) -> pd.DataFrame:
    """
    getdistance2 のベクトル化版（高速化）

    ループの代わりに NumPy のベクトル演算を使用
    """
    uniprot_id = atomcoord.iloc[:, 0].name
    N = len(atomcoord)

    # インデックスペア (i < j)
    index_pairs = list(combinations(range(N), 2))

    # 残基名（NaN を "NA" に置換して文字列化）
    residues = atomcoord.iloc[:, 0].fillna("NA").astype(str)

    # PDB/Chain 列 (4列おき)
    cols = atomcoord.iloc[:, 1::4].columns.tolist()

    # ベースとなる距離テーブルを作成
    distance = pd.DataFrame(
        {
            # 残基番号ペア (1-based)
            uniprot_id: [f"{i + 1}, {j + 1}" for i, j in index_pairs],
            # 残基名ペア（すべて str なので TypeError を起こさない）
            "residue pair": [f"{residues.iloc[i]}, {residues.iloc[j]}" for i, j in index_pairs],
        }
    )

    # 各 PDB Chain ごとにベクトル化計算
    for i, col in enumerate(cols):
        col_index = (i * 4) + 2
        atoms = atomcoord.iloc[:, col_index : col_index + 3].to_numpy()
        distance[col] = calculat_vectorized(atoms)

    return distance
