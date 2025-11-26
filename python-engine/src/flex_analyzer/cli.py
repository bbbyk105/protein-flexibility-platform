"""CLIエントリーポイント"""

import json
import click
import numpy as np
from pathlib import Path
from typing import Optional

from .parser import extract_ca_coords_from_file, extract_ca_coords_from_files, generate_mock_coords
from .core import compute_dsa_and_flex_fast
from .models import AnalysisResult, ResidueData, FlexStats, PairMatrix


@click.command()
@click.option(
    "--input",
    "-i",
    "input_files",
    multiple=True,
    type=click.Path(exists=True),
    help="Input PDB/mmCIF file(s). Can specify multiple times.",
)
@click.option("--chain", "-c", default="A", help="Chain ID to analyze (default: A)")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output JSON file path")
@click.option("--job-id", default="analysis", help="Job identifier (default: analysis)")
@click.option("--pdb-id", help="PDB ID (optional)")
@click.option("--mock", is_flag=True, help="Use mock data for testing")
@click.option(
    "--mock-structures",
    default=10,
    type=int,
    help="Number of structures for mock data (default: 10)",
)
@click.option(
    "--mock-residues", default=50, type=int, help="Number of residues for mock data (default: 50)"
)
def main(
    input_files: tuple,
    chain: str,
    output: str,
    job_id: str,
    pdb_id: Optional[str],
    mock: bool,
    mock_structures: int,
    mock_residues: int,
):
    """
    タンパク質の揺らぎ解析CLI

    複数構造からDSAスコアとflex_scoreを計算し、JSON出力します。
    """
    try:
        # データ取得
        if mock:
            click.echo("Generating mock data...")
            ca_coords, residue_info = generate_mock_coords(
                num_structures=mock_structures, num_residues=mock_residues, seed=42
            )
        elif not input_files:
            raise click.UsageError("Either --input or --mock must be specified")
        else:
            click.echo(f"Loading structures from {len(input_files)} file(s)...")
            if len(input_files) == 1:
                ca_coords, residue_info = extract_ca_coords_from_file(input_files[0], chain)
            else:
                ca_coords, residue_info = extract_ca_coords_from_files(list(input_files), chain)

        M, N, _ = ca_coords.shape
        click.echo(f"Loaded {M} structures with {N} residues")

        # 解析実行
        click.echo("Computing DSA scores and flexibility...")
        dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

        # 統計情報
        flex_stats = FlexStats(
            min=float(np.min(flex_scores)),
            max=float(np.max(flex_scores)),
            mean=float(np.mean(flex_scores)),
            median=float(np.median(flex_scores)),
        )

        # 残基データ
        residues = []
        for idx, (res_num, res_name) in enumerate(residue_info):
            # 各残基のDSAスコア平均（対角除く）
            dsa_values = np.concatenate([dsa_matrix[idx, :idx], dsa_matrix[idx, idx + 1 :]])
            avg_dsa = float(np.mean(dsa_values)) if len(dsa_values) > 0 else 0.0

            residues.append(
                ResidueData(
                    index=idx,
                    residue_number=res_num,
                    residue_name=res_name,
                    flex_score=float(flex_scores[idx]),
                    dsa_score=avg_dsa,
                )
            )

        # ペア行列（DSAスコア）
        pair_matrix = PairMatrix(type="dsa_score", size=N, values=dsa_matrix.tolist())

        # 結果オブジェクト
        result = AnalysisResult(
            job_id=job_id,
            pdb_id=pdb_id,
            chain_id=chain,
            num_structures=M,
            num_residues=N,
            residues=residues,
            flex_stats=flex_stats,
            pair_matrix=pair_matrix,
        )

        # JSON出力
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        click.echo(f"✓ Analysis complete! Results saved to {output}")
        click.echo(f"  Flex score range: {flex_stats.min:.4f} - {flex_stats.max:.4f}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
