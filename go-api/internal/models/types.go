// internal/models/types.go
package models

// AnalyzeRequest はPDB解析リクエスト
type AnalyzeRequest struct {
	ChainID string `json:"chain_id"`
}

// AnalyzeResponse は解析開始レスポンス
type AnalyzeResponse struct {
	JobID   string `json:"job_id"`
	Status  string `json:"status"`
	Message string `json:"message"`
}

// UniProtAnalyzeRequest はUniProt解析リクエスト
type UniProtAnalyzeRequest struct {
	UniProtID     string `json:"uniprot_id" validate:"required"`
	MaxStructures int    `json:"max_structures,omitempty"` // デフォルト: 20
}

// ResidueData は残基ごとのデータ（Python models.pyと一致）
type ResidueData struct {
	Index         int     `json:"index"`
	ResidueNumber int     `json:"residue_number"`
	ResidueName   string  `json:"residue_name"`
	FlexScore     float64 `json:"flex_score"`
	DSAScore      float64 `json:"dsa_score"`
}

// FlexStats は統計情報（Python models.pyと一致）
type FlexStats struct {
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
	Mean   float64 `json:"mean"`
	Median float64 `json:"median"`
}

// PairMatrix はペアワイズ行列（Python models.pyと一致）
type PairMatrix struct {
	Type     string      `json:"type"`
	Size     int         `json:"size"`
	Values   [][]float64 `json:"values,omitempty"`
	Data     []float64   `json:"data,omitempty"`      // UniProtレベル解析用
	FlexMask [][]bool    `json:"flex_mask,omitempty"` // UniProtレベル解析用
}

// AnalysisResult は解析結果全体（Python models.pyと一致）
type AnalysisResult struct {
	JobID         string        `json:"job_id"`
	PDBID         *string       `json:"pdb_id"`
	ChainID       string        `json:"chain_id"`
	NumStructures int           `json:"num_structures"`
	NumResidues   int           `json:"num_residues"`
	Residues      []ResidueData `json:"residues"`
	FlexStats     FlexStats     `json:"flex_stats"`
	PairMatrix    PairMatrix    `json:"pair_matrix"`
}

// PerStructureResult は各構造の解析結果（UniProtレベル解析用）
type PerStructureResult struct {
	PDBID            string     `json:"pdb_id"`
	ChainID          string     `json:"chain_id"`
	NumConformations int        `json:"num_conformations"`
	FlexStats        FlexStats  `json:"flex_stats"`
	PairMatrix       PairMatrix `json:"pair_matrix"`
}

// ===========================
//       ▼ DSA / UMF ▼
// ===========================

// DSAPerResidue は各残基の DSA スコア
type DSAPerResidue struct {
	Index   int     `json:"index"`
	ResName string  `json:"resname"`
	Score   float64 `json:"dsa_score"`
}

// DSAMainPoint は DSA のメインプロット（距離 vs スコア）用
type DSAMainPoint struct {
	MeanDistance float64 `json:"mean_distance"`
	Score        float64 `json:"score"`
}

// DSACisInfo は cis 近傍残基情報
type DSACisInfo struct {
	Threshold     float64   `json:"threshold"`
	NumPositions  int       `json:"num_positions"`
	Positions     []int     `json:"positions"`
	MeanDistances []float64 `json:"mean_distances"`
}

// DSAResult は DSA 全体結果
type DSAResult struct {
	NumStructures    int             `json:"num_structures"`
	NumResidues      int             `json:"num_residues"`
	UMF              float64         `json:"umf"`
	PairScoreMean    float64         `json:"dsa_pair_score_mean"`
	PairScoreStd     float64         `json:"dsa_pair_score_std"`
	MainPlotPoints   []DSAMainPoint  `json:"dsa_main_plot"`
	PerResidueScores []DSAPerResidue `json:"per_residue_dsa"`
	Cis              DSACisInfo      `json:"cis"`
}

// UniProtLevelResult はUniProtレベルの解析結果
type UniProtLevelResult struct {
	UniProtID             string               `json:"uniprot_id"`
	NumStructures         int                  `json:"num_structures"`
	NumConformationsTotal int                  `json:"num_conformations_total"`
	NumResidues           int                  `json:"num_residues"`
	Residues              []ResidueData        `json:"residues"`
	GlobalFlexStats       FlexStats            `json:"global_flex_stats"`
	GlobalPairMatrix      PairMatrix           `json:"global_pair_matrix"`
	PerStructureResults   []PerStructureResult `json:"per_structure_results"`
	FlexPresenceRatio     []float64            `json:"flex_presence_ratio"`
	FlexRatioThreshold    float64              `json:"flex_ratio_threshold"`
	ScoreThreshold        float64              `json:"score_threshold"`

	// Python 側が JSON の "dsa" に入れてくる DSA / UMF 結果
	DSA *DSAResult `json:"dsa,omitempty"`
}

// ErrorResponse はエラーレスポンス
type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

// JobStatus はジョブステータス
type JobStatus struct {
	JobID     string `json:"job_id"`
	Status    string `json:"status"` // "pending", "processing", "completed", "failed"
	Message   string `json:"message,omitempty"`
	Progress  int    `json:"progress,omitempty"` // 0-100
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}
