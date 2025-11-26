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
	Type   string        `json:"type"`
	Size   int           `json:"size"`
	Values [][]float64   `json:"values"`
}

// AnalysisResult は解析結果全体（Python models.pyと一致）
type AnalysisResult struct {
	JobID         string       `json:"job_id"`
	PDBID         *string      `json:"pdb_id"`
	ChainID       string       `json:"chain_id"`
	NumStructures int          `json:"num_structures"`
	NumResidues   int          `json:"num_residues"`
	Residues      []ResidueData `json:"residues"`
	FlexStats     FlexStats    `json:"flex_stats"`
	PairMatrix    PairMatrix   `json:"pair_matrix"`
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
