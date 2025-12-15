// frontend/lib/api.ts

import type {
  AnalysisParams,
  JobResponse,
  JobsResponse,
  JobStatus,
  NotebookDSAResult,
  ErrorResponse,
} from "@/types/dsa";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_DSA_API_URL ?? "http://localhost:8080";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    let errorData: any = null;
    try {
      const text = await res.text();
      console.log("[DEBUG] handleResponse - Error response text:", text);
      errorData = JSON.parse(text) as Partial<ErrorResponse>;
      if (errorData.error) {
        message = errorData.error;
      }
      console.log("[DEBUG] handleResponse - Error data:", errorData);
    } catch (e) {
      console.log(
        "[DEBUG] handleResponse - Failed to parse error response:",
        e
      );
      // ignore json parse error
    }
    console.error("[DEBUG] handleResponse - Throwing error:", message);
    throw new Error(message);
  }
  const jsonData = await res.json();
  console.log("[DEBUG] handleResponse - Success response:", jsonData);
  return jsonData as T;
}

export async function createDSAJob(
  params: AnalysisParams
): Promise<JobsResponse> {
  // デバッグ: 送信するパラメータをログ出力
  console.log(
    "[DEBUG] createDSAJob - Sending params:",
    JSON.stringify(params, null, 2)
  );
  console.log(
    "[DEBUG] createDSAJob - API URL:",
    `${API_BASE_URL}/api/dsa/analyze`
  );

  const requestBody = JSON.stringify(params);
  console.log("[DEBUG] createDSAJob - Request body:", requestBody);

  const res = await fetch(`${API_BASE_URL}/api/dsa/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: requestBody,
  });

  console.log("[DEBUG] createDSAJob - Response status:", res.status);
  console.log("[DEBUG] createDSAJob - Response ok:", res.ok);

  return handleResponse<JobsResponse>(res);
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
