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
  highlightedResidue,
}: MolstarViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<any>(null);
  const structureRef = useRef<any>(null);
  const isInitializedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 初期化
  useEffect(() => {
    if (isInitializedRef.current || !containerRef.current) return;

    const initMolstar = async () => {
      try {
        setIsLoading(true);
        setError(null);
        isInitializedRef.current = true;

        const [{ createPluginUI }, { DefaultPluginUISpec }, { renderReact18 }] = await Promise.all([
          import('molstar/lib/mol-plugin-ui'),
          import('molstar/lib/mol-plugin-ui/spec'),
          import('molstar/lib/mol-plugin-ui/react18'),
        ]);
        
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

        const pdbUrl = `https://files.rcsb.org/download/${pdbId}.pdb`;
        const data = await plugin.builders.data.download(
          { url: pdbUrl, isBinary: false },
          { state: { isGhost: false } }
        );

        const trajectory = await plugin.builders.structure.parseTrajectory(data, 'pdb');
        const model = await plugin.builders.structure.createModel(trajectory);
        const structure = await plugin.builders.structure.createStructure(model);
        
        structureRef.current = structure;

        await plugin.builders.structure.representation.addRepresentation(structure, {
          type: 'cartoon',
        });

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
      if (pluginRef.current?.dispose) {
        pluginRef.current.dispose();
        pluginRef.current = null;
        structureRef.current = null;
        isInitializedRef.current = false;
      }
    };
  }, [pdbId]);

  // ハイライト機能
  useEffect(() => {
    if (!pluginRef.current || !structureRef.current || highlightedResidue === null) return;

    const highlightResidue = async () => {
      try {
        const plugin = pluginRef.current;
        const residue = residues.find(r => r.index === highlightedResidue);
        if (!residue) return;

        // Script を使って残基を選択
        const { Script } = await import('molstar/lib/mol-script/script');
        const { MolScriptBuilder: MS } = await import('molstar/lib/mol-script/language/builder');
        const { StructureSelection } = await import('molstar/lib/mol-model/structure');

        // 残基番号で選択クエリを作成
        const data = plugin.managers.structure.hierarchy.current.structures[0]?.cell.obj?.data;
        if (!data) return;

        const selection = Script.getStructureSelection(
          Q => Q.struct.generator.atomGroups({
            'residue-test': Q.core.rel.eq([
              Q.struct.atomProperty.macromolecular.label_seq_id(),
              residue.residue_number
            ]),
            'chain-test': Q.core.rel.eq([
              Q.struct.atomProperty.macromolecular.label_asym_id(),
              chainId
            ])
          }),
          data
        );

        const loci = StructureSelection.toLociWithSourceUnits(selection);

        // ハイライト表示
        plugin.managers.interactivity.lociHighlights.highlightOnly({ loci });

        // カメラをフォーカス
        plugin.managers.camera.focusLoci(loci);

      } catch (err) {
        console.error('Highlight error:', err);
      }
    };

    highlightResidue();
  }, [highlightedResidue, residues, chainId]);

  const handleReset = () => {
    if (pluginRef.current?.canvas3d) {
      pluginRef.current.canvas3d.requestCameraReset();
      // ハイライトをクリア
      pluginRef.current.managers.interactivity.lociHighlights.clearHighlights();
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
        {highlightedResidue !== null && (
          <div className="absolute top-4 left-4 z-10 bg-blue-600 text-white px-3 py-1 rounded-lg text-sm font-semibold shadow-lg">
            残基 {residues.find(r => r.index === highlightedResidue)?.residue_number} をハイライト中
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
