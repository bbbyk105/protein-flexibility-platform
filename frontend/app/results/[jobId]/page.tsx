// app/results/[jobId]/page.tsx

import ResultPageClient from "./ResultPageClient";

interface ResultPageProps {
  // Next.js 16 では params が Promise として渡ってくる
  params: Promise<{ jobId: string }>;
}

export default async function ResultPage({ params }: ResultPageProps) {
  // ここでだけ await して OK（サーバー側）
  const { jobId } = await params;

  return <ResultPageClient jobId={jobId} />;
}
