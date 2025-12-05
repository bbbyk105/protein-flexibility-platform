// frontend/lib/api.ts

import type {
  AnalysisParams,
  JobResponse,
  JobStatus,
  NotebookDSAResult,
  ErrorResponse,
} from "@/types/dsa";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_DSA_API_URL ?? "http://localhost:8080";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const data = (await res.json()) as Partial<ErrorResponse>;
      if (data.error) {
        message = data.error;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(message);
  }
  return (await res.json()) as T;
}

export async function createDSAJob(
  params: AnalysisParams
): Promise<JobResponse> {
  const res = await fetch(`${API_BASE_URL}/api/dsa/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  return handleResponse<JobResponse>(res);
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE_URL}/api/dsa/status/${jobId}`, {
    method: "GET",
  });
  return handleResponse<JobStatus>(res);
}

export async function fetchJobResult(
  jobId: string
): Promise<NotebookDSAResult | ErrorResponse> {
  const res = await fetch(`${API_BASE_URL}/api/dsa/result/${jobId}`, {
    method: "GET",
  });
  // 結果 か エラー JSON が返ってくる想定
  return (await res.json()) as NotebookDSAResult | ErrorResponse;
}
