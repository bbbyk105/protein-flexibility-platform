'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ResidueData } from '@/types';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

interface FlexScoreChartProps {
  residues: ResidueData[];
}

export default function FlexScoreChart({ residues }: FlexScoreChartProps) {
  // グラフ用データ整形
  const chartData = residues.map((residue) => ({
    position: residue.residue_number,
    residueName: residue.residue_name,
    flexScore: parseFloat(residue.flex_score.toFixed(4)),
    dsaScore: parseFloat(residue.dsa_score.toFixed(2)),
  }));

  // 平均値計算
  const avgFlex = residues.reduce((sum, r) => sum + r.flex_score, 0) / residues.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          残基ごとの Flex Score プロファイル
        </CardTitle>
        <CardDescription>
          各残基の柔軟性スコア（青線）と平均値（赤破線）
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
            <XAxis 
              dataKey="position" 
              label={{ value: '残基番号', position: 'insideBottom', offset: -5 }}
              className="text-slate-600 dark:text-slate-400"
            />
            <YAxis 
              label={{ value: 'Flex Score', angle: -90, position: 'insideLeft' }}
              className="text-slate-600 dark:text-slate-400"
            />
            <Tooltip 
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white dark:bg-slate-800 p-3 border rounded-lg shadow-lg">
                      <p className="font-semibold">{data.residueName} {data.position}</p>
                      <p className="text-sm text-blue-600">Flex Score: {data.flexScore}</p>
                      <p className="text-sm text-green-600">DSA Score: {data.dsaScore}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="flexScore" 
              stroke="#3b82f6" 
              strokeWidth={2}
              dot={{ r: 2 }}
              name="Flex Score"
            />
            <Line 
              type="monotone" 
              dataKey={() => avgFlex} 
              stroke="#ef4444" 
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name={`平均値 (${avgFlex.toFixed(3)})`}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
