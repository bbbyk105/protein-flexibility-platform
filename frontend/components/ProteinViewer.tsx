'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink } from 'lucide-react';
import { ResidueData } from '@/types';
import Image from 'next/image';

interface ProteinViewerProps {
  pdbId?: string;
  uniprotId?: string;
  residues: ResidueData[];
}

export default function ProteinViewer({ pdbId, uniprotId, residues }: ProteinViewerProps) {
  if (!pdbId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>3D 構造表示</CardTitle>
          <CardDescription>PDB IDが必要です</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const imageUrl = `https://cdn.rcsb.org/images/structures/${pdbId.toLowerCase()}_assembly-1.jpeg`;
  const pdbUrl = `https://www.rcsb.org/structure/${pdbId}`;

  const minFlex = Math.min(...residues.map(r => r.flex_score));
  const maxFlex = Math.max(...residues.map(r => r.flex_score));
  const avgFlex = residues.reduce((sum, r) => sum + r.flex_score, 0) / residues.length;

  const topFlexResidues = [...residues]
    .sort((a, b) => b.flex_score - a.flex_score)
    .slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>3D 構造 & 柔軟性解析</span>
          <Button size="sm" variant="outline" asChild>
            <a href={pdbUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4 mr-1" />
              RCSB PDBで開く
            </a>
          </Button>
        </CardTitle>
        <CardDescription>
          PDB ID: {pdbId} | UniProt: {uniprotId}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="relative w-full h-96 bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden">
          <Image
            src={imageUrl}
            alt={`${pdbId} structure`}
            fill
            className="object-contain"
          />
        </div>

        <div>
          <h3 className="font-semibold mb-3">Flex Score カラースケール</h3>
          <div className="space-y-2">
            <div className="h-8 rounded-lg" style={{
              background: 'linear-gradient(to right, #3b82f6, #22c55e, #eab308, #ef4444)'
            }} />
            <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400">
              <span>低柔軟性 ({minFlex.toFixed(2)})</span>
              <span>平均 ({avgFlex.toFixed(2)})</span>
              <span>高柔軟性 ({maxFlex.toFixed(2)})</span>
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-semibold mb-3">最も柔軟な残基 Top 5</h3>
          <div className="space-y-2">
            {topFlexResidues.map((residue, index) => (
              <div
                key={residue.index}
                className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-lg font-bold text-slate-400">
                    #{index + 1}
                  </span>
                  <div>
                    <p className="font-semibold">
                      {residue.residue_name} {residue.residue_number}
                    </p>
                    <p className="text-xs text-slate-500">
                      Index: {residue.index}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-red-600">
                    {residue.flex_score.toFixed(4)}
                  </p>
                  <p className="text-xs text-slate-500">
                    DSA: {residue.dsa_score.toFixed(2)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="font-semibold mb-3">柔軟性の分布</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400">低柔軟性</p>
              <p className="text-2xl font-bold">
                {residues.filter(r => r.flex_score < avgFlex * 0.8).length}
              </p>
              <p className="text-xs text-slate-500">残基</p>
            </div>
            <div className="text-center p-4 bg-green-50 dark:bg-green-950 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400">中程度</p>
              <p className="text-2xl font-bold">
                {residues.filter(r => r.flex_score >= avgFlex * 0.8 && r.flex_score <= avgFlex * 1.2).length}
              </p>
              <p className="text-xs text-slate-500">残基</p>
            </div>
            <div className="text-center p-4 bg-red-50 dark:bg-red-950 rounded-lg">
              <p className="text-sm text-slate-600 dark:text-slate-400">高柔軟性</p>
              <p className="text-2xl font-bold">
                {residues.filter(r => r.flex_score > avgFlex * 1.2).length}
              </p>
              <p className="text-xs text-slate-500">残基</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
