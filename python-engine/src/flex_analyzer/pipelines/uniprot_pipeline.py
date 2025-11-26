from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.flex_analyzer.core import compute_uniprot_level_flex
from src.flex_analyzer.data_sources import build_structure_set_from_uniprot
from src.flex_analyzer.models import StructureSet, UniProtLevelResult


def run_uniprot_pipeline(
    uniprot_id: str,
    max_structures: int = 20,
    output_dir: Path = Path("output/uniprot_results"),
) -> UniProtLevelResult:
    """
    UniProt ID を入力として:
      - data_sources.uniprot で StructureSet を構築し
      - core.compute_uniprot_level_flex で解析し
      - JSON ファイルとして保存する

    という一連の流れを実行するパイプライン。
    """

    # 1) 構造セットの構築
    sset: StructureSet = build_structure_set_from_uniprot(
        uniprot_id=uniprot_id,
        max_structures=max_structures,
    )

    # 2) Flex 解析の実行
    result: UniProtLevelResult = compute_uniprot_level_flex(
        structure_coords_list=[sset.coords],
        residues=sset.residues,
        pdb_ids=sset.pdb_ids,
        uniprot_id=sset.uniprot_id_resolved,
        chain_ids=sset.chain_ids,
        flex_ratio_threshold=0.5,
    )

    # 3) 結果の表示（ざっくり）
    print("\n============================================================")
    print(f"🧪 UniProtレベル2段階解析 - {sset.uniprot_id_input}")
    print("============================================================")
    print(f"入力 UniProt ID: {sset.uniprot_id_input}")
    print(f"解決 UniProt ID: {sset.uniprot_id_resolved}")
    print(f"構造数: {result.num_structures}")
    print(f"総コンフォメーション数: {result.num_conformations_total}")
    print(f"残基数: {result.num_residues}")

    print("\nグローバルFlex Stats:")
    print(f"  Min:    {result.global_flex_stats.min:.4f}")
    print(f"  Max:    {result.global_flex_stats.max:.4f}")
    print(f"  Mean:   {result.global_flex_stats.mean:.4f}")
    print(f"  Median: {result.global_flex_stats.median:.4f}")

    print("\n各構造の簡易情報:")
    for i, per_struct in enumerate(result.per_structure_results):
        print(f"  [{i+1}] {per_struct.pdb_id} (chain {per_struct.chain_id})")
        print(
            f"      コンフォメーション数: {per_struct.num_conformations}\n"
            f"      Flex範囲: {per_struct.flex_stats.min:.4f} - "
            f"{per_struct.flex_stats.max:.4f}"
        )

    # 4) JSON に保存（入力された UniProt ID ベースのファイル名）
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{sset.uniprot_id_input}_uniprot_result.json"
    out_path.write_text(
        json.dumps(result.model_dump(), indent=2),
        encoding="utf-8",
    )
    print("\n結果JSONを書き出しました:")
    print(f"  {out_path}")

    print("\n🎉 UniProtレベル解析 完了！")
    print("============================================================")

    return result
