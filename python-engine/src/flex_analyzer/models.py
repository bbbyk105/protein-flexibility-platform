"""Pydantic モデル定義 - Notebook DSA 準拠"""

from typing import List, Optional
from pydantic import BaseModel, Field


class PairScore(BaseModel):
    """ペアごとの DSA Score データ"""

    i: int = Field(..., description="Residue index i (1-based)")
    j: int = Field(..., description="Residue index j (1-based)")
    residue_pair: str = Field(..., description="Residue pair string (e.g., 'ALA-123, GLY-145')")
    distance_mean: float = Field(..., description="Mean distance across structures")
    distance_std: float = Field(..., description="Standard deviation of distance")
    score: float = Field(..., description="DSA score = distance_mean / distance_std")


class PerResidueScore(BaseModel):
    """残基ごとのスコア（3D 可視化用）"""

    index: int = Field(..., description="Residue index (0-based)")
    residue_number: int = Field(..., description="Residue number (1-based, UniProt)")
    residue_name: str = Field(..., description="Three-letter residue name")
    score: float = Field(..., description="Per-residue DSA score (average of related pairs)")


class Heatmap(BaseModel):
    """ヒートマップデータ"""

    size: int = Field(..., description="Matrix dimension (N x N)")
    values: List[List[Optional[float]]] = Field(..., description="2D matrix values (NaN as None)")


class CisInfo(BaseModel):
    """Cis ペプチド結合統計"""

    cis_dist_mean: float = Field(..., description="Mean distance of cis pairs")
    cis_dist_std: float = Field(..., description="Std deviation of cis pair distances")
    cis_score_mean: float = Field(..., description="Mean DSA score of cis pairs")
    cis_num: int = Field(..., description="Number of pairs that are cis in all structures")
    mix: int = Field(..., description="Number of pairs with mixed cis/trans conformations")
    cis_pairs: List[str] = Field(
        ..., description="List of cis pair indices (e.g., ['1, 2', '3, 4'])"
    )
    threshold: float = Field(..., description="Distance threshold used for cis detection (Å)")


class NotebookDSAResult(BaseModel):
    """Notebook DSA 解析結果（完全版）"""

    # メタデータ
    uniprot_id: str = Field(..., description="UniProt accession ID")
    num_structures: int = Field(..., description="Number of PDB structures used")
    num_residues: int = Field(..., description="Number of residues")
    pdb_ids: List[str] = Field(..., description="List of PDB IDs used")
    excluded_pdbs: List[str] = Field(
        default_factory=list, description="PDB IDs excluded due to errors"
    )
    seq_ratio: float = Field(..., description="Sequence alignment ratio threshold")
    method: str = Field(..., description="PDB method filter (e.g., 'X-ray diffraction')")
    
    # 追加メタデータ
    full_sequence_length: int = Field(..., description="Full UniProt sequence length")
    residue_coverage_percent: float = Field(..., description="Percentage of full sequence covered by residues")
    num_chains: int = Field(..., description="Number of chains used in analysis")
    top5_resolution_mean: Optional[float] = Field(None, description="Mean resolution of top 5 PDB structures (Å)")

    # グローバル指標
    umf: float = Field(..., description="UMF: mean of all pair scores")
    pair_score_mean: float = Field(..., description="Mean of pair scores")
    pair_score_std: float = Field(..., description="Std deviation of pair scores")

    # ペアごとの詳細
    pair_scores: List[PairScore] = Field(..., description="DSA scores for all residue pairs")

    # Per-residue スコア（3D 可視化用）
    per_residue_scores: List[PerResidueScore] = Field(..., description="Per-residue DSA scores")

    # ヒートマップ
    heatmap: Optional[Heatmap] = Field(None, description="Score heatmap matrix")

    # Cis 統計
    cis_info: CisInfo = Field(..., description="Cis peptide bond statistics")
