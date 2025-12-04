#!/usr/bin/env python3
"""
統合テストスクリプト - 全モジュールの動作確認

このスクリプトは以下をテストします:
1. 各モジュールのインポート
2. 基本的な関数の動作
3. 小規模データでのパイプライン実行
4. JSON 出力の検証
"""

import sys
import json
import tempfile
from pathlib import Path

print("=" * 80)
print("Flex Analyzer - 統合テスト")
print("=" * 80)

# Step 1: モジュールのインポートテスト
print("\n[Step 1] モジュールのインポートテスト...")

modules_to_test = [
    "models",
    "utils",
    "distance",
    "score",
    "cis",
    "heatmap",
    "per_residue",
    "uniprot_data",
    "cif_data",
    "sequence",
]

for module_name in modules_to_test:
    try:
        __import__(f"src.flex_analyzer.{module_name}")
        print(f"  ✓ {module_name}")
    except ImportError as e:
        print(f"  ✗ {module_name}: {e}")
        sys.exit(1)

try:
    from src.flex_analyzer.pipelines import dsa_pipeline

    print("  ✓ pipelines.dsa_pipeline")
except ImportError as e:
    print(f"  ✗ pipelines.dsa_pipeline: {e}")
    sys.exit(1)

print("\n  ✅ 全モジュールのインポート成功！")

# Step 2: 基本関数のテスト
print("\n[Step 2] 基本関数のテスト...")

import numpy as np
import pandas as pd
from src.flex_analyzer.distance import calculat
from src.flex_analyzer.utils import convert_one_to_three, convert_three_to_one

# calculat 関数のテスト
atom1 = np.array([0.0, 0.0, 0.0])
atom2 = np.array([1.0, 0.0, 0.0])
dist = calculat(atom1, atom2)
expected = 1.0

if abs(dist - expected) < 0.001:
    print(f"  ✓ calculat: {dist:.3f} Å (expected: {expected:.3f} Å)")
else:
    print(f"  ✗ calculat: {dist:.3f} Å (expected: {expected:.3f} Å)")
    sys.exit(1)

# アミノ酸変換のテスト
if convert_one_to_three("A") == "ALA":
    print("  ✓ convert_one_to_three")
else:
    print("  ✗ convert_one_to_three")
    sys.exit(1)

if convert_three_to_one("ALA") == "A":
    print("  ✓ convert_three_to_one")
else:
    print("  ✗ convert_three_to_one")
    sys.exit(1)

print("\n  ✅ 基本関数のテスト成功！")

# Step 3: Pydantic モデルのテスト
print("\n[Step 3] Pydantic モデルのテスト...")

from src.flex_analyzer.models import PairScore, PerResidueScore, CisInfo, Heatmap, NotebookDSAResult

try:
    # PairScore のテスト
    pair = PairScore(
        i=1, j=2, residue_pair="ALA-1, GLY-2", distance_mean=3.85, distance_std=0.12, score=32.08
    )
    print("  ✓ PairScore")

    # PerResidueScore のテスト
    per_res = PerResidueScore(index=0, residue_number=1, residue_name="ALA", score=42.15)
    print("  ✓ PerResidueScore")

    # CisInfo のテスト
    cis_info = CisInfo(
        cis_dist_mean=2.98,
        cis_dist_std=0.15,
        cis_score_mean=25.67,
        cis_num=5,
        mix=12,
        cis_pairs=["1, 2"],
        threshold=3.8,
    )
    print("  ✓ CisInfo")

    # Heatmap のテスト
    hm = Heatmap(size=2, values=[[None, 32.08], [32.08, None]])
    print("  ✓ Heatmap")

    # NotebookDSAResult のテスト
    result = NotebookDSAResult(
        uniprot_id="P62988",
        num_structures=1,
        num_residues=2,
        pdb_ids=["1ABC"],
        excluded_pdbs=[],
        seq_ratio=0.9,
        method="X-ray diffraction",
        umf=35.5,
        pair_score_mean=35.5,
        pair_score_std=0.0,
        pair_scores=[pair],
        per_residue_scores=[per_res],
        heatmap=hm,
        cis_info=cis_info,
    )
    print("  ✓ NotebookDSAResult")

    # JSON シリアライズのテスト
    json_str = result.model_dump_json(indent=2)
    json_obj = json.loads(json_str)
    print("  ✓ JSON シリアライズ")

    print("\n  ✅ Pydantic モデルのテスト成功！")

