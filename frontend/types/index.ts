// types/index.ts

export interface AnalyzeResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface ResidueData {
  index: number;
  residue_number: number;
  residue_name: string;
  flex_score: number;
  dsa_score: number;
}

export interface FlexStats {
  min: number;
  max: number;
  mean: number;
  median: number;
}

export interface UniProtLevelResult {
  uniprot_id: string;
  num_structures: number;
  num_conformations_total: number;
  num_residues: number;
  residues: ResidueData[];
  global_flex_stats: FlexStats;
  flex_presence_ratio?: number[];
}
