"""NumPyベクトル化による高速実装"""

import numpy as np
from typing import Tuple, List, Optional
from .utils import calculate_distance_matrix, safe_divide
from .models import (
    ResidueData,
    FlexStats,
    PairMatrix,
    PerStructureResult,
    UniProtLevelResult,
)


def compute_dsa_and_flex_fast(ca_coords: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    DSAスコアとflex_scoreを高速計算（NumPyベクトル化版）

    Args:
        ca_coords: 形状 (M, N, 3) のCα座標配列
                   M = 構造数、N = 残基数

    Returns:
        (dsa_matrix, std_matrix, flex_scores)
        - dsa_matrix: 形状 (N, N) のDSAスコア行列
        - std_matrix: 形状 (N, N) の距離標準偏差行列
        - flex_scores: 形状 (N,) の残基ごとの可変性スコア
    """
    M, N, _ = ca_coords.shape

    # 全構造の全ペア距離を一括計算
    distance_matrices = np.zeros((M, N, N), dtype=np.float64)
    for k in range(M):
        distance_matrices[k] = calculate_distance_matrix(ca_coords[k])

    # 各ペアの平均距離と標準偏差を計算（構造間での統計量）
    mean_distances = np.mean(distance_matrices, axis=0)  # (N, N)
    std_distances = np.std(distance_matrices, axis=0, ddof=1 if M > 1 else 0)  # (N, N)

    # DSAスコア = 平均距離 / 標準偏差
    dsa_matrix = safe_divide(mean_distances, std_distances, epsilon=1e-8)

    # 対角成分は0にする
    np.fill_diagonal(dsa_matrix, 0.0)
    np.fill_diagonal(std_distances, 0.0)

    # flex_score: 各残基について、関連するペアの標準偏差の平均
    row_mean = np.mean(std_distances, axis=1)  # (N,)
    col_mean = np.mean(std_distances, axis=0)  # (N,)
    flex_scores = (row_mean + col_mean) / 2.0  # (N,)

    return dsa_matrix, std_distances, flex_scores


def _create_flex_mask(std_matrix: np.ndarray, score_threshold: float = 0.5) -> np.ndarray:
    """
    標準偏差行列からflex_maskを作成（内部ヘルパー関数）

    Args:
        std_matrix: 形状 (N, N) の標準偏差行列
        score_threshold: 閾値（std > threshold で flex）

    Returns:
        flex_mask: 形状 (N, N) のbool配列
    """
    N = std_matrix.shape[0]
    flex_mask = std_matrix > score_threshold

    # 対角は必ずFalse
    np.fill_diagonal(flex_mask, False)

    # 対称性を保証
    flex_mask = np.logical_or(flex_mask, flex_mask.T)

    return flex_mask


def _flatten_upper_triangle(matrix: np.ndarray) -> List[float]:
    """
    上三角行列（対角除く）を1次元配列にflatten

    Args:
        matrix: 形状 (N, N) の行列

    Returns:
        flatten済みリスト（長さ N*(N-1)/2）
    """
    N = matrix.shape[0]
    flattened = []
    for i in range(N):
        for j in range(i + 1, N):
            flattened.append(float(matrix[i, j]))
    return flattened


def compute_uniprot_level_flex(
    structure_coords_list: List[np.ndarray],
    residues: List[ResidueData],
    pdb_ids: List[str],
    uniprot_id: str,
    chain_ids: Optional[List[str]] = None,
    score_threshold: float = 0.5,
    flex_ratio_threshold: float = 0.5,
) -> UniProtLevelResult:
    """
    UniProtレベルの2段階揺らぎ解析（完全版）

    Args:
        structure_coords_list: 各PDB構造グループの座標配列リスト
                               structure_coords_list[i] は形状 (M_i, N, 3)
        residues: 全構造共通の残基情報リスト（長さ N）
        pdb_ids: 各構造グループのPDB IDリスト
        uniprot_id: UniProt ID
        chain_ids: 各構造グループのチェーンIDリスト（Noneの場合は全て"A"）
        score_threshold: std閾値（デフォルト0.5）
        flex_ratio_threshold: 揺らぎ判定の閾値（デフォルト0.5 = 50%）

    Returns:
        UniProtLevelResult: 統合解析結果
    """
    num_structures = len(structure_coords_list)
    N = len(residues)

    if chain_ids is None:
        chain_ids = ["A"] * num_structures

    # === ステップ1: 各構造グループごとの解析 ===
    per_structure_results = []
    all_flex_masks = []  # 各構造のflex_mask（bool行列）

    for i, ca_coords in enumerate(structure_coords_list):
        M_i = ca_coords.shape[0]

        # DSA & flex計算
        dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

        # flex_mask作成
        flex_mask = _create_flex_mask(std_matrix, score_threshold=score_threshold)
        all_flex_masks.append(flex_mask)

        # FlexStats
        flex_stats = FlexStats(
            min=float(np.min(flex_scores)),
            max=float(np.max(flex_scores)),
            mean=float(np.mean(flex_scores)),
            median=float(np.median(flex_scores)),
        )

        # PairMatrix（flex_mask付き）
        pair_matrix = PairMatrix(
            type="dsa_score",
            size=N,
            values=dsa_matrix.tolist(),
            flex_mask=flex_mask.tolist(),
        )

        # PerStructureResult
        per_structure_results.append(
            PerStructureResult(
                pdb_id=pdb_ids[i],
                chain_id=chain_ids[i],
                num_conformations=M_i,
                flex_stats=flex_stats,
                pair_matrix=pair_matrix,
            )
        )

    # === ステップ2: UniProtレベルでの統合解析 ===
    # 全構造を結合
    coords_all = np.concatenate(structure_coords_list, axis=0)  # (M_total, N, 3)
    M_total = coords_all.shape[0]

    # グローバルDSA & flex計算
    global_dsa, global_std, global_flex_scores = compute_dsa_and_flex_fast(coords_all)

    # === ステップ3: flex_presence_ratio計算 ===
    flex_presence_matrix = np.zeros((N, N), dtype=np.float64)

    for i in range(N):
        for j in range(i + 1, N):
            # このペアが何個の構造でflexか
            count_flex = sum(mask[i, j] for mask in all_flex_masks)
            ratio = count_flex / num_structures
            flex_presence_matrix[i, j] = ratio
            flex_presence_matrix[j, i] = ratio

    # flatten
    flex_presence_ratio = _flatten_upper_triangle(flex_presence_matrix)

    # === ステップ4: 最終flex_mask（条件A OR 条件B） ===
    # 条件A: global_std > score_threshold
    condition_A = global_std > score_threshold

    # 条件B: flex_presence_ratio >= flex_ratio_threshold
    condition_B = flex_presence_matrix >= flex_ratio_threshold

    # 最終判定（A OR B）
    global_final_flex_mask = np.logical_or(condition_A, condition_B)

    # 対角は必ずFalse
    np.fill_diagonal(global_final_flex_mask, False)

    # グローバルFlexStats
    global_flex_stats = FlexStats(
        min=float(np.min(global_flex_scores)),
        max=float(np.max(global_flex_scores)),
        mean=float(np.mean(global_flex_scores)),
        median=float(np.median(global_flex_scores)),
    )

    # グローバルPairMatrix（final_flex_mask付き）
    global_pair_matrix = PairMatrix(
        type="final_flex",
        size=N,
        values=global_dsa.tolist(),
        flex_mask=global_final_flex_mask.tolist(),
    )

    # === ステップ5: 残基ごとのデータ（グローバルflex_scoreベース） ===
    residues_with_global = []
    for idx, res in enumerate(residues):
        # 各残基のDSAスコア平均（対角除く）
        dsa_values = np.concatenate([global_dsa[idx, :idx], global_dsa[idx, idx + 1 :]])
        avg_dsa = float(np.mean(dsa_values)) if len(dsa_values) > 0 else 0.0

        residues_with_global.append(
            ResidueData(
                index=res.index,
                residue_number=res.residue_number,
                residue_name=res.residue_name,
                flex_score=float(global_flex_scores[idx]),
                dsa_score=avg_dsa,
            )
        )

    # === 最終結果 ===
    return UniProtLevelResult(
        uniprot_id=uniprot_id,
        num_structures=num_structures,
        num_conformations_total=M_total,
        num_residues=N,
        residues=residues_with_global,
        global_flex_stats=global_flex_stats,
        global_pair_matrix=global_pair_matrix,
        per_structure_results=per_structure_results,
        flex_presence_ratio=flex_presence_ratio,
        flex_ratio_threshold=flex_ratio_threshold,
        score_threshold=score_threshold,
    )


# src/flex_analyzer/core.py に追記

from typing import Dict, Any, Tuple, List

import numpy as np

from .dsa import compute_dsa_stats, dsa_stats_to_dict


def analyze_flex_and_dsa_from_coords(
    ca_coords: np.ndarray,
    residue_info: List[Tuple[int, str]],
) -> Dict[str, Any]:
    """
    parser.extract_ca_coords_from_* で得られた Cα 座標と残基情報から、
    - 既存の Flex 解析（あなたの既存ロジックでやっているもの）
    - 追加の DSA/UMF 解析 (compute_dsa_stats)
    を合わせた dict を返すエントリポイントの一例。

    ここでは「DSA 部分」のみ作っているので、
    もし core.py に既に Flex 用の関数があるなら、
    その結果に DSA の dict をマージする形で使ってください。
    """

    if ca_coords.ndim != 3:
        raise ValueError(f"ca_coords must be (K, N, 3), got {ca_coords.shape}")

    K, N, _ = ca_coords.shape
    if len(residue_info) != N:
        raise ValueError(f"len(residue_info)={len(residue_info)} does not match coords N={N}")

    # --- DSA part ---
    dsa_stats = compute_dsa_stats(ca_coords)
    dsa_dict = dsa_stats_to_dict(dsa_stats)

    # per-residue 情報を組み立てておく（3D 色付け & テーブル用）
    per_residue = []
    for i, (res_seq, resname) in enumerate(residue_info):
        dsa_score = dsa_dict["per_residue_scores"][i]
        per_residue.append(
            {
                "index": int(res_seq),
                "resname": resname,
                "dsa_score": dsa_score,
            }
        )

    result: Dict[str, Any] = {
        "num_structures": int(dsa_dict["num_structures"]),
        "num_residues": int(dsa_dict["num_residues"]),
        "umf": dsa_dict["umf"],
        "dsa_pair_score_mean": dsa_dict["pair_score_mean"],
        "dsa_pair_score_std": dsa_dict["pair_score_std"],
        "dsa_main_plot": dsa_dict["main_plot_points"],
        "per_residue_dsa": per_residue,
        "cis": dsa_dict["cis"],
    }

    return result
