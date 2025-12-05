// frontend/app/analyze/page.tsx
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createDSAJob } from "@/lib/api";
import type { AnalysisParams } from "@/types/dsa";

export default function AnalyzePage() {
  const router = useRouter();

  const [uniprotId, setUniprotId] = useState("P69905");
  const [maxStructures, setMaxStructures] = useState<number>(20);
  const [seqRatio, setSeqRatio] = useState<number>(0.9);
  const [cisThreshold, setCisThreshold] = useState<number>(3.8);
  const [method, setMethod] = useState<string>("X-ray diffraction");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const params: AnalysisParams = {
        uniprot_id: uniprotId.trim(),
        max_structures: maxStructures,
        seq_ratio: seqRatio,
        cis_threshold: cisThreshold,
        method, // ← ここで "X-ray diffraction" を渡す
      };

      const job = await createDSAJob(params);

      // /results/[jobId] に遷移
      router.push(`/results/${job.job_id}`);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "解析ジョブの作成に失敗しました。"
      );
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8">
      <h1 className="text-2xl font-semibold">DSA 解析を開始</h1>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-gray-200 p-4"
      >
        <div>
          <label className="block text-sm font-medium">UniProt ID</label>
          <input
            type="text"
            value={uniprotId}
            onChange={(e) => setUniprotId(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            required
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">Max structures</label>
            <input
              type="number"
              min={2}
              max={50}
              value={maxStructures}
              onChange={(e) => setMaxStructures(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Seq. ratio</label>
            <input
              type="number"
              step={0.01}
              min={0.5}
              max={1}
              value={seqRatio}
              onChange={(e) => setSeqRatio(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">
              Cis threshold (Å)
            </label>
            <input
              type="number"
              step={0.1}
              value={cisThreshold}
              onChange={(e) => setCisThreshold(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">
              Method (PDB filter)
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="X-ray diffraction">X-ray diffraction</option>
              <option value="dsa">dsa (※テスト用）</option>
            </select>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 whitespace-pre-wrap">{error}</p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 inline-flex items-center justify-center rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {isSubmitting ? "ジョブ作成中..." : "解析を開始"}
        </button>
      </form>
    </main>
  );
}
