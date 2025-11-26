"""Pydanticモデル定義"""

from typing import List, Optional
from pydantic import BaseModel, Field


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
    """ペアワイズ行列データ"""

    type: str = Field(..., description="Matrix type: dsa_score or distance_std")
    size: int = Field(..., description="Matrix dimension (N x N)")
    values: List[List[float]] = Field(..., description="2D matrix values")


class AnalysisResult(BaseModel):
    """解析結果の全体構造"""

    job_id: str = Field(..., description="Unique job identifier")
    pdb_id: Optional[str] = Field(None, description="PDB ID if available")
    chain_id: str = Field(..., description="Chain identifier")
    num_structures: int = Field(..., description="Number of input structures")
    num_residues: int = Field(..., description="Number of residues analyzed")
    residues: List[ResidueData] = Field(..., description="Per-residue data")
    flex_stats: FlexStats = Field(..., description="Overall flexibility statistics")
    pair_matrix: PairMatrix = Field(..., description="Pairwise score matrix")
