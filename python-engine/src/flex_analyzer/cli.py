"""CLI エントリーポイント - DSA 解析"""

from __future__ import annotations

import click
from pathlib import Path

from .pipelines import run_dsa_pipeline


@click.command()
@click.option("--uniprot", required=True, help="UniProt accession ID (e.g., P62988)")
@click.option(
    "--max-structures",
    default=20,
    type=int,
    help="Maximum number of PDB structures to analyze (default: 20)",
)
@click.option(
    "--seq-ratio",
    default=0.9,
    type=float,
    help="Sequence alignment ratio threshold (default: 0.9)",
)
@click.option(
    "--cis-threshold",
    default=3.8,
    type=float,
    help="Distance threshold for cis detection in Angstroms (default: 3.8)",
)
@click.option(
    "--method",
    default="X-ray diffraction",
    help="PDB method filter (default: 'X-ray diffraction')",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output JSON file path",
)
@click.option(
    "--pdb-dir",
    default="pdb_files",
    type=click.Path(),
    help="Directory to store PDB files (default: pdb_files)",
)
@click.option(
    "--verbose/--no-verbose",
    default=True,
    help="Enable verbose output (default: True)",
)
def main(
    uniprot: str,
    max_structures: int,
    seq_ratio: float,
    cis_threshold: float,
    method: str,
    output: str,
    pdb_dir: str,
    verbose: bool,
):
    """
    DSA (Distance Scoring Analysis) for protein flexibility

    Analyzes protein flexibility from multiple PDB structures using the DSA method.
    """

    if verbose:
        click.echo("=" * 80)
        click.echo("DSA Analysis Tool")
        click.echo("=" * 80)
        click.echo("\nParameters:")
        click.echo(f"  UniProt ID: {uniprot}")
        click.echo(f"  Max structures: {max_structures}")
        click.echo(f"  Seq ratio: {seq_ratio}")
        click.echo(f"  Cis threshold: {cis_threshold} A")
        click.echo(f"  Method: {method}")
        click.echo(f"  Output (JSON): {output}")
        click.echo()

    # ★ ここで output_path と heatmap_png_path を決める
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    heatmap_png_path = output_path.with_name("heatmap.png")

    if verbose:
        click.echo(f"  Heatmap PNG: {heatmap_png_path}")
        click.echo()

    try:
        # パイプライン実行（PNG の保存パスも渡す）
        result = run_dsa_pipeline(
            uniprot_id=uniprot,
            max_structures=max_structures,
            seq_ratio=seq_ratio,
            cis_threshold=cis_threshold,
            method=method,
            output_dir=output_path.parent,
            pdb_dir=Path(pdb_dir),
            verbose=verbose,
            heatmap_png_path=heatmap_png_path,  # ★ここが追加
        )

        # JSON 出力
        with output_path.open("w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        if verbose:
            click.echo(f"\nResults saved to: {output_path}")
            click.echo(f"Heatmap PNG saved to: {heatmap_png_path}")
            click.echo("\nSummary:")
            click.echo(f"  UMF: {result.umf:.4f}")
            click.echo(f"  Structures used: {result.num_structures}")
            click.echo(f"  Residues: {result.num_residues}")
            click.echo(f"  Cis pairs: {result.cis_info.cis_num}")
            click.echo(f"  Mixed pairs: {result.cis_info.mix}")

        click.echo("\nAnalysis completed successfully.")

    except Exception as e:
        click.echo(f"\nError: {str(e)}", err=True)
        if verbose:
            import traceback

            click.echo("\nFull traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
