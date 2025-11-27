"use client";

import { Suspense } from "react";
import UniProtAnalysis from "@/components/analysis/UniProtAnalysis";

function AnalyzeContent() {
  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2">タンパク質揺らぎ解析</h1>
          <p className="text-slate-600 dark:text-slate-400 mb-8">
            UniProt ID から柔軟性スコアを計算します
          </p>

          <UniProtAnalysis />
        </div>
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AnalyzeContent />
    </Suspense>
  );
}
