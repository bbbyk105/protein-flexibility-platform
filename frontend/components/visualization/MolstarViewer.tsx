'use client';

import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, RotateCcw, Maximize2 } from 'lucide-react';
import { ResidueData, ColorMode } from '@/types';

interface MolstarViewerProps {
  pdbId: string;
  chainId: string;
  residues: ResidueData[];
  colorBy: ColorMode;
  onResidueClick?: (residueIndex: number) => void;
  highlightedResidue?: number | null;
}

export default function MolstarViewer({
  pdbId,
  chainId,
  residues,
  colorBy,
}: MolstarViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<unknown>(null);
  const isInitializedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 既に初期化済みの場合はスキップ（Strict Mode 対策）
    if (isInitializedRef.current || !containerRef.current) return;

    const initMolstar = async () => {
      try {
        setIsLoading(true);
        setError(null);
        isInitializedRef.current = true;

        // 動的インポート
        const [{ createPluginUI }, { DefaultPluginUISpec }, { renderReact18 }] = await Promise.all([
          import('molstar/lib/mol-plugin-ui'),
          import('molstar/lib/mol-plugin-ui/spec'),
          import('molstar/lib/mol-plugin-ui/react18'),
        ]);
        
        // プラグイン初期化
        const plugin = await createPluginUI({
          target: containerRef.current as HTMLElement,
          render: renderReact18,
          spec: {
            ...DefaultPluginUISpec(),
            layout: {
              initial: {
                isExpanded: false,
                showControls: false,
              },
            },
          },
        });

        pluginRef.current = plugin;

        // PDB構造をロード
        const pdbUrl = `https://files.rcsb.org/download/${pdbId}.pdb`;
        const data = await plugin.builders.data.download(
          { url: pdbUrl, isBinary: false },
          { state: { isGhost: false } }
        );

        const trajectory = await plugin.builders.structure.parseTrajectory(data, 'pdb');
        const model = await plugin.builders.structure.createModel(trajectory);
        const structure = await plugin.builders.structure.createStructure(model);

        // 基本的なカートゥーン表現を追加
        await plugin.builders.structure.representation.addRepresentation(structure, {
          type: 'cartoon',
        });

        // ビューをフィット
        plugin.canvas3d?.requestCameraReset();

        setIsLoading(false);
      } catch (err) {
        console.error('Mol* initialization error:', err);
        setError('3D構造の読み込みに失敗しました');
        setIsLoading(false);
        isInitializedRef.current = false;
      }
    };

    initMolstar();

    return () => {
      if (pluginRef.current && typeof (pluginRef.current as { dispose?: () => void }).dispose === 'function') {
        (pluginRef.current as { dispose: () => void }).dispose();
        pluginRef.current = null;
        isInitializedRef.current = false;
      }
    };
  }, [pdbId]);

  const handleReset = () => {
    const plugin = pluginRef.current as { canvas3d?: { requestCameraReset: () => void } };
    if (plugin?.canvas3d) {
      plugin.canvas3d.requestCameraReset();
    }
  };

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>3D 構造表示 (Mol* Viewer)</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleReset} disabled={isLoading}>
              <RotateCcw className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="outline" disabled={isLoading}>
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        </CardTitle>
        <CardDescription>
          PDB: {pdbId} | Chain: {chainId} | カラーリング: {colorBy}
        </CardDescription>
      </CardHeader>
      <CardContent className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 z-10 rounded-lg">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
              <p className="text-sm text-slate-600 dark:text-slate-400">構造を読み込み中...</p>
              <p className="text-xs text-slate-500 mt-1">{pdbId}.pdb</p>
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 z-10 rounded-lg">
            <div className="text-center">
              <p className="text-red-600 font-semibold mb-2">{error}</p>
              <p className="text-xs text-slate-500">
                PDB ID: {pdbId} が見つからない可能性があります
              </p>
            </div>
          </div>
        )}
        <div 
          ref={containerRef} 
          className="w-full h-[600px] border rounded-lg overflow-hidden bg-slate-50 dark:bg-slate-900"
          style={{ position: 'relative' }}
        />
      </CardContent>
    </Card>
  );
}
