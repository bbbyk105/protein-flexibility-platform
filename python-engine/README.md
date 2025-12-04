# Flex Analyzer - DSA Engine

タンパク質の揺らぎ解析エンジン（Notebook DSA_Cis_250317.ipynb の完全再現）

## インストール

```bash
cd python-engine
pip install -e .
```

## 使用方法

### 基本的な使い方

```bash
flex-analyze --uniprot P62988 --output result.json
```

### カスタムパラメータ

```bash
flex-analyze \
  --uniprot P62988 \
  --max-structures 30 \
  --seq-ratio 0.85 \
  --cis-threshold 3.5 \
  --method "X-ray diffraction" \
  --output result.json
```

## パラメータ

- `--uniprot`: UniProt ID（必須）
- `--max-structures`: 解析する最大 PDB 構造数（デフォルト: 20）
- `--seq-ratio`: 配列アライメント閾値（デフォルト: 0.9）
- `--cis-threshold`: Cis 判定の距離閾値 Å（デフォルト: 3.8）
- `--method`: PDB 取得時のメソッドフィルタ（デフォルト: "X-ray diffraction"）
- `--output`, `-o`: 出力 JSON ファイルパス（必須）
- `--pdb-dir`: PDB ファイル保存ディレクトリ（デフォルト: pdb_files）
- `--verbose/--no-verbose`: 詳細ログの表示（デフォルト: True）

## 出力 JSON スキーマ

```json
{
  "uniprot_id": "P62988",
  "num_structures": 18,
  "num_residues": 150,
  "pdb_ids": ["1ABC", "2XYZ", ...],
  "excluded_pdbs": ["3BAD"],
  "seq_ratio": 0.9,
  "method": "X-ray diffraction",
  "umf": 45.67,
  "pair_score_mean": 48.23,
  "pair_score_std": 12.45,
  "pair_scores": [
    {
      "i": 1,
      "j": 2,
      "residue_pair": "ALA-1, GLY-2",
      "distance_mean": 3.85,
      "distance_std": 0.12,
      "score": 32.08
    },
    ...
  ],
  "per_residue_scores": [
    {
      "index": 0,
      "residue_number": 1,
      "residue_name": "ALA",
      "score": 42.15
    },
    ...
  ],
  "heatmap": {
    "size": 150,
    "values": [[...], ...]
  },
  "cis_info": {
    "cis_dist_mean": 2.98,
    "cis_dist_std": 0.15,
    "cis_score_mean": 25.67,
    "cis_num": 5,
    "mix": 12,
    "cis_pairs": ["45, 46", "78, 79"],
    "threshold": 3.8
  }
}
```

## モジュール構成

```
src/flex_analyzer/
├── __init__.py
├── cli.py                 # CLI エントリーポイント
├── models.py              # Pydantic モデル
├── utils.py               # ユーティリティ
├── uniprot_data.py        # UniProt データ取得
├── cif_data.py            # mmCIF 処理
├── distance.py            # 距離計算（calculat）
├── score.py               # DSA Score 計算
├── cis.py                 # Cis 検出
├── heatmap.py             # ヒートマップ生成
├── per_residue.py         # Per-residue スコア
├── sequence.py            # 配列トリミング
└── pipelines/
    ├── __init__.py
    └── dsa_pipeline.py    # 統合パイプライン
```

## 特徴

- ✅ Notebook DSA_Cis_250317.ipynb のロジックを完全再現
- ✅ NumPy ベクトル化による高速化
- ✅ 変異判定（normal / substitution / chimera / delins）対応
- ✅ Cis ペプチド結合の検出
- ✅ UMF (Unified Mobility Factor) 計算
- ✅ ヒートマップ生成
- ✅ Per-residue スコア（3D 可視化用）

## 開発

テスト実行:

```bash
pytest tests/
```

## ライセンス

Research use only
