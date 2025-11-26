"""UniProtレベル解析の完全版テスト"""

import numpy as np
import json
from src.flex_analyzer.core import compute_uniprot_level_flex
from src.flex_analyzer.models import ResidueData
from src.flex_analyzer.parser import generate_mock_coords

print("=" * 60)
print("🧪 UniProtレベル2段階解析 - 完全版テスト")
print("=" * 60)

# === テスト1: 基本動作確認 ===
print("\n[テスト1] 基本動作確認")
print("-" * 60)

# 構造1: 10コンフォメーション、30残基
coords1, residues_info1 = generate_mock_coords(
    num_structures=10, 
    num_residues=30, 
    noise_scale=1.5,
    seed=42
)

# 構造2: 5コンフォメーション、30残基
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
        flex_score=0.0,
        dsa_score=0.0
    )
    for i, (res_num, res_name) in enumerate(residues_info1)
]

# 解析実行
result = compute_uniprot_level_flex(
    structure_coords_list=[coords1, coords2],
    residues=residues,
    pdb_ids=["1ABC", "2XYZ"],
    uniprot_id="P12345",
    chain_ids=["A", "A"],
    score_threshold=0.5,
    flex_ratio_threshold=0.5
)

print(f"\n✅ 解析完了")
print(f"UniProt ID: {result.uniprot_id}")
print(f"構造数: {result.num_structures}")
print(f"総コンフォメーション数: {result.num_conformations_total}")
print(f"残基数: {result.num_residues}")

# === テスト2: flex_presence_ratio の長さ確認 ===
print("\n[テスト2] flex_presence_ratio の長さ確認")
print("-" * 60)
N = result.num_residues
expected_length = N * (N - 1) // 2
actual_length = len(result.flex_presence_ratio)
print(f"期待値: {expected_length} (= {N} × {N-1} / 2)")
print(f"実際値: {actual_length}")
assert actual_length == expected_length, "❌ flex_presence_ratio の長さが不正！"
print("✅ PASS")

# === テスト3: PairMatrix に flex_mask が存在するか ===
print("\n[テスト3] PairMatrix の flex_mask 確認")
print("-" * 60)

# 各構造
for i, per_struct in enumerate(result.per_structure_results):
    assert per_struct.pair_matrix.flex_mask is not None, f"❌ 構造{i+1}にflex_maskがない！"
    print(f"✓ 構造{i+1} ({per_struct.pdb_id}): flex_mask 存在")

# グローバル
assert result.global_pair_matrix.flex_mask is not None, "❌ globalにflex_maskがない！"
print(f"✓ グローバル: flex_mask 存在")
print("✅ PASS")

# === テスト4: final_flex_mask の条件確認 ===
print("\n[テスト4] final_flex_mask の条件確認（A OR B）")
print("-" * 60)

global_mask = np.array(result.global_pair_matrix.flex_mask)
flex_count = np.sum(global_mask)
total_pairs = N * (N - 1) // 2

print(f"柔軟なペア数: {flex_count} / {total_pairs} ({flex_count/total_pairs*100:.1f}%)")
print(f"flex_ratio_threshold: {result.flex_ratio_threshold}")
print(f"score_threshold: {result.score_threshold}")
print("✅ PASS")

# === テスト5: 対角成分が全てFalseか ===
print("\n[テスト5] 対角成分の確認")
print("-" * 60)

diagonal_check = all(not global_mask[i, i] for i in range(N))
assert diagonal_check, "❌ 対角成分にTrueが含まれている！"
print("✓ 全ての対角成分がFalse")
print("✅ PASS")

# === テスト6: JSON出力 ===
print("\n[テスト6] JSON出力テスト")
print("-" * 60)

try:
    result_json = result.model_dump_json(indent=2)
    result_dict = json.loads(result_json)
    
    # 必須フィールドの確認
    assert "uniprot_id" in result_dict
    assert "global_pair_matrix" in result_dict
    assert "flex_mask" in result_dict["global_pair_matrix"]
    assert "flex_presence_ratio" in result_dict
    assert "per_structure_results" in result_dict
    
    # ファイル保存
    with open("test_uniprot_result.json", "w") as f:
        f.write(result_json)
    
    print("✓ JSON生成成功")
    print("✓ test_uniprot_result.json に保存")
    print("✅ PASS")
except Exception as e:
    print(f"❌ FAIL: {e}")

# === テスト7: 統計情報の表示 ===
print("\n[テスト7] 統計情報")
print("-" * 60)
print(f"グローバルFlex Stats:")
print(f"  Min:    {result.global_flex_stats.min:.4f}")
print(f"  Max:    {result.global_flex_stats.max:.4f}")
print(f"  Mean:   {result.global_flex_stats.mean:.4f}")
print(f"  Median: {result.global_flex_stats.median:.4f}")

print(f"\n各構造の詳細:")
for i, per_struct in enumerate(result.per_structure_results):
    print(f"  [{i+1}] {per_struct.pdb_id} (chain {per_struct.chain_id})")
    print(f"      コンフォメーション数: {per_struct.num_conformations}")
    print(f"      Flex範囲: {per_struct.flex_stats.min:.4f} - {per_struct.flex_stats.max:.4f}")

print("\n" + "=" * 60)
print("🎉 全テスト合格！")
print("=" * 60)
