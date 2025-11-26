"""Pydanticモデル定義"""

from typing import List, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import List
import numpy as np


class ResidueData(BaseModel):
    """残基ごとのデータ"""

    index: int = Field(..., description="0-indexed position in the sequence")
    residue_number: int = Field(..., description="PDB residue number")
    residue_name: str = Field(..., description="Three-letter residue name")
    flex_score: float = Field(..., description="Flexibility score for this residue")
    dsa_score: Optional[float] = Field(None, description="Average DSA score for this residue")


class FlexStats(BaseModel):
    """統計情報"""

    min: float = Field(..., description="Minimum flex_score")
    max: float = Field(..., description="Maximum flex_score")
    mean: float = Field(..., description="Mean flex_score")
    median: float = Field(..., description="Median flex_score")


class PairMatrix(BaseModel):
    """ペアワイズ行列データ（拡張版: flex_mask対応）"""

    type: str = Field(..., description="Matrix type: dsa_score, distance_std, or final_flex")
    size: int = Field(..., description="Matrix dimension (N x N)")
    values: List[List[float]] = Field(..., description="2D matrix values")
    flex_mask: Optional[List[List[bool]]] = Field(
        None, description="Boolean mask indicating flexible pairs (True = flexible)"
    )

    def flatten_upper_triangle(self, matrix_type: str = "values") -> List[float]:
        """
        上三角部分（対角除く）をflatten

        Args:
            matrix_type: "values" or "flex_mask"

        Returns:
            flatten済みリスト（長さ N*(N-1)/2）
        """
        N = self.size
        flattened = []

        if matrix_type == "values":
            for i in range(N):
                for j in range(i + 1, N):
                    flattened.append(self.values[i][j])
        elif matrix_type == "flex_mask" and self.flex_mask is not None:
            for i in range(N):
                for j in range(i + 1, N):
                    flattened.append(self.flex_mask[i][j])

        return flattened


class AnalysisResult(BaseModel):
    """解析結果の全体構造（単一構造グループ用）"""

    job_id: str = Field(..., description="Unique job identifier")
    pdb_id: Optional[str] = Field(None, description="PDB ID if available")
    chain_id: str = Field(..., description="Chain identifier")
    num_structures: int = Field(..., description="Number of input structures")
    num_residues: int = Field(..., description="Number of residues analyzed")
    residues: List[ResidueData] = Field(..., description="Per-residue data")
    flex_stats: FlexStats = Field(..., description="Overall flexibility statistics")
    pair_matrix: PairMatrix = Field(..., description="Pairwise score matrix")


class PerStructureResult(BaseModel):
    """各PDB構造グループの解析結果"""

    pdb_id: str = Field(..., description="PDB ID")
    chain_id: Optional[str] = Field(None, description="Chain identifier")
    num_conformations: int = Field(
        ..., description="Number of conformations in this structure group"
    )
    flex_stats: FlexStats = Field(..., description="Flexibility statistics for this structure")
    pair_matrix: PairMatrix = Field(..., description="Pairwise score matrix with flex_mask")


class UniProtLevelResult(BaseModel):
    """UniProtレベルの統合解析結果（複数PDB構造を統合）"""

    uniprot_id: str = Field(..., description="UniProt accession ID")
    num_structures: int = Field(..., description="Number of PDB structure groups")
    num_conformations_total: int = Field(
        ..., description="Total number of conformations across all structures"
    )
    num_residues: int = Field(..., description="Number of common residues")
    residues: List[ResidueData] = Field(
        ..., description="Per-residue data (based on global analysis)"
    )

    # UniProt全体でのDSA/flex結果
    global_flex_stats: FlexStats = Field(
        ..., description="Global flexibility statistics across all structures"
    )
    global_pair_matrix: PairMatrix = Field(
        ..., description="Global pairwise score matrix with final_flex_mask"
    )

    # 構造ごとの詳細
    per_structure_results: List[PerStructureResult] = Field(
        ..., description="Individual structure analysis results"
    )

    # ペアごとの「構造の何%でflexか」の統計（flatten形式）
    flex_presence_ratio: List[float] = Field(
        ...,
        description="Ratio of structures where each pair is flexible (upper triangle flattened)",
    )
    flex_ratio_threshold: float = Field(
        ..., description="Threshold used for flex presence determination"
    )
    score_threshold: float = Field(
        default=0.5, description="Threshold for std to be considered flexible"
    )


@dataclass
class StructureSet:
    """
    UniProt / AlphaFold / 手動PDB などから集めた
    「解析可能な構造の束」を表すコンテナ。

    core.compute_uniprot_level_flex に渡すための共通フォーマット。
    """

    # ユーザーが入力した UniProt ID（Inactive かもしれない）
    uniprot_id_input: str

    # 実際に解析に使った Active な UniProt ID
    # 例: P62988 (入力) → P62987 (resolved)
    uniprot_id_resolved: str

    # shape: (M_total, N, 3) 全構造・全残基の Cα 座標
    coords: np.ndarray

    # 残基情報（既存の ResidueData を利用）
    residues: List["ResidueData"]

    # 実際に解析に使った PDB ID 一覧
    pdb_ids: List[str]

    # 各構造に対応するチェーンID（とりあえず全部 "A" でもOK）
    chain_ids: List[str]

    # 構造の出どころ（将来 AlphaFold なども区別したいので文字列で持つ）
    # 例: "uniprot_pdb", "alphafold", "manual_pdb"
    source: str = "uniprot_pdb"

    # 残基数ミスマッチなどで除外された PDB ID
    excluded_pdbs: List[str] = field(default_factory=list)
