// frontend/app/analyze/page.tsx
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createDSAJob } from "@/lib/api";
import type { AnalysisParams } from "@/types/dsa";

export default function AnalyzePage() {
  const router = useRouter();

  const [uniprotIds, setUniprotIds] = useState("C6H0Y9");
  const [method, setMethod] = useState<string>("X-ray");
  const [seqRatio, setSeqRatio] = useState<number>(0.2);
  const [negativePdbid, setNegativePdbid] = useState<string>("");
  const [cisThreshold, setCisThreshold] = useState<number>(3.3);
  const [exportCsv, setExportCsv] = useState<boolean>(true);
  const [heatmap, setHeatmap] = useState<boolean>(true);
  const [procCis, setProcCis] = useState<boolean>(true);
  const [overwrite, setOverwrite] = useState<boolean>(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // デバッグ: フォームの値をログ出力
      console.log("[DEBUG] handleSubmit - Form values:", {
        uniprotIds,
        method,
        seqRatio,
        negativePdbid,
        cisThreshold,
        exportCsv,
        heatmap,
        procCis,
        overwrite,
      });

      const params: AnalysisParams = {
        uniprot_ids: uniprotIds.trim(),
      };

      // オプショナルなパラメータを追加（値が存在する場合のみ）
      if (method) {
        params.method = method;
      }
      if (seqRatio > 0) {
        params.seq_ratio = seqRatio;
      }
      if (negativePdbid.trim()) {
        params.negative_pdbid = negativePdbid.trim();
      }
      if (cisThreshold > 0) {
        params.cis_threshold = cisThreshold;
      }
      params.export = exportCsv;
      params.heatmap = heatmap;
      params.proc_cis = procCis;
      params.overwrite = overwrite;

      // デバッグ: 最終的なパラメータをログ出力
      console.log("[DEBUG] handleSubmit - Final params object:", params);
      console.log(
        "[DEBUG] handleSubmit - Final params JSON:",
        JSON.stringify(params, null, 2)
      );

      const jobsResponse = await createDSAJob(params);

      // 複数のジョブが作成された場合は比較ページに遷移、1つの場合は通常の結果ページに遷移
      if (jobsResponse.jobs.length === 1) {
        router.push(`/results/${jobsResponse.jobs[0].job_id}`);
      } else {
        // 複数のジョブIDをクエリパラメータで渡す
        const jobIds = jobsResponse.jobs.map((j) => j.job_id).join(",");
        router.push(`/compare?jobIds=${jobIds}`);
      }
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
      <h1 className="text-2xl font-semibold">Notebook DSA 解析を開始</h1>
      <p className="text-sm text-gray-600">
        Colab Notebook DSA_Cis_250317.ipynb の機能を完全再現した解析を実行します
      </p>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-gray-200 p-4"
      >
        <div>
          <label className="block text-sm font-medium">
            UniProt ID(s){" "}
            <span className="text-gray-500">
              (複数の場合はカンマまたはスペース区切り)
            </span>
          </label>
          <input
            type="text"
            value={uniprotIds}
            onChange={(e) => setUniprotIds(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder="例: C6H0Y9 または C6H0Y9 P02699"
            required
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">
              Method (PDB filter)
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="X-ray">X-ray</option>
              <option value="NMR">NMR</option>
              <option value="EM">EM</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium">Sequence ratio</label>
            <input
              type="number"
              step={0.01}
              min={0.01}
              max={1}
              value={seqRatio}
              onChange={(e) => setSeqRatio(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              配列アライメント閾値 (0.0-1.0)
            </p>
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
            <p className="mt-1 text-xs text-gray-500">cis判定の距離閾値</p>
          </div>

          <div>
            <label className="block text-sm font-medium">
              Negative PDB ID{" "}
              <span className="text-gray-500">(除外するPDB ID)</span>
            </label>
            <input
              type="text"
              value={negativePdbid}
              onChange={(e) => setNegativePdbid(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="例: 1AAA 1BBB または 1AAA,1BBB"
            />
            <p className="mt-1 text-xs text-gray-500">
              スペースまたはカンマ区切り
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">オプション</p>
          <div className="grid gap-2 md:grid-cols-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportCsv}
                onChange={(e) => setExportCsv(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">CSV出力</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={heatmap}
                onChange={(e) => setHeatmap(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">ヒートマップ生成</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={procCis}
                onChange={(e) => setProcCis(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Cis解析</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(e) => setOverwrite(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm">上書き</span>
            </label>
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
