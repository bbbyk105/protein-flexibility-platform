package models

import "time"

// AnalysisParams は解析リクエストのパラメータ
type AnalysisParams struct {
	UniProtID     string  `json:"uniprot_id" binding:"required"`
	MaxStructures int     `json:"max_structures"`
	SeqRatio      float64 `json:"seq_ratio"`
	CisThreshold  float64 `json:"cis_threshold"`
	Method        string  `json:"method"`
}

// JobResponse はジョブ作成時のレスポンス
type JobResponse struct {
	JobID     string    `json:"job_id"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
}

// JobStatus はジョブの状態を表す
type JobStatus struct {
	JobID     string    `json:"job_id"`
	Status    string    `json:"status"` // "pending" | "processing" | "completed" | "failed"
	Progress  int       `json:"progress"`
	Message   string    `json:"message"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// NotebookDSAResult はPythonエンジンの出力結果（仕様書のスキーマ）
type NotebookDSAResult struct {
	// メタデータ
	UniProtID     string   `json:"uniprot_id"`
	NumStructures int      `json:"num_structures"`
	NumResidues   int      `json:"num_residues"`
	PDBIDs        []string `json:"pdb_ids"`
	ExcludedPDBs  []string `json:"excluded_pdbs"`
	SeqRatio      float64  `json:"seq_ratio"`
	Method        string   `json:"method"`

	// グローバル指標
	UMF           float64 `json:"umf"`
	PairScoreMean float64 `json:"pair_score_mean"`
	PairScoreStd  float64 `json:"pair_score_std"`

	// ペアごとの詳細
	PairScores []PairScore `json:"pair_scores"`

	// Per-residue スコア（3D 可視化用）
	PerResidueScores []PerResidueScore `json:"per_residue_scores"`

	// ヒートマップ（N×N 行列）
	Heatmap *Heatmap `json:"heatmap"`

	// Cis 統計
	CisInfo CisInfo `json:"cis_info"`
}

// PairScore はペアごとのスコア
type PairScore struct {
	I            int     `json:"i"`             // 1-based
	J            int     `json:"j"`             // 1-based
	ResiduePair  string  `json:"residue_pair"`  // "ALA-123, GLY-145"
	DistanceMean float64 `json:"distance_mean"`
	DistanceStd  float64 `json:"distance_std"`
	Score        float64 `json:"score"`
}

// PerResidueScore は残基ごとのスコア
type PerResidueScore struct {
	Index         int     `json:"index"`          // 0-based
	ResidueNumber int     `json:"residue_number"` // 1-based (UniProt)
	ResidueName   string  `json:"residue_name"`
	Score         float64 `json:"score"`
}

// Heatmap はN×N行列
type Heatmap struct {
	Size   int         `json:"size"`
	Values [][]float64 `json:"values"` // NaN を含む
}

// CisInfo はCisペプチド結合の統計情報
type CisInfo struct {
	CisDistMean  float64  `json:"cis_dist_mean"`
	CisDistStd   float64  `json:"cis_dist_std"`
	CisScoreMean float64  `json:"cis_score_mean"`
	CisNum       int      `json:"cis_num"`   // 全構造で常にcisのペア数
	Mix          int      `json:"mix"`       // cis/trans混在ペア数
	CisPairs     []string `json:"cis_pairs"` // ["1, 2", "3, 4", ...]
	Threshold    float64  `json:"threshold"`
}

// ErrorResponse はエラー時のレスポンス
type ErrorResponse struct {
	Error         string                 `json:"error"`
	PartialResult map[string]interface{} `json:"partial_result,omitempty"`
}