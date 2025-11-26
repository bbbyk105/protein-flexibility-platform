from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Tuple

from src.flex_analyzer.core import (
    compute_uniprot_level_flex,
    analyze_flex_and_dsa_from_coords,
)
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
      - core.compute_uniprot_level_flex で「既存の揺らぎ解析」を実行し
      - 追加で DSA/UMF 解析 (analyze_flex_and_dsa_from_coords) を実行し
      - 両方をまとめて JSON に保存する

    という一連の流れを実行するパイプライン。
    """

    # 1) 構造セットの構築
    sset: StructureSet = build_structure_set_from_uniprot(
        uniprot_id=uniprot_id,
        max_structures=max_structures,
    )

    # 2) 既存の UniProt レベル Flex 解析
    result: UniProtLevelResult = compute_uniprot_level_flex(
        structure_coords_list=[sset.coords],
        residues=sset.residues,
        pdb_ids=sset.pdb_ids,
        uniprot_id=sset.uniprot_id_resolved,
        chain_ids=sset.chain_ids,
        flex_ratio_threshold=0.5,
    )

    # 3) DSA / UMF / cis を追加で計算（全構造まとめて）
    #    sset.coords: shape = (M_total, N, 3)
    #    residue_info: [(残基番号, 残基名), ...]
    residue_info: List[Tuple[int, str]] = [
        (r.residue_number, r.residue_name) for r in sset.residues
    ]
    dsa_extra = analyze_flex_and_dsa_from_coords(sset.coords, residue_info)

    # 4) ログ出力（既存 + DSA 概要）
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

    # DSA/UMF 概要も表示
    print("\nDSA / UMF Stats:")
    print(f"  UMF:                {dsa_extra['umf']:.4f}")
    print(f"  PairScore Mean:     {dsa_extra['dsa_pair_score_mean']:.4f}")
    print(f"  PairScore Std:      {dsa_extra['dsa_pair_score_std']:.4f}")
    print(f"  cis-like positions: {dsa_extra['cis']['num_positions']}")

    print("\n各構造の簡易情報:")
    for i, per_struct in enumerate(result.per_structure_results):
        print(f"  [{i+1}] {per_struct.pdb_id} (chain {per_struct.chain_id})")
        print(
            f"      コンフォメーション数: {per_struct.num_conformations}\n"
            f"      Flex範囲: {per_struct.flex_stats.min:.4f} - "
            f"{per_struct.flex_stats.max:.4f}"
        )

    # 5) JSON に保存（既存の UniProtLevelResult に DSA をマージ）
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{sset.uniprot_id_input}_uniprot_result.json"

    payload = result.model_dump()
    payload["dsa"] = dsa_extra  # ← ここに全部入る

    out_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    print("\n結果JSONを書き出しました:")
    print(f"  {out_path}")

    print("\n🎉 UniProtレベル解析 完了！")
    print("============================================================")

    return result
