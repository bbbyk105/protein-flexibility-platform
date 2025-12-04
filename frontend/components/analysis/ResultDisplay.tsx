"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UniProtLevelResult } from "@/types";
import { BarChart3, Table, Box } from "lucide-react";
import FlexScoreChart from "@/components/visualization/FlexScoreChart";
import StructureComparisonPanel from "./StructureComparisonPanel";
import { Badge } from "@/components/ui/badge";

interface ResultDisplayProps {
  result: UniProtLevelResult;
}

export default function ResultDisplay({ result }: ResultDisplayProps) {
  return (
    <div className="space-y-6">
      {/* 基本情報カード */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            解析結果サマリー
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-slate-500">UniProt ID</p>
              <p className="text-lg font-semibold">{result.uniprot_id}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500">構造数</p>
              <p className="text-lg font-semibold">{result.num_structures}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500">コンフォメーション</p>
              <p className="text-lg font-semibold">
                {result.num_conformations_total}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500">残基数</p>
              <p className="text-lg font-semibold">{result.num_residues}</p>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-3">グローバル Flex 統計</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  最小値
                </p>
                <p className="text-lg font-semibold">
                  {result.global_flex_stats.min.toFixed(4)}
                </p>
              </div>
              <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  最大値
                </p>
                <p className="text-lg font-semibold">
                  {result.global_flex_stats.max.toFixed(4)}
                </p>
              </div>
              <div className="p-3 bg-purple-50 dark:bg-purple-950 rounded-lg">
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  平均値
                </p>
                <p className="text-lg font-semibold">
                  {result.global_flex_stats.mean.toFixed(4)}
                </p>
              </div>
              <div className="p-3 bg-orange-50 dark:bg-orange-950 rounded-lg">
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  中央値
                </p>
                <p className="text-lg font-semibold">
                  {result.global_flex_stats.median.toFixed(4)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* タブで切り替え */}
      <Tabs defaultValue="chart" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="chart">
            <BarChart3 className="w-4 h-4 mr-1" />
            グラフ
          </TabsTrigger>
          <TabsTrigger value="3d-comparison">
            <Box className="w-4 h-4 mr-1" />
            3D構造 & 比較
          </TabsTrigger>
          <TabsTrigger value="table">
            <Table className="w-4 h-4 mr-1" />
            データテーブル
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chart" className="mt-6">
          <FlexScoreChart residues={result.residues} />
        </TabsContent>

        <TabsContent value="3d-comparison" className="mt-6">
          <StructureComparisonPanel result={result} />
        </TabsContent>

        <TabsContent value="table" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>
                残基データ（全 {result.residues.length} 件）
              </CardTitle>
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
                    </tr>
                  </thead>
                  <tbody>
                    {result.residues.map((residue) => (
                      <tr
                        key={residue.index}
                        className="border-b dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
                      >
                        <td className="p-2">{residue.residue_number}</td>
                        <td className="p-2">
                          <Badge variant="outline">
                            {residue.residue_name}
                          </Badge>
                        </td>
                        <td className="p-2 text-right font-mono">
                          {residue.flex_score.toFixed(4)}
                        </td>
                        <td className="p-2 text-right font-mono">
                          {residue.dsa_score.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
