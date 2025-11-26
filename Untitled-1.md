```
protein-flexibility-platform/
├── python-engine/              # Python解析エンジン
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/
│   │   └── flex_analyzer/
│   │       ├── __init__.py
│   │       ├── cli.py          # CLIエントリーポイント
│   │       ├── core.py         # NumPy高速実装
│   │       ├── reference.py    # 参照実装(forループ)
│   │       ├── parser.py       # PDB/mmCIFパーサー
│   │       ├── models.py       # Pydanticモデル
│   │       └── utils.py        # ユーティリティ
│   └── tests/
│       ├── __init__.py
│       ├── test_core.py        # 高速版のテスト
│       └── test_accuracy.py    # 高速版vs参照版の一致検証
│
├── go-api/                     # Go + Fiber APIサーバ
│   ├── go.mod
│   ├── go.sum
│   ├── main.go
│   ├── handlers/
│   │   └── results.go
│   ├── models/
│   │   └── result.go
│   ├── data/                   # サンプルJSON格納用
│   │   └── sample_result.json
│   └── README.md
│
└── nextjs-frontend/            # Next.js フロントエンド
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── api/                # 必要に応じてNext.js API Routes
    ├── components/
    │   ├── FlexScoreChart.tsx  # 残基ごとのスコアグラフ
    │   ├── MolstarViewer.tsx   # Mol* 3D表示
    │   ├── HeatmapViewer.tsx   # ヒートマップ
    │   └── ui/                 # shadcn/uiコンポーネント
    ├── lib/
    │   ├── api.ts              # API呼び出しロジック
    │   └── types.ts            # TypeScript型定義
    └── README.md
```
