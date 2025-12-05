"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";

import Heatmap from "@/components/visualization/Heatmap";
import MolstarViewer from "@/components/visualization/MolstarViewer";

import type {
  JobStatus as DSAJobStatus,
  NotebookDSAResult,
  PerResidueScore,
} from "@/types/dsa";
import type { ResidueData } from "@/types";

interface ResultPageClientProps {
  jobId: string;
}

// PerResidueScore → ResidueData に変換
function toResidueData(list: PerResidueScore[]): ResidueData[] {
  return list.map((r) => ({
    index: r.index,
    residue_number: r.residue_number,
    residue_name: r.residue_name,
    dsa_score: r.score,
    // flex_score は DSA では未使用なので入れない（型上 optional にしておく）
  }));
}

export default function ResultPageClient({ jobId }: ResultPageClientProps) {
  const router = useRouter();

  const [jobStatus, setJobStatus] = useState<DSAJobStatus | null>(null);
  const [result, setResult] = useState<NotebookDSAResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------
  // 結果取得
  // -------------------------------
  const fetchResult = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8080/api/dsa/result/${jobId}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: NotebookDSAResult = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
      setError("結果の取得に失敗しました。時間をおいて再度お試しください。");
    }
  }, [jobId]);

  // -------------------------------
  // ステータスのポーリング
  // -------------------------------
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(
          `http://localhost:8080/api/dsa/status/${jobId}`,
          { cache: "no-store" }
        );

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data: DSAJobStatus = await res.json();
        setJobStatus(data);

        if (data.status === "completed") {
          clearInterval(timer);
          fetchResult();
        }

        if (data.status === "failed") {
          clearInterval(timer);
          setError(data.message || "解析に失敗しました。");
        }
      } catch (e) {
        console.error(e);
        setError("ステータス取得に失敗しました。サーバーを確認してください。");
      }
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [jobId, fetchResult]);

  // -------------------------------
  // ローディング・エラー表示
  // -------------------------------
  if (
    !jobStatus ||
    jobStatus.status === "pending" ||
    jobStatus.status === "processing"
  ) {
    return (
      <main className="max-w-4xl mx-auto py-16">
        <section className="bg-white border rounded-xl shadow-sm px-6 py-10 text-center">
          <div className="mx-auto mb-4 h-10 w-10 border-4 border-gray-300 border-t-black rounded-full animate-spin" />
          <h1 className="text-xl font-semibold text-gray-900">
            DSA 解析を実行中です
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            ジョブ ID: <span className="font-mono">{jobId}</span>
          </p>
          {jobStatus && (
            <p className="mt-2 text-xs text-gray-500">
              状態: {jobStatus.status} / {jobStatus.message}
            </p>
          )}
        </section>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-3xl mx-auto py-16">
        <section className="bg-white border border-red-100 rounded-xl shadow-sm px-6 py-10 text-center">
          <h1 className="text-2xl font-bold text-red-600">解析エラー</h1>
          <p className="mt-4 text-sm text-gray-700 whitespace-pre-wrap">
            {error}
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

  if (!result) {
    // completed なのに result がまだ無い一瞬の状態
    return (
      <main className="max-w-4xl mx-auto py-16">
        <section className="bg-white border rounded-xl shadow-sm px-6 py-10 text-center">
          <div className="mx-auto mb-4 h-8 w-8 border-4 border-gray-300 border-t-black rounded-full animate-spin" />
          <p className="text-sm text-gray-700">
            解析結果を取得しています。もう少々お待ちください…
          </p>
        </section>
      </main>
    );
  }

  // 表示用に変換
  const residues: ResidueData[] = toResidueData(
    result.per_residue_scores ?? []
  );
  const heatmapValues: (number | null)[][] = result.heatmap?.values ?? [];
  const primaryPdb = result.pdb_ids[0] ?? "";

  // -------------------------------
  // 本体 UI
  // -------------------------------
  return (
    <main className="max-w-6xl mx-auto py-10 space-y-10">
      {/* ヘッダー */}
      <header className="space-y-2">
        <p className="text-xs font-medium tracking-wide text-gray-500 uppercase">
          DSA Analysis Result
        </p>
        <h1 className="text-3xl font-bold text-gray-900">
          DSA 解析結果 – {result.uniprot_id}
        </h1>
        <p className="text-sm text-gray-600">
          ジョブ ID: <span className="font-mono">{jobStatus.job_id}</span>
        </p>
      </header>

      {/* 概要カード */}
      <section className="bg-white border rounded-xl shadow-sm px-6 py-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          解析概要 Overview
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-700">
          <div>
            <p className="text-xs text-gray-500">UniProt ID</p>
            <p className="mt-1 font-medium">{result.uniprot_id}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">構造数</p>
            <p className="mt-1 font-medium">{result.num_structures}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">残基数</p>
            <p className="mt-1 font-medium">{result.num_residues}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">UMF</p>
            <p className="mt-1 font-mono">{result.umf.toFixed(4)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">ペアスコア平均</p>
            <p className="mt-1 font-mono">
              {result.pair_score_mean.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">ペアスコア標準偏差</p>
            <p className="mt-1 font-mono">{result.pair_score_std.toFixed(2)}</p>
          </div>
          <div className="col-span-2 md:col-span-2">
            <p className="text-xs text-gray-500">使用 PDB ID</p>
            <p className="mt-1 font-mono text-xs">
              {result.pdb_ids.join(", ")}
            </p>
          </div>
        </div>
      </section>

      {/* 3D ビューア */}
      <section className="bg-white border rounded-xl shadow-sm px-6 py-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            3D 構造表示 (Mol* Viewer)
          </h2>
          <p className="text-xs text-gray-500">
            PDB: {primaryPdb || "N/A"} | Chain: A
          </p>
        </div>

        {primaryPdb ? (
          <MolstarViewer
            pdbId={primaryPdb}
            chainId="A"
            residues={residues}
            colorBy="dsa"
          />
        ) : (
          <p className="text-sm text-gray-600">
            使用可能な PDB ID がありません。
          </p>
        )}
      </section>

      {/* ヒートマップ */}
      <section className="bg-white border rounded-xl shadow-sm px-6 py-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          可変性ヒートマップ
        </h2>
        {heatmapValues.length === 0 ? (
          <p className="text-sm text-gray-600">
            ヒートマップデータがありません。
          </p>
        ) : (
          <Heatmap values={result.heatmap?.values ?? []} />
        )}
      </section>
    </main>
  );
}
