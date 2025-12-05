// types/index.ts

export interface AnalyzeResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  message?: string;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface ResidueData {
  index: number;
  residue_number: number;
  residue_name: string;
  dsa_score: number;
}

export interface FlexStats {
  min: number;
  max: number;
  mean: number;
  median: number;
}

export interface PairMatrix {
  type: string;
  size: number;
  values?: number[][];
  data?: number[];
  flex_mask?: boolean[][];
}

export interface PerStructureResult {
  pdb_id: string;
  chain_id: string;
  num_conformations: number;
  flex_stats: FlexStats;
  pair_matrix: PairMatrix;
}

export interface UniProtLevelResult {
  uniprot_id: string;
  num_structures: number;
  num_conformations_total: number;
  num_residues: number;
  residues: ResidueData[];
  global_flex_stats: FlexStats;
  global_pair_matrix?: PairMatrix;
  per_structure_results?: PerStructureResult[];
  flex_presence_ratio?: number[];
  flex_ratio_threshold?: number;
  score_threshold?: number;
}

// 3D Viewer用の型
export type ColorMode = "flex" | "dsa" | "bfactor";

export interface StructureViewerProps {
  pdbId: string;
  chainId: string;
  residues: ResidueData[];
  colorBy: ColorMode;
  onResidueClick?: (residueIndex: number) => void;
  highlightedResidue?: number | null;
}
