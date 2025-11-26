'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import UniProtAnalysis from '@/components/analysis/UniProtAnalysis';
import PDBAnalysis from '@/components/analysis/PDBAnalysis';

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get('mode') || 'uniprot';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2">タンパク質揺らぎ解析</h1>
          <p className="text-slate-600 dark:text-slate-400 mb-8">
            UniProt ID または PDB ファイルから柔軟性スコアを計算します
          </p>

          <Tabs defaultValue={mode} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="uniprot">UniProt 解析</TabsTrigger>
              <TabsTrigger value="pdb">PDB アップロード</TabsTrigger>
            </TabsList>

            <TabsContent value="uniprot" className="mt-6">
              <UniProtAnalysis />
            </TabsContent>

            <TabsContent value="pdb" className="mt-6">
              <PDBAnalysis />
            </TabsContent>
          </Tabs>
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
