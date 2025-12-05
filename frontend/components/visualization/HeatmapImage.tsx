"use client";

import Image from "next/image";

interface HeatmapImageProps {
  jobId: string;
  className?: string;
}

export function HeatmapImage({ jobId, className }: HeatmapImageProps) {
  const src = `http://localhost:8080/api/dsa/jobs/${jobId}/heatmap`;

  return (
    <div className={className ?? "flex flex-col items-center gap-3"}>
      <h3 className="text-sm font-medium text-slate-800">DSA Heatmap (PNG)</h3>
      <div className="relative w-[600px] h-[600px] max-w-full">
        <Image
          src={src}
          alt="DSA Heatmap"
          fill
          className="rounded-lg border object-contain bg-white"
          unoptimized
        />
      </div>
    </div>
  );
}
