// app/compare/page.tsx

import ComparePageClient from "./ComparePageClient";

interface ComparePageProps {
  searchParams: Promise<{ jobIds?: string }>;
}

export default async function ComparePage({
  searchParams,
}: ComparePageProps) {
  const params = await searchParams;
  const jobIds = params.jobIds?.split(",").filter(Boolean) || [];

  return <ComparePageClient jobIds={jobIds} />;
}

