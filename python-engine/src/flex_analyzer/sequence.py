"""
sequence.py

DSA 解析パイプライン用のユーティリティ関数群。

- sort_sequence: UniProt 配列 + 各 PDB/chain の配列テーブルをトリミング・整形
- getcoord:      各 PDB/chain の CA 座標 (atom_coord/*.csv) を読み込み、
                 DSA 用の atomcoord テーブル (1 + 4 * n_structures 列) を構築

修正内容:
- sort_sequence に seq_ratio フィルタを実装
- _find_coord_file を簡素化（小文字 PDB ID のみ）
- _load_coord_table の列名パターンマッチング改善
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Hashable, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


@dataclass
class PDBChain:
    """PDB ID と Chain ID のペア"""

    pdbid: str
    chain: str

    @property
    def label(self) -> str:
        """ログや列名表示用のラベル"""
        return f"{self.pdbid} {self.chain}"


def _parse_pdb_chain_column_name(col: Hashable) -> Optional[PDBChain]:
    """
    trimsequence の列名から PDB ID / chain を取り出す。

    想定フォーマット:
        - "1A00 A"
        - "1a00 A" (小文字 PDB ID も許容)

    先頭列 (UniProt ID) はここでは処理しないので、
    呼び出し側で columns[1:] を回す前提。
    """
    name = str(col).strip()
    if not name:
        return None

    parts = name.split()
    if len(parts) != 2:
        # "1A00" みたいに chain 名が入っていない場合は無視
        return None

    pdbid, chain = parts
    pdbid = pdbid.strip()
    chain = chain.strip()

    if not pdbid or not chain:
        return None

    return PDBChain(pdbid=pdbid, chain=chain)


def _find_coord_file(pdb_chain: PDBChain, atom_coord_dir: Path) -> Optional[Path]:
    """
    atom_coord ディレクトリ内で、指定 PDB の座標 CSV ファイルを探す。

    命名規則（優先順位順）:
        1. {pdbid}.csv (小文字) - 推奨
        2. {pdbid}.csv (大文字)
        3. {PDBID}.csv (元の大文字)

    例:
        - 1a00.csv (推奨)
        - 1A00.csv
    """
    pdbid = pdb_chain.pdbid

    # 優先順位順に試行
    candidates = [
        pdbid.lower(),  # 推奨: 小文字
        pdbid.upper(),  # 大文字
        pdbid,  # 元のまま
    ]

    for candidate in candidates:
        path = atom_coord_dir / f"{candidate}.csv"
        if path.exists():
            return path

    return None


def _load_coord_table(path: Path) -> pd.DataFrame:
    """
    座標ファイルを読み込み、x, y, z 列を特定する。

    対応する列名パターン（優先度順）:
        1. Cartn_x, Cartn_y, Cartn_z (mmCIF 標準)
        2. x, y, z (小文字)
        3. X, Y, Z (大文字)
        4. coord_x, coord_y, coord_z
        5. 数値カラムの先頭3つ（フォールバック）

    Returns:
        x, y, z 列を含む DataFrame
    """
    df = pd.read_csv(path)

    # パターンマッチング（優先度順）
    patterns = [
        ("Cartn_x", "Cartn_y", "Cartn_z"),  # mmCIF 標準
        ("x", "y", "z"),  # 小文字
        ("X", "Y", "Z"),  # 大文字
        ("coord_x", "coord_y", "coord_z"),  # その他
    ]

    for x_col, y_col, z_col in patterns:
        if all(c in df.columns for c in [x_col, y_col, z_col]):
            # 見つかった列を x, y, z にリネーム
            return df[[x_col, y_col, z_col]].rename(columns={x_col: "x", y_col: "y", z_col: "z"})

    # フォールバック: 数値カラムから推測
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if len(numeric_cols) >= 3:
        x_col, y_col, z_col = numeric_cols[:3]
        print(
            f"[_load_coord_table] WARNING: 座標列を推測しました "
            f"({path.name}): {x_col}, {y_col}, {z_col}"
        )
        return df[[x_col, y_col, z_col]].rename(columns={x_col: "x", y_col: "y", z_col: "z"})

    raise RuntimeError(
        f"座標ファイル {path} から x,y,z を特定できませんでした。\n" f"列名: {list(df.columns)}"
    )


# ---------------------------------------------------------------------------
# sort_sequence
# ---------------------------------------------------------------------------


def sort_sequence(
    uniprot_id: str,
    seqdata: pd.DataFrame,
    seq_ratio: float = 0.9,
) -> pd.DataFrame:
    """
    配列トリミング・アライメント用関数。

    seq_ratio 以上の構造で揃っている残基のみを保持する。

    Args:
        uniprot_id: UniProt ID（先頭列の名前に使用）
        seqdata: 配列 DataFrame
            - 0列目: UniProt 配列
            - 1列目以降: 各 PDB/chain の配列
        seq_ratio: 閾値（0.0-1.0）
            この割合以上の構造で揃っている残基のみを保持

    Returns:
        フィルタリング後の DataFrame

    Example:
        >>> seqdata = pd.DataFrame({
        ...     'P69905': ['ALA', 'VAL', 'LEU', 'SER'],
        ...     '1A00 A': ['ALA', 'VAL', np.nan, 'SER'],
        ...     '1A01 A': ['ALA', np.nan, 'LEU', 'SER'],
        ...     '1A0U A': ['ALA', 'VAL', 'LEU', np.nan],
        ... })
        >>> result = sort_sequence('P69905', seqdata, seq_ratio=0.75)
        # 残基 0 は 4/4 構造で揃っている → 保持
        # 残基 1 は 3/4 構造で揃っている (75%) → 保持
        # 残基 2 は 3/4 構造で揃っている (75%) → 保持
        # 残基 3 は 3/4 構造で揃っている (75%) → 保持
    """
    df = seqdata.copy()

    # 先頭列を UniProt ID でリネーム
    cols = list(df.columns)
    if cols:
        cols[0] = uniprot_id
        df.columns = cols

    # seq_ratio フィルタ: 各行（残基）で非 NaN の列数をカウント
    num_structures = len(df.columns) - 1  # UniProt 列を除く

    if num_structures == 0:
        # 構造が1つもない場合はそのまま返す
        return df

    threshold = int(num_structures * seq_ratio)

    # 各行の非 NaN 数をカウント（UniProt 列を除く）
    count_per_row = df.iloc[:, 1:].count(axis=1)

    # threshold 以上の行のみを保持
    df_filtered = df[count_per_row >= threshold].copy()
    df_filtered.reset_index(drop=True, inplace=True)

    if len(df_filtered) == 0:
        raise RuntimeError(
            f"seq_ratio={seq_ratio} でフィルタした結果、残基が0になりました。\n"
            f"元の残基数: {len(df)}, 構造数: {num_structures}\n"
            f"seq_ratio を下げるか、より多くの構造を使用してください。"
        )

    removed = len(df) - len(df_filtered)
    if removed > 0:
        print(
            f"[sort_sequence] INFO: {len(df)} 残基 → {len(df_filtered)} 残基に絞り込み "
            f"({removed} 残基を除外, seq_ratio={seq_ratio:.2f})"
        )

    return df_filtered


# ---------------------------------------------------------------------------
# getcoord
# ---------------------------------------------------------------------------


def getcoord(trimsequence: pd.DataFrame, atom_coord_dir: str = "atom_coord/") -> pd.DataFrame:
    """
    DSA 解析で使用する CA 座標テーブルを構築する。

    入力:
        trimsequence:
            - 0 列目: UniProt 配列 (列名は UniProt ID)
            - 1 列目以降: "1A00 A" のような PDB/chain を表す列

    出力 (atomcoord):
        - 最初の列 "uniprot_residue": UniProt 配列 (3 文字コード)
        - 以降: 各構造ごとに 4 列のブロック (合計 1 + 4 * n_structures 列)
            [label_k, x_k, y_k, z_k]

    Example:
        >>> atomcoord.columns
        ['uniprot_residue', 'label_1a00_A', 'x_1a00_A', 'y_1a00_A', 'z_1a00_A',
         'label_1a01_A', 'x_1a01_A', 'y_1a01_A', 'z_1a01_A', ...]
    """
    atom_coord_base = Path(atom_coord_dir)
    atom_coord_base.mkdir(parents=True, exist_ok=True)

    if trimsequence.shape[1] < 2:
        raise ValueError(
            f"trimsequence に PDB/chain 列がありません (列数: {trimsequence.shape[1]})。\n"
            f"列名: {list(trimsequence.columns)}"
        )

    # UniProt 配列 (0 列目)
    uniprot_residues = trimsequence.iloc[:, 0].reset_index(drop=True)
    num_residues = len(uniprot_residues)

    # 出力 DataFrame の骨格
    atomcoord = pd.DataFrame({"uniprot_residue": uniprot_residues})

    pdb_chains: List[PDBChain] = []

    # 1 列目以降を PDB/chain 列として解釈
    for col in trimsequence.columns[1:]:
        pc = _parse_pdb_chain_column_name(col)
        if pc is None:
            print(
                f"[getcoord] WARNING: 列名 '{col}' から PDB/chain を解釈できなかったためスキップします。"
            )
            continue
        pdb_chains.append(pc)

    if not pdb_chains:
        raise RuntimeError(
            "getcoord: 有効な PDB/chain 列名が解釈できませんでした。\n"
            f"trimsequence.columns = {list(trimsequence.columns)}\n"
            f"想定フォーマット: '1A00 A', '1bzz B' など"
        )

    print(f"[getcoord] INFO: {len(pdb_chains)} 構造の座標を読み込みます")

    used_structures = 0
    failed_structures = []

    for pc in pdb_chains:
        coord_path = _find_coord_file(pc, atom_coord_base)
        if coord_path is None:
            print(
                f"[getcoord] WARNING: {pc.label} の座標ファイルが見つかりません "
                f"(探索ディレクトリ: {atom_coord_base})"
            )
            failed_structures.append(pc.label)
            continue

        try:
            coord_df = _load_coord_table(coord_path)
        except Exception as e:
            print(f"[getcoord] WARNING: {coord_path.name} の読み込みに失敗: {e}")
            failed_structures.append(pc.label)
            continue

        # x, y, z 列が正しく取得できているか確認
        if not all(c in coord_df.columns for c in ["x", "y", "z"]):
            print(
                f"[getcoord] WARNING: {coord_path.name} に x, y, z 列がありません。スキップします。"
            )
            failed_structures.append(pc.label)
            continue

        # 残基数の整合性チェック
        if len(coord_df) < num_residues:
            pad_len = num_residues - len(coord_df)
            print(
                f"[getcoord] INFO: {pc.label} の座標行数({len(coord_df)})が "
                f"trimsequence の残基数({num_residues})より少ないため、"
                f"末尾を NaN で埋めます (+{pad_len} 行)"
            )
            pad = pd.DataFrame(
                {
                    "x": [np.nan] * pad_len,
                    "y": [np.nan] * pad_len,
                    "z": [np.nan] * pad_len,
                }
            )
            coord_df = pd.concat([coord_df, pad], axis=0, ignore_index=True)

        elif len(coord_df) > num_residues:
            print(
                f"[getcoord] INFO: {pc.label} の座標行数({len(coord_df)})が "
                f"trimsequence の残基数({num_residues})より多いため、"
                f"先頭 {num_residues} 行のみを使用します"
            )
            coord_df = coord_df.iloc[:num_residues].reset_index(drop=True)

        else:
            coord_df = coord_df.reset_index(drop=True)

        # 4 列ブロック: [label, x, y, z]
        label_series = pd.Series([pc.label] * num_residues)

        block = pd.DataFrame(
            {
                f"label_{pc.pdbid}_{pc.chain}": label_series,
                f"x_{pc.pdbid}_{pc.chain}": coord_df["x"].values,
                f"y_{pc.pdbid}_{pc.chain}": coord_df["y"].values,
                f"z_{pc.pdbid}_{pc.chain}": coord_df["z"].values,
            }
        )

        atomcoord = pd.concat([atomcoord, block], axis=1)
        used_structures += 1

    if used_structures == 0:
        raise RuntimeError(
            "getcoord: CA 座標が 1 つも取得できませんでした。\n"
            f"探索ディレクトリ: {atom_coord_base}\n"
            f"失敗した構造: {failed_structures}\n"
            "以下を確認してください:\n"
            "  1. atom_coord ディレクトリに CSV ファイルが存在するか\n"
            "  2. ファイル名が {pdbid}.csv 形式か (例: 1a00.csv)\n"
            "  3. CSV に x, y, z または Cartn_x, Cartn_y, Cartn_z 列があるか"
        )

    print(
        f"[getcoord] SUCCESS: {used_structures}/{len(pdb_chains)} 構造の座標を取得しました "
        f"(残基数: {num_residues})"
    )

    if failed_structures:
        print(f"[getcoord] 失敗した構造 ({len(failed_structures)}): {', '.join(failed_structures)}")

    return atomcoord
