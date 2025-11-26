'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload } from 'lucide-react';

export default function PDBAnalysis() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="w-5 h-5" />
          PDB ファイルアップロード
        </CardTitle>
        <CardDescription>
          PDB ファイルを直接アップロードして解析（実装予定）
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-slate-500">Coming soon...</p>
      </CardContent>
    </Card>
  );
}
