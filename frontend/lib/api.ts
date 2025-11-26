import axios from "axios";
import { AnalyzeResponse, JobStatus, UniProtLevelResult } from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const analyzeUniProt = async (
  uniprotId: string,
  maxStructures: number = 20
): Promise<AnalyzeResponse> => {
  const response = await apiClient.post("/analyze/uniprot", {
    uniprot_id: uniprotId,
    max_structures: maxStructures,
  });
  return response.data;
};

export const analyzePDB = async (
  file: File,
  chainId: string = "A",
  pdbId?: string
): Promise<AnalyzeResponse> => {
  const formData = new FormData();
  formData.append("pdb_file", file);
  formData.append("chain_id", chainId);
  if (pdbId) {
    formData.append("pdb_id", pdbId);
  }

  const response = await apiClient.post("/analyze", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response = await apiClient.get(`/status/${jobId}`);
  return response.data;
};

export const getUniProtResult = async (
  jobId: string
): Promise<UniProtLevelResult> => {
  const response = await apiClient.get(`/results/uniprot/${jobId}`);
  return response.data;
};

export const checkHealth = async () => {
  const response = await apiClient.get("/health");
  return response.data;
};
