"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UniProtLevelResult, ColorMode, PerStructureResult } from "@/types";
import MolstarViewer from "@/components/visualization/MolstarViewer";
import { Dna, Palette } from "lucide-react";

interface StructureComparisonPanelProps {
  result: UniProtLevelResult;
}

export default function StructureComparisonPanel({
  result,
}: StructureComparisonPanelProps) {
  // 使用可能な構造一覧
  const structures = result.per_structure_results || [];
  const hasStructures = structures.length > 0;

  // 選択中の構造（デフォルトは最初の構造）
  const [selectedStructureIndex, setSelectedStructureIndex] = useState(0);
  const selectedStructure: PerStructureResult | null = hasStructures
    ? structures[selectedStructureIndex]
    : null;

  // カラーモード
  const [colorMode, setColorMode] = useState<ColorMode>("flex");

  // ハイライト中の残基
  const [highlightedResidue, setHighlightedResidue] = useState<number | null>(
    null
  );

  // 構造が無い場合
  if (!hasStructures || !selectedStructure) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>3D 構造比較</CardTitle>
          <CardDescription>構造データが利用できません</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-slate-500">
            この解析結果には個別のPDB構造情報が含まれていません。
          </p>
        </CardContent>
      </Card>
    );
  }

  // 統計情報
  const minFlex = Math.min(...result.residues.map((r) => r.flex_score));
  const maxFlex = Math.max(...result.residues.map((r) => r.flex_score));
  const avgFlex =
    result.residues.reduce((sum, r) => sum + r.flex_score, 0) /
    result.residues.length;

  // Top 5 柔軟残基
  const topFlexResidues = [...result.residues]
    .sort((a, b) => b.flex_score - a.flex_score)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* 構造選択 & カラーモード */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Dna className="w-5 h-5" />
            構造選択 & 表示設定
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* 構造選択 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">PDB 構造</label>
              <Select
                value={selectedStructureIndex.toString()}
                onValueChange={(value) =>
                  setSelectedStructureIndex(parseInt(value))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {structures.map((structure, index) => (
                    <SelectItem key={index} value={index.toString()}>
                      {structure.pdb_id} (Chain {structure.chain_id}) -{" "}
                      {structure.num_conformations} conf.
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* カラーモード選択 */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Palette className="w-4 h-4" />
                カラーリングモード
              </label>
              <Select
                value={colorMode}
                onValueChange={(value) => setColorMode(value as ColorMode)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flex">Flex Score</SelectItem>
                  <SelectItem value="dsa">DSA Score</SelectItem>
                  <SelectItem value="bfactor">B-factor</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 選択中の構造情報 */}
          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-slate-500">PDB ID</p>
                <p className="font-semibold">{selectedStructure.pdb_id}</p>
              </div>
              <div>
                <p className="text-slate-500">Chain ID</p>
                <p className="font-semibold">{selectedStructure.chain_id}</p>
              </div>
              <div>
                <p className="text-slate-500">コンフォメーション数</p>
                <p className="font-semibold">
                  {selectedStructure.num_conformations}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* メインの2カラムレイアウト */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* 左カラム: 3D Viewer */}
        <div>
          <MolstarViewer
            pdbId={selectedStructure.pdb_id}
            chainId={selectedStructure.chain_id}
            residues={result.residues}
            colorBy={colorMode}
            onResidueClick={(index) => setHighlightedResidue(index)}
            highlightedResidue={highlightedResidue}
          />
        </div>

        {/* 右カラム: 統計 & テーブル */}
        <div className="space-y-6">
          {/* カラースケール凡例 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">カラースケール</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div
                className="h-8 rounded-lg"
                style={{
                  background:
                    "linear-gradient(to right, #3b82f6, #ffffff, #ef4444)",
                }}
              />
              <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400">
                <span>低 ({minFlex.toFixed(2)})</span>
                <span>平均 ({avgFlex.toFixed(2)})</span>
                <span>高 ({maxFlex.toFixed(2)})</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                {colorMode === "flex" &&
                  "青 = 低柔軟性（安定）、赤 = 高柔軟性（動的）"}
                {colorMode === "dsa" && "青 = 低DSA、赤 = 高DSA"}
                {colorMode === "bfactor" && "青 = 低B-factor、赤 = 高B-factor"}
              </p>
            </CardContent>
          </Card>

          {/* Top 5 柔軟残基 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">最も柔軟な残基 Top 5</CardTitle>
              <CardDescription>
                クリックで3Dビューアでハイライト
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {topFlexResidues.map((residue, rank) => (
                  <button
                    key={residue.index}
                    onClick={() => setHighlightedResidue(residue.index)}
                    className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                      highlightedResidue === residue.index
                        ? "bg-blue-100 dark:bg-blue-900 border-2 border-blue-500"
                        : "bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-lg font-bold text-slate-400">
                        #{rank + 1}
                      </span>
                      <div className="text-left">
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
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 残基統計 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">柔軟性分布</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    低柔軟性
                  </p>
                  <p className="text-2xl font-bold">
                    {
                      result.residues.filter(
                        (r) => r.flex_score < avgFlex * 0.8
                      ).length
                    }
                  </p>
                  <p className="text-xs text-slate-500">残基</p>
                </div>
                <div className="text-center p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    中程度
                  </p>
                  <p className="text-2xl font-bold">
                    {
                      result.residues.filter(
                        (r) =>
                          r.flex_score >= avgFlex * 0.8 &&
                          r.flex_score <= avgFlex * 1.2
                      ).length
                    }
                  </p>
                  <p className="text-xs text-slate-500">残基</p>
                </div>
                <div className="text-center p-3 bg-red-50 dark:bg-red-950 rounded-lg">
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    高柔軟性
                  </p>
                  <p className="text-2xl font-bold">
                    {
                      result.residues.filter(
                        (r) => r.flex_score > avgFlex * 1.2
                      ).length
                    }
                  </p>
                  <p className="text-xs text-slate-500">残基</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 残基テーブル（クリック可能） */}
      <Card>
        <CardHeader>
          <CardTitle>全残基データ（クリックで3Dハイライト）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0">
                <tr>
                  <th className="p-2 text-left">番号</th>
                  <th className="p-2 text-left">残基</th>
                  <th className="p-2 text-right">Flex Score</th>
                  <th className="p-2 text-right">DSA Score</th>
                  <th className="p-2 text-center">アクション</th>
                </tr>
              </thead>
              <tbody>
                {result.residues.map((residue) => (
                  <tr
                    key={residue.index}
                    className={`border-b dark:border-slate-700 cursor-pointer transition-colors ${
                      highlightedResidue === residue.index
                        ? "bg-blue-100 dark:bg-blue-900"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                    onClick={() => setHighlightedResidue(residue.index)}
                  >
                    <td className="p-2">{residue.residue_number}</td>
                    <td className="p-2">
                      <Badge variant="outline">{residue.residue_name}</Badge>
                    </td>
                    <td className="p-2 text-right font-mono">
                      {residue.flex_score.toFixed(4)}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {residue.dsa_score.toFixed(4)}
                    </td>
                    <td className="p-2 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setHighlightedResidue(residue.index);
                        }}
                        className="text-xs text-blue-600 hover:text-blue-800"
                      >
                        ハイライト
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
