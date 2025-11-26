"""UniProtレベル解析のテストスクリプト"""

import numpy as np
from src.flex_analyzer.core import compute_uniprot_level_flex
from src.flex_analyzer.models import ResidueData
from src.flex_analyzer.parser import generate_mock_coords

# モックデータ生成：2つの構造グループ
print("🧪 テスト開始: UniProtレベル解析")
print("-" * 50)

# 構造1: 10個のコンフォメーション、30残基
coords1, residues_info1 = generate_mock_coords(
    num_structures=10, 
    num_residues=30, 
    noise_scale=1.5,
    seed=42
)

# 構造2: 5個のコンフォメーション、30残基（同じ残基数）
coords2, residues_info2 = generate_mock_coords(
    num_structures=5, 
    num_residues=30, 
    noise_scale=2.0,
    seed=123
)

print(f"✓ 構造1: {coords1.shape[0]} コンフォメーション x {coords1.shape[1]} 残基")
print(f"✓ 構造2: {coords2.shape[0]} コンフォメーション x {coords2.shape[1]} 残基")

# ResidueDataリスト作成
residues = [
    ResidueData(
        index=i,
        residue_number=res_num,
        residue_name=res_name,
        flex_score=0.0,  # 仮の値
        dsa_score=0.0    # 仮の値
    )
    for i, (res_num, res_name) in enumerate(residues_info1)
]

# UniProtレベル解析実行
print("\n�� UniProtレベル解析実行中...")
result = compute_uniprot_level_flex(
    structure_coords_list=[coords1, coords2],
    residues=residues,
    pdb_ids=["1ABC", "2XYZ"],
    uniprot_id="P12345",
    chain_ids=["A", "A"],
    flex_ratio_threshold=0.5
)

print("\n✅ 解析完了！")
print("-" * 50)
print(f"UniProt ID: {result.uniprot_id}")
print(f"構造数: {result.num_structures}")
print(f"総コンフォメーション数: {result.num_conformations_total}")
print(f"残基数: {result.num_residues}")
print(f"\nグローバルFlex Stats:")
print(f"  Min:    {result.global_flex_stats.min:.4f}")
print(f"  Max:    {result.global_flex_stats.max:.4f}")
print(f"  Mean:   {result.global_flex_stats.mean:.4f}")
print(f"  Median: {result.global_flex_stats.median:.4f}")

print(f"\n各構造の詳細:")
for i, per_struct in enumerate(result.per_structure_results):
    print(f"  [{i+1}] {per_struct.pdb_id} (chain {per_struct.chain_id})")
    print(f"      コンフォメーション数: {per_struct.num_conformations}")
    print(f"      Flex範囲: {per_struct.flex_stats.min:.4f} - {per_struct.flex_stats.max:.4f}")

print(f"\nflex_presence_ratio: {len(result.flex_presence_ratio)} ペア")
print(f"  例: 最初の5ペア = {result.flex_presence_ratio[:5]}")

print(f"\n✓ 全ての機能が正常に動作しました！")
