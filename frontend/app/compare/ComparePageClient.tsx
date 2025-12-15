"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type {
  JobStatus as DSAJobStatus,
  NotebookDSAResult,
} from "@/types/dsa";
import { HeatmapImage } from "@/components/visualization/HeatmapImage";
import { DistanceScorePlot } from "@/components/visualization/DistanceScorePlot";

interface ComparePageClientProps {
  jobIds: string[];
}

interface JobData {
  jobId: string;
  status: DSAJobStatus | null;
  result: NotebookDSAResult | null;
  error: string | null;
}

export default function ComparePageClient({
  jobIds,
}: ComparePageClientProps) {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobData[]>(
    jobIds.map((id) => ({
      jobId: id,
      status: null,
      result: null,
      error: null,
    }))
  );

  // 各ジョブのステータスを取得
  const fetchJobStatus = useCallback(
    async (jobId: string): Promise<DSAJobStatus | null> => {
      try {
        const res = await fetch(
          `http://localhost:8080/api/dsa/status/${jobId}`,
          { cache: "no-store" }
        );
        if (!res.ok) {
          return null;
        }
        return await res.json();
      } catch (e) {
        console.error(`Failed to fetch status for ${jobId}:`, e);
        return null;
      }
    },
    []
  );

  // 各ジョブの結果を取得
  const fetchJobResult = useCallback(
    async (jobId: string): Promise<NotebookDSAResult | null> => {
      try {
        const res = await fetch(
          `http://localhost:8080/api/dsa/result/${jobId}`,
          { cache: "no-store" }
        );
        if (!res.ok) {
          return null;
        }
        return await res.json();
      } catch (e) {
        console.error(`Failed to fetch result for ${jobId}:`, e);
        return null;
      }
    },
    []
  );

  // ステータスのポーリング
  useEffect(() => {
    if (jobIds.length === 0) {
      return;
    }

    const timer = setInterval(async () => {
      const updatedJobs = await Promise.all(
        jobs.map(async (job) => {
          // 既に完了している場合はスキップ
          if (job.result || job.error) {
            return job;
          }

          const status = await fetchJobStatus(job.jobId);
          if (!status) {
            return job;
          }

          // ステータスが完了したら結果を取得
          if (status.status === "completed") {
            const result = await fetchJobResult(job.jobId);
            if (result) {
              return { ...job, status, result };
            }
          }

          // ステータスが失敗したらエラーを設定
          if (status.status === "failed") {
            return {
              ...job,
              status,
              error: status.message || "解析に失敗しました",
            };
          }

          return { ...job, status };
        })
      );

      setJobs(updatedJobs);
    }, 2000);

    return () => {
      clearInterval(timer);
    };
  }, [jobIds, jobs, fetchJobStatus, fetchJobResult]);

  // 初期ロード時にステータスを取得
  useEffect(() => {
    const loadInitialStatus = async () => {
      const initialJobs = await Promise.all(
        jobIds.map(async (jobId) => {
          const status = await fetchJobStatus(jobId);
          return {
            jobId,
            status,
            result: null,
            error: null,
          };
        })
      );
      setJobs(initialJobs);
    };

    if (jobIds.length > 0) {
      loadInitialStatus();
    }
  }, [jobIds, fetchJobStatus]);

  // すべてのジョブが完了しているかチェック
  const allCompleted = jobs.every(
    (job) => job.result !== null || job.error !== null
  );
  const allPending = jobs.every(
    (job) =>
      job.status === null ||
      job.status.status === "pending" ||
      job.status.status === "processing"
  );

  // ローディング表示
  if (allPending && !allCompleted) {
    return (
      <main className="max-w-6xl mx-auto py-16">
        <section className="bg-white border rounded-xl shadow-sm px-6 py-10 text-center">
          <div className="mx-auto mb-4 h-10 w-10 border-4 border-gray-300 border-t-black rounded-full animate-spin" />
          <h1 className="text-xl font-semibold text-gray-900">
            複数の解析を実行中です
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            {jobs.length} 件のジョブを処理中...
          </p>
        </section>
      </main>
    );
  }

  // エラー表示（すべてエラーの場合）
  if (jobs.every((job) => job.error !== null)) {
    return (
      <main className="max-w-3xl mx-auto py-16">
        <section className="bg-white border border-red-100 rounded-xl shadow-sm px-6 py-10 text-center">
          <h1 className="text-2xl font-bold text-red-600">解析エラー</h1>
          <p className="mt-4 text-sm text-gray-700">
            すべての解析に失敗しました。
          </p>
          <button
            onClick={() => router.push("/")}
            className="mt-8 inline-flex items-center px-4 py-2 rounded-md bg-black text-white text-sm font-medium hover:bg-gray-800 transition"
          >
            ホームに戻る
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="max-w-7xl mx-auto py-10 space-y-8">
      {/* ヘッダー */}
      <header className="space-y-2">
        <p className="text-xs font-medium tracking-wide text-gray-500 uppercase">
          DSA Analysis Comparison
        </p>
        <h1 className="text-3xl font-bold text-gray-900">
          解析結果の比較 ({jobs.length} 件)
        </h1>
        <p className="text-sm text-gray-600">
          複数のUniProt IDの解析結果を並べて比較できます
        </p>
      </header>

      {/* 比較テーブル - 概要 */}
      <section className="bg-white border rounded-xl shadow-sm px-6 py-5 overflow-x-auto">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          解析概要の比較
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  UniProt ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ステータス
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  エントリ数
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  チェーン数
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  残基数
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  UMF
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cisペア数
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.map((job, index) => (
                <tr key={job.jobId} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap font-medium">
                    {job.result?.uniprot_id || job.status?.job_id || "N/A"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.error ? (
                      <span className="px-2 py-1 text-xs font-medium text-red-800 bg-red-100 rounded">
                        失敗
                      </span>
                    ) : job.result ? (
                      <span className="px-2 py-1 text-xs font-medium text-green-800 bg-green-100 rounded">
                        完了
                      </span>
                    ) : job.status?.status === "processing" ? (
                      <span className="px-2 py-1 text-xs font-medium text-blue-800 bg-blue-100 rounded">
                        処理中
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-medium text-gray-800 bg-gray-100 rounded">
                        待機中
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.result?.num_structures || "-"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.result?.num_chains || job.result?.num_structures || "-"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.result?.num_residues || "-"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap font-mono font-semibold text-blue-600">
                    {job.result?.umf.toFixed(1) || "-"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.result?.cis_info?.cis_num || "-"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {job.result && (
                      <Link
                        href={`/results/${job.jobId}`}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                      >
                        詳細を見る
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 各ジョブの詳細結果を並べて表示 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {jobs.map((job) => {
          if (!job.result) {
            return null;
          }

          return (
            <div
              key={job.jobId}
              className="bg-white border rounded-xl shadow-sm p-6 space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  {job.result.uniprot_id}
                </h3>
                <Link
                  href={`/results/${job.jobId}`}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  詳細 →
                </Link>
              </div>

              {/* 主要指標 */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-gray-500">UMF</p>
                  <p className="mt-1 font-mono font-semibold text-blue-600 text-lg">
                    {job.result.umf.toFixed(1)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">エントリ数</p>
                  <p className="mt-1 font-medium">{job.result.num_structures}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">残基数</p>
                  <p className="mt-1 font-medium">{job.result.num_residues}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Cisペア数</p>
                  <p className="mt-1 font-medium text-purple-600">
                    {job.result.cis_info?.cis_num || 0}
                  </p>
                </div>
              </div>

              {/* ヒートマップ */}
              {job.result.heatmap && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    可変性ヒートマップ
                  </h4>
                  <div className="border rounded-lg overflow-hidden">
                    <HeatmapImage jobId={job.jobId} />
                  </div>
                </div>
              )}

              {/* Distance-Score Plot */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Distance-Score Plot
                </h4>
                <div className="border rounded-lg overflow-hidden">
                  <DistanceScorePlot jobId={job.jobId} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* エラーがあるジョブの表示 */}
      {jobs.some((job) => job.error) && (
        <section className="bg-red-50 border border-red-200 rounded-xl shadow-sm px-6 py-5">
          <h2 className="text-lg font-semibold text-red-900 mb-4">
            エラーが発生したジョブ
          </h2>
          <div className="space-y-2">
            {jobs
              .filter((job) => job.error)
              .map((job) => (
                <div key={job.jobId} className="text-sm">
                  <p className="font-medium text-red-900">
                    ジョブ ID: {job.jobId}
                  </p>
                  <p className="text-red-700 mt-1">{job.error}</p>
                </div>
              ))}
          </div>
        </section>
      )}
    </main>
  );
}

