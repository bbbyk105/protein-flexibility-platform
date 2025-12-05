"use client";

import React from "react";

interface HeatmapProps {
  // Python からは (number | null)[][] が返ってくる想定
  values: (number | null)[][];
  title?: string;
}

// 元ノートの説明に合わせた表示レンジ
const DISPLAY_MIN = 20;
const DISPLAY_MAX = 130;

export default function Heatmap({ values, title }: HeatmapProps) {
  // データが無い場合
  if (!values || values.length === 0) {
    return (
      <div className="border rounded-lg bg-white p-4 text-sm text-slate-500">
        ヒートマップ用のデータがありません。
      </div>
    );
  }

  const size = values.length;

  // 数値だけを抜き出しておく（統計表示に使いたい時用）
  const numericValues = values
    .flat()
    .filter((v): v is number => v !== null && !Number.isNaN(v));

  if (numericValues.length === 0) {
    return (
      <div className="border rounded-lg bg-white p-4 text-sm text-slate-500">
        有効なスコアが存在しないため、ヒートマップを表示できません。
      </div>
    );
  }

  const clampScore = (v: number) =>
    Math.max(DISPLAY_MIN, Math.min(DISPLAY_MAX, v));

  const toRatio = (v: number) =>
    (clampScore(v) - DISPLAY_MIN) / (DISPLAY_MAX - DISPLAY_MIN || 1);

  return (
    <div className="flex flex-col gap-3">
      {title && <h3 className="text-sm font-medium text-slate-800">{title}</h3>}

      {/* 本体（カード幅いっぱいの正方形） */}
      <div className="w-full max-w-[640px] mx-auto">
        <div className="relative aspect-square border rounded-lg overflow-hidden bg-white">
          <div
            className="grid w-full h-full"
            style={{
              gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))`,
              gridTemplateRows: `repeat(${size}, minmax(0, 1fr))`,
            }}
          >
            {values.map((row, i) =>
              row.map((v, j) => {
                // データ無しの部分は白
                if (v === null || Number.isNaN(v)) {
                  return <div key={`${i}-${j}`} className="bg-white" />;
                }

                const ratio = toRatio(v);
                // ざっくり「青→赤」のグラデーション（元は rainbow_r だけど簡略化）
                const hue = 240 - 240 * ratio; // 240=青, 0=赤
                const color = `hsl(${hue}deg, 80%, 60%)`;

                return (
                  <div key={`${i}-${j}`} style={{ backgroundColor: color }} />
                );
              })
            )}
          </div>
        </div>

        {/* 簡易カラーバー */}
        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
          <span>{DISPLAY_MIN}</span>
          <span>Score</span>
          <span>{DISPLAY_MAX}</span>
        </div>
      </div>
    </div>
  );
}