except Exception as e:
    print(f"  ✗ Pydantic モデルエラー: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Step 4: UniProt データ取得テスト（ネットワーク接続が必要）
print("\n[Step 4] UniProt データ取得テスト（オプション）...")
print("  ⚠ このテストはインターネット接続が必要です")

try_uniprot = input("  UniProt データ取得をテストしますか？ (y/N): ").strip().lower()

if try_uniprot == "y":
    try:
        from src.flex_analyzer.uniprot_data import UniprotData

        # まず P62988 のリダイレクトをテスト
        print("\n  [リダイレクトテスト]")
        print("  テスト: P62988 (Obsolete ID)")
        test_obsolete = UniprotData("P62988")
        print(f"  ✓ P62988 → {test_obsolete.get_resolved_id()} にリダイレクト成功")

        # 次に通常のデータ取得をテスト
        print("\n  [通常のデータ取得テスト]")
        # P69905 (Hemoglobin subunit alpha) を使用
        # 理由: X-ray 構造が豊富（200+ entries）で、テストに最適
        test_id = "P69905"
        print(f"  テスト UniProt ID: {test_id} (Hemoglobin subunit alpha)")

        unidata = UniprotData(test_id)
        print(f"  ✓ UniProt データ取得成功")

        uniprot_ids = unidata.get_id()
        print(f"  ✓ UniProt IDs: {uniprot_ids}")

        fasta = unidata.fasta()
        print(f"  ✓ FASTA 配列取得: {len(fasta)} aa")

        fullname = unidata.get_fullname()
        print(f"  ✓ Full name: {fullname}")

        # X-ray でフィルタ（修正後は "X-ray" として正しく認識される）
        pdblist = unidata.pdblist("X-ray diffraction")
        print(f"  ✓ PDB リスト (X-ray): {len(pdblist)} entries")
        print(f"    {', '.join(pdblist[:5])}{'...' if len(pdblist) > 5 else ''}")

        print("\n  ✅ UniProt データ取得テスト成功！")

    except Exception as e:
        print(f"  ⚠ UniProt テストでエラー: {e}")
        import traceback

        traceback.print_exc()
else:
    print("  ⏭ UniProt テストをスキップ")

# Step 5: パイプライン統合テスト（オプション）
print("\n[Step 5] パイプライン統合テスト（オプション）...")
print("  ⚠ このテストは数分かかる場合があります")

try_pipeline = input("  完全なパイプラインをテストしますか？ (y/N): ").strip().lower()

if try_pipeline == "y":
    try:
        from src.flex_analyzer.pipelines.dsa_pipeline import run_dsa_pipeline

        # テスト用の一時ディレクトリ
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # P69905 (Hemoglobin subunit alpha) を使用
            # 理由: X-ray 構造が豊富で、確実に 2 構造以上取得できる
            print(f"\n  テスト UniProt ID: P69905 (Hemoglobin subunit alpha)")
            print(f"  最大構造数: 3 (テスト用)")
            print(f"  出力ディレクトリ: {tmpdir}")
            print("\n  解析を開始します...")

            result = run_dsa_pipeline(
                uniprot_id="P69905",
                max_structures=3,
                seq_ratio=0.9,
                cis_threshold=3.8,
                method="X-ray diffraction",  # 修正後は正しく動作
                output_dir=tmpdir,
                pdb_dir=tmpdir / "pdb_files",
                verbose=True,
            )

            print("\n  ✓ パイプライン実行成功！")
            print(f"\n  結果サマリー:")
            print(f"    UniProt ID: {result.uniprot_id}")
            print(f"    構造数: {result.num_structures}")
            print(f"    残基数: {result.num_residues}")
            print(f"    UMF: {result.umf:.4f}")
            print(f"    Pair scores: {len(result.pair_scores)}")
            print(f"    Per-residue scores: {len(result.per_residue_scores)}")
            print(f"    Cis pairs: {result.cis_info.cis_num}")
            print(f"    Mixed pairs: {result.cis_info.mix}")

            # JSON 保存テスト
            output_path = tmpdir / "test_result.json"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))

            print(f"\n  ✓ JSON 出力テスト成功: {output_path}")

            # JSON 読み込みテスト
            with open(output_path, "r", encoding="utf-8") as f:
                loaded_json = json.load(f)

            print(f"  ✓ JSON 読み込みテスト成功")
            print(f"    JSON サイズ: {len(json.dumps(loaded_json))} bytes")

            print("\n  ✅ パイプライン統合テスト成功！")

    except Exception as e:
        print(f"  ✗ パイプラインテストエラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
else:
    print("  ⏭ パイプラインテストをスキップ")

# 最終結果
print("\n" + "=" * 80)
print("✅ 全テスト完了！")
print("=" * 80)
print("\n次のステップ:")
print("  1. パッケージをインストール: pip install -e .")
print("  2. CLI を実行: flex-analyze --uniprot P62988 --output result.json")
print("=" * 80)
