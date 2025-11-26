# Flex Analyzer - タンパク質揺らぎ解析エンジン

複数構造の Cα 座標から DSA スコアと可変性指標を高速計算する Python パッケージ。

## 特徴

- ✅ **単一 PDB 解析**: 複数モデルを含む PDB ファイルから揺らぎを計算
- ✅ **UniProt 自動解析**: UniProt ID から自動的に PDB 構造を取得・解析
- ✅ **高速計算**: NumPy ベクトル化により高速処理
- ✅ **JSON 出力**: Web 可視化に最適な形式で出力

## インストール

```bash
cd python-engine
pip install -e ".[dev]"
```

## 使い方

### 1. UniProt 自動解析（推奨）

UniProt ID を指定するだけで、自動的に PDB 構造を取得・解析します。

```bash
# ユビキチン（P62988）を解析
flex-analyze --uniprot P62988 --max-structures 20 -o results/ubiquitin.json

# 最大構造数を制限
flex-analyze --uniprot P12345 --max-structures 10 -o results/result.json

# 閾値をカスタマイズ
flex-analyze --uniprot P62988 \
  --max-structures 20 \
  --flex-ratio-threshold 0.6 \
  --score-threshold 1.5 \
  -o results/result.json
```

**特徴:**

- Inactive な UniProt ID も自動解決（DEMERGED 対応）
- 404 の PDB を自動スキップ
- 残基数ミスマッチの構造を自動除外
- フルレングス構造のみを使用

### 2. 単一 PDB 解析

```bash
# 単一ファイル（複数MODELを含む）
flex-analyze -i data/protein.pdb -c A -o results/result.json --job-id job1

# 複数ファイル
flex-analyze -i struct1.pdb -i struct2.pdb -i struct3.pdb -c A -o results/result.json
```

### 3. モックデータでのテスト

```bash
flex-analyze --mock --output results/mock_result.json --job-id mock_test

# 構造数・残基数をカスタマイズ
flex-analyze --mock --mock-structures 50 --mock-residues 100 -o results/mock.json
```

## Python API での使用

### UniProt 解析パイプライン

```python
from flex_analyzer.pipelines.uniprot_pipeline import run_uniprot_pipeline

# P62988（ユビキチン）を解析
result = run_uniprot_pipeline(
    uniprot_id="P62988",
    max_structures=20,
)

print(f"構造数: {result.num_structures}")
print(f"総コンフォメーション数: {result.num_conformations_total}")
print(f"グローバル Flex Stats: {result.global_flex_stats}")
```

### 低レベル API

```python
from flex_analyzer.core import compute_dsa_and_flex_fast
import numpy as np

# 座標データ（M構造 x N残基 x 3次元）
coords = np.random.randn(10, 50, 3)

# 解析実行
residue_flex, residue_dsa, pair_matrix = compute_dsa_and_flex_fast(coords)

print(f"残基ごとの flex_score: {residue_flex}")
```

## 出力 JSON 形式

### 単一 PDB 解析

```json
{
  "job_id": "example",
  "pdb_id": "1UBQ",
  "chain_id": "A",
  "num_structures": 10,
  "num_residues": 76,
  "residues": [
    {
      "index": 0,
      "residue_number": 1,
      "residue_name": "MET",
      "flex_score": 1.234,
      "dsa_score": 0.567
    }
  ],
  "flex_stats": {
    "min": 0.123,
    "max": 3.456,
    "mean": 0.789,
    "median": 0.654
  },
  "pair_matrix": {
    "type": "flex",
    "data": [0.1, 0.2, ...],
    "size": 76
  }
}
```

### UniProt レベル解析

```json
{
  "uniprot_id": "P62987",
  "num_structures": 7,
  "num_conformations_total": 402,
  "num_residues": 76,
  "residues": [...],
  "global_flex_stats": {...},
  "global_pair_matrix": {...},
  "per_structure_results": [
    {
      "pdb_id": "2LJ5",
      "chain_id": "A",
      "num_conformations": 200,
      "flex_stats": {...}
    }
  ],
  "flex_presence_ratio": [...],
  "flex_ratio_threshold": 0.5,
  "score_threshold": 1.0
}
```

## テストの実行

```bash
# 全テスト実行
pytest tests/ -v

# 特定のテスト
pytest tests/test_core.py -v
pytest tests/test_accuracy.py -v

# UniProt パイプラインテスト
python test_uniprot_complete.py
```

## プロジェクト構造

```
python-engine/
├── src/flex_analyzer/
│   ├── cli.py              # CLIエントリーポイント
│   ├── core.py             # コア解析アルゴリズム
│   ├── models.py           # データモデル
│   ├── parser.py           # PDB/mmCIF パーサー
│   ├── data_sources/
│   │   ├── uniprot.py      # UniProt API連携
│   │   └── __init__.py
│   └── pipelines/
│       ├── uniprot_pipeline.py  # UniProt解析パイプライン
│       └── __init__.py
├── tests/                  # テストコード
├── data/                   # ダウンロード済みPDB
└── output/                 # 解析結果JSON
```

## 技術仕様

- **言語**: Python 3.12+
- **主要ライブラリ**:
  - NumPy 1.26.0 (高速計算)
  - Biopython 1.83 (PDB 解析)
  - Pydantic 2.5.0 (データ検証)
  - Click 8.1.0 (CLI)
  - Requests 2.31.0 (API 通信)

## ライセンス

MIT License

## 開発者向け

### 開発環境セットアップ

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### 新しい機能の追加

1. `src/flex_analyzer/` に機能を実装
2. `tests/` にテストを追加
3. `README.md` に使用例を追加
4. プルリクエストを作成

## トラブルシューティング

### UniProt ID が見つからない

```bash
# Inactive ID の場合、自動的に Active ID へリダイレクトされます
flex-analyze --uniprot P62988 -o result.json
# → P62987 へ自動解決
```

### PDB ダウンロードエラー

```bash
# 404 の PDB は自動的にスキップされます
# 残基数が異なる PDB も自動除外されます
```

### メモリ不足

```bash
# 構造数を制限してください
flex-analyze --uniprot P12345 --max-structures 10 -o result.json
```

## サポート

- GitHub Issues: https://github.com/bbbyk105/protein-flexibility-platform/issues
- ドキュメント: [coming soon]
