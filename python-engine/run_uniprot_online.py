#!/usr/bin/env python
"""
UniProt ID からオンラインで構造を取得し、
UniProt レベル揺らぎ解析パイプラインを実行する CLI エントリ。

使い方:
    python run_uniprot_online.py P62988 20
"""

import argparse
from pathlib import Path

from src.flex_analyzer.pipelines import run_uniprot_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run UniProt-level flexibility analysis via online structure fetching."
    )
    parser.add_argument(
        "uniprot_id",
        help="UniProt accession ID (e.g. P62988)",
    )
    parser.add_argument(
        "max_structures",
        nargs="?",
        type=int,
        default=20,
        help="Maximum number of PDB structures to fetch and use (default: 20).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/uniprot_results"),
        help="Directory to save the JSON result.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_uniprot_pipeline(
        uniprot_id=args.uniprot_id.strip(),
        max_structures=args.max_structures,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
