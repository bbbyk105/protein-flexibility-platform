# Flex Analyzer - タンパク質揺らぎ解析エンジン

複数構造の Cα 座標から DSA スコアと可変性指標を高速計算する Python パッケージ。

## インストール

```bash
cd python-engine
pip install -e ".[dev]"
```

## 使い方

### モックデータでのテスト

```bash
flex-analyze --mock --output results/mock_result.json --job-id mock_test
```

### 実際の PDB ファイルを使用

```bash
# 単一ファイル（複数MODELを含む）
flex-analyze -i data/protein.pdb -c A -o results/result.json --job-id job1

# 複数ファイル
flex-analyze -i struct1.pdb -i struct2.pdb -i struct3.pdb -c A -o results/result.json
```

## テストの実行

```bash
pytest tests/ -v
```

## 出力 JSON 形式

```json
{
  "job_id": "example",
  "pdb_id": "XXXX",
  "chain_id": "A",
  "num_structures": 10,
  "num_residues": 150,
  "residues": [...],
  "flex_stats": {...},
  "pair_matrix": {...}
}
```
