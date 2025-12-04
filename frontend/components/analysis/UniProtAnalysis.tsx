'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Dna, AlertCircle } from 'lucide-react';
import { analyzeUniProt, getJobStatus, getUniProtResult } from '@/lib/api';
import { JobStatus, UniProtLevelResult } from '@/types';
import AnalysisProgress from './AnalysisProgress';
import ResultDisplay from './ResultDisplay';

export default function UniProtAnalysis() {
  const [uniprotId, setUniprotId] = useState('P62988');
  const [maxStructures, setMaxStructures] = useState(20);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<UniProtLevelResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // 推定進捗用
  const [displayProgress, setDisplayProgress] = useState(0);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  const handleAnalyze = async () => {
    if (!uniprotId.trim()) {
      setError('UniProt ID を入力してください');
      return;
    }

    setError(null);
    setIsAnalyzing(true);
    setJobStatus(null);
    setResult(null);
    setDisplayProgress(0);
    startTimeRef.current = Date.now();

    try {
      // 解析開始
      const response = await analyzeUniProt(uniprotId, maxStructures);
      setJobId(response.job_id);

      // 推定進捗バーのアニメーション開始
      progressIntervalRef.current = setInterval(() => {
        setDisplayProgress((prev) => {
          const elapsed = (Date.now() - startTimeRef.current) / 1000; // 経過秒数
          
          // 時間経過に基づいて進捗を計算
          // 0-30秒: 0-30%
          // 30-60秒: 30-60%
          // 60-90秒: 60-80%
          // 90秒以降: 80-95%（完了まで）
          let estimated = 0;
          if (elapsed < 30) {
            estimated = elapsed; // 0-30%
          } else if (elapsed < 60) {
            estimated = 30 + (elapsed - 30); // 30-60%
          } else if (elapsed < 90) {
            estimated = 60 + (elapsed - 60) * 0.67; // 60-80%
          } else {
            estimated = 80 + Math.min((elapsed - 90) * 0.15, 15); // 80-95%
          }
          
          return Math.min(Math.floor(estimated), 95);
        });
      }, 1000); // 1秒ごとに更新

      // ポーリング開始
      pollIntervalRef.current = setInterval(async () => {
        try {
          const status = await getJobStatus(response.job_id);
          setJobStatus(status);

          if (status.status === 'completed') {
            // 完了時は100%に設定
            setDisplayProgress(100);
            
            // インターバルをクリア
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);

            // 結果取得
            const resultData = await getUniProtResult(response.job_id);
            setResult(resultData);
            setIsAnalyzing(false);
          } else if (status.status === 'failed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
            setError(status.message || '解析に失敗しました');
            setIsAnalyzing(false);
          }
        } catch (err) {
          console.error('Status polling error:', err);
        }
      }, 2000); // 2秒ごとにポーリング

      // 5分でタイムアウト
      setTimeout(() => {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
        if (isAnalyzing) {
          setError('解析がタイムアウトしました');
          setIsAnalyzing(false);
        }
      }, 300000);
    } catch (err: any) {
      setError(err.response?.data?.message || '解析の開始に失敗しました');
      setIsAnalyzing(false);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    }
  };

  // クリーンアップ
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, []);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Dna className="w-5 h-5" />
            UniProt 自動解析
          </CardTitle>
          <CardDescription>
            UniProt ID を入力すると、自動的に PDB 構造を取得して解析します
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="uniprot-id">UniProt ID</Label>
            <Input
              id="uniprot-id"
              placeholder="例: P62988 (ユビキチン)"
              value={uniprotId}
              onChange={(e) => setUniprotId(e.target.value)}
              disabled={isAnalyzing}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="max-structures">最大構造数</Label>
            <Input
              id="max-structures"
              type="number"
              min={1}
              max={100}
              value={maxStructures}
              onChange={(e) => setMaxStructures(parseInt(e.target.value) || 20)}
              disabled={isAnalyzing}
            />
            <p className="text-sm text-slate-500">
              解析する PDB 構造の最大数（1〜100）
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="w-full"
            size="lg"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                解析中...
              </>
            ) : (
              <>
                <Dna className="mr-2 h-4 w-4" />
                解析開始
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {jobStatus && (
        <AnalysisProgress 
          jobStatus={{
            ...jobStatus,
            progress: displayProgress // 時間ベースの推定進捗
          }} 
          jobId={jobId || ''} 
        />
      )}

      {result && (
        <ResultDisplay result={result} />
      )}
    </div>
  );
}
