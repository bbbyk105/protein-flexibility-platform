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
    全残基ペア (i, j) の距離を計算（Notebook DSA_Cis_250317.py 完全準拠）

    Notebook の getdistance2 関数（行 601-620）を完全再現。

    atomcoord の列構造（getcoord の出力）:
        - 列0: UniProt 配列（列名: UniProt ID）
        - 列1以降: 4 列ブロックの繰り返し
            [label, x, y, z, label, x, y, z, ...]
        
        ★重要な仕様:
            - label 列の位置: 1, 5, 9, 13, ... (4k+1)
            - x 列の位置: 2, 6, 10, 14, ... (4k+2)
            - y 列の位置: 3, 7, 11, 15, ... (4k+3)
            - z 列の位置: 4, 8, 12, 16, ... (4k+4)

    Args:
        atomcoord: getcoord の出力 DataFrame

    Returns:
        distance DataFrame:
            - 列0: UniProt ID のペア "i+1, j+1" (1-based)
            - 列1: "residue pair" (残基名ペア)
            - 列2以降: 各 PDB/Chain の距離値
                列名は PDB/Chain 名（例: "1A00 A"）

    例:
        入力 atomcoord:
        | P69905 | 1A00 A | 1.2 | 2.3 | 3.4 | 1A01 A | 1.1 | 2.2 | 3.3 |
        | ALA    | 1A00 A | ... | ... | ... | 1A01 A | ... | ... | ... |
        | VAL    | 1A00 A | ... | ... | ... | 1A01 A | ... | ... | ... |

        出力 distance:
        | P69905  | residue pair | 1A00 A  | 1A01 A  |
        | 1, 2    | ALA, VAL     | 3.85    | 3.92    |
        | 1, 3    | ALA, LEU     | 7.21    | 7.18    |
    """
    # ========================================================================
    # Step 1: 基本情報の取得
    # ========================================================================
    uniprot_col_name = atomcoord.columns[0]
    N = len(atomcoord)  # 残基数

    # 全残基ペア (i < j) のインデックスを生成
    index_pairs = list(combinations(range(N), 2))

    # 残基名（NaN を "NA" に置換して文字列化）
    residues = atomcoord.iloc[:, 0].fillna("NA").astype(str)

    # ========================================================================
    # Step 2: PDB/Chain 列名を取得（位置ベース）
    # ========================================================================
    # Notebook の実装:
    #   cols = atomcoord.columns.values.tolist()[1::4]
    # つまり、1, 5, 9, 13, ... 列目がラベル列
    
    cols = []
    num_structures = (len(atomcoord.columns) - 1) // 4  # UniProt 列を除いた 4 列ブロック数
    
    for i in range(num_structures):
        label_col_idx = 1 + (i * 4)  # 1, 5, 9, 13, ...
        
        if label_col_idx < len(atomcoord.columns):
            # ラベル列の値から列名を取得（全行同じ値なので最初の行を使用）
            label_value = atomcoord.iloc[0, label_col_idx]
            # 列名として使用（文字列化）
            col_name = str(label_value) if pd.notna(label_value) else f"Structure_{i+1}"
            cols.append(col_name)
        else:
            print(
                f"[getdistance2] WARNING: 想定される列インデックス {label_col_idx} "
                f"が範囲外です（総列数: {len(atomcoord.columns)}）"
            )

    if not cols:
        raise RuntimeError(
            "getdistance2: PDB/Chain 列が見つかりません。\n"
            f"atomcoord.columns = {list(atomcoord.columns)}\n"
            f"列数 = {len(atomcoord.columns)}"
        )

    print(f"[getdistance2] INFO: {len(cols)} 構造の距離を計算します")
    print(f"[getdistance2] DEBUG: PDB/Chain 列名 = {cols}")

    # ========================================================================
    # Step 3: distance DataFrame の骨格を作成
    # ========================================================================
    distance = pd.DataFrame(
        {
            # 残基番号ペア (1-based)
            uniprot_col_name: [f"{i + 1}, {j + 1}" for i, j in index_pairs],
            # 残基名ペア
            "residue pair": [f"{residues.iloc[i]}, {residues.iloc[j]}" for i, j in index_pairs],
        }
    )

    # ========================================================================
    # Step 4: 各 PDB/Chain ごとに距離を計算
    # ========================================================================
    for idx, col in enumerate(cols):
        # このラベル列の位置
        label_col_idx = 1 + (idx * 4)  # 1, 5, 9, 13, ...
        
        # x, y, z 列の位置
        x_col_idx = label_col_idx + 1  # 2, 6, 10, 14, ...
        y_col_idx = label_col_idx + 2  # 3, 7, 11, 15, ...
        z_col_idx = label_col_idx + 3  # 4, 8, 12, 16, ...
        
        # 列インデックスの範囲チェック
        if z_col_idx >= len(atomcoord.columns):
            print(
                f"[getdistance2] WARNING: {col} の座標列が不足 "
                f"(z_col_idx={z_col_idx}, 総列数={len(atomcoord.columns)})"
            )
            # NaN で埋める
            distance[col] = np.nan
            continue
        
        # x, y, z を抽出（位置ベース）
        atoms = atomcoord.iloc[:, x_col_idx:z_col_idx + 1].to_numpy()
        
        # 3列であることを確認
        if atoms.shape[1] != 3:
            print(
                f"[getdistance2] WARNING: {col} の座標が 3 列ではありません "
                f"(shape={atoms.shape})"
            )
            distance[col] = np.nan
            continue
        
        # ベクトル化距離計算
        try:
            distances = calculat_vectorized(atoms)
            distance[col] = distances
        except Exception as e:
            print(f"[getdistance2] WARNING: {col} の距離計算でエラー: {e}")
            distance[col] = np.nan
            continue

    # ========================================================================
    # Step 5: 結果の検証
    # ========================================================================
    print(f"[getdistance2] SUCCESS: {len(distance)} ペアの距離を計算しました")
    print(f"[getdistance2] DEBUG: distance.shape = {distance.shape}")
    print(f"[getdistance2] DEBUG: distance.columns[:5] = {list(distance.columns[:5])}")

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


