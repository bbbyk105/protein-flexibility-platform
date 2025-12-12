/* eslint-disable @next/next/no-img-element */
"use client";

import React from "react";

type DistanceScorePlotProps = {
  jobId: string;
};

export const DistanceScorePlot: React.FC<DistanceScorePlotProps> = ({
  jobId,
}) => {
  // Go API が返す PNG への URL
  const src = `http://localhost:8080/api/dsa/jobs/${jobId}/distance-score`;

  return (
    <div className="mt-8 flex flex-col items-center gap-2">
      <h3 className="text-sm font-medium text-slate-700">
        Distance–Score Plot
      </h3>
      <img
        src={src}
        alt="Distance vs Score"
        style={{
          maxWidth: "600px",
          width: "100%",
          borderRadius: 8,
          border: "1px solid #e2e8f0",
          background: "#ffffff",
        }}
      />
    </div>
  );
};
