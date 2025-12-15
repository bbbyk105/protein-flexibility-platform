// frontend/types/dsa.ts

export interface AnalysisParams {
  uniprot_ids: string; // 複数対応（カンマまたはスペース区切り）
  method?: string; // "X-ray", "NMR", "EM"
  seq_ratio?: number; // 0.0-1.0
  negative_pdbid?: string; // 除外するPDB ID（スペースまたはカンマ区切り）
  cis_threshold?: number; // cis判定の距離閾値
  export?: boolean; // CSV出力するか
  heatmap?: boolean; // ヒートマップを生成するか
  proc_cis?: boolean; // cis解析を行うか
  overwrite?: boolean; // 上書きするか
}

export interface JobResponse {
  job_id: string;
  status: string;
  created_at: string; // ISO string
}

export interface JobsResponse {
  jobs: JobResponse[];
  created_at: string; // ISO string
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
}

// ---- NotebookDSAResult ----

export interface PairScore {
  i: number; // 1-based
  j: number; // 1-based
  residue_pair: string; // "ALA-123, GLY-145"
  distance_mean: number;
  distance_std: number;
  score: number;
}

export interface PerResidueScore {
  index: number; // 0-based
  residue_number: number; // 1-based
  residue_name: string;
  score: number;
}

export interface Heatmap {
  size: number;
  values: (number | null)[][]; // NaN は null として受ける前提
}

export interface CisInfo {
  cis_dist_mean: number;
  cis_dist_std: number;
  cis_score_mean: number;
  cis_num: number;
  mix: number;
  cis_pairs: string[]; // "1, 2" 形式
  threshold: number;
}

export interface NotebookDSAResult {
  // メタデータ
  uniprot_id: string;
  num_structures: number;
  num_residues: number;
  pdb_ids: string[];
  excluded_pdbs: string[];
  seq_ratio: number;
  method: string;

  // 追加メタデータ
  full_sequence_length: number;
  residue_coverage_percent: number;
  num_chains: number;
  top5_resolution_mean: number | null;

  // グローバル指標
  umf: number;
  pair_score_mean: number;
  pair_score_std: number;

  // ペアごとの詳細
  pair_scores: PairScore[];

  // Per-residue スコア
  per_residue_scores: PerResidueScore[];

  // ヒートマップ
  heatmap: Heatmap | null;

  // Cis 統計
  cis_info: CisInfo;
}

export interface ErrorResponse {
  error: string;
  partial_result?: unknown;
}
