'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { JobStatus } from '@/types';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

interface AnalysisProgressProps {
  jobStatus: JobStatus;
  jobId: string;
}

export default function AnalysisProgress({ jobStatus, jobId }: AnalysisProgressProps) {
  const getStatusIcon = () => {
    switch (jobStatus.status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Loader2 className="w-5 h-5 animate-spin text-blue-600" />;
    }
  };

  const getStatusBadge = () => {
    switch (jobStatus.status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-600">完了</Badge>;
      case 'failed':
        return <Badge variant="destructive">失敗</Badge>;
      case 'processing':
        return <Badge variant="default" className="bg-blue-600">処理中</Badge>;
      default:
        return <Badge variant="secondary">待機中</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            {getStatusIcon()}
            解析状況
          </span>
          {getStatusBadge()}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>進捗</span>
            <span className="font-medium">{jobStatus.progress || 0}%</span>
          </div>
          <Progress value={jobStatus.progress || 0} />
        </div>

        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Job ID:</span>
            <span className="font-mono text-xs">{jobId}</span>
          </div>
          {jobStatus.message && (
            <div className="flex justify-between">
              <span className="text-slate-500">メッセージ:</span>
              <span className="text-xs">{jobStatus.message}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
