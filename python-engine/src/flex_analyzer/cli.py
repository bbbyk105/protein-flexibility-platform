"""CLI エントリーポイント - DSA 解析"""

import json
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
    "--seq-ratio", default=0.9, type=float, help="Sequence alignment ratio threshold (default: 0.9)"
)
@click.option(
    "--cis-threshold",
    default=3.8,
    type=float,
    help="Distance threshold for cis detection in Angstroms (default: 3.8)",
)
@click.option(
    "--method", default="X-ray diffraction", help="PDB method filter (default: 'X-ray diffraction')"
)
@click.option("--output", "-o", required=True, type=click.Path(), help="Output JSON file path")
@click.option(
    "--pdb-dir",
    default="pdb_files",
    type=click.Path(),
    help="Directory to store PDB files (default: pdb_files)",
)
@click.option("--verbose/--no-verbose", default=True, help="Enable verbose output (default: True)")
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

    \b
    Examples:
      # Basic analysis
      flex-analyze --uniprot P62988 --output result.json

      # Custom parameters
      flex-analyze --uniprot P62988 --max-structures 30 --seq-ratio 0.85 --output result.json

      # Adjust cis threshold
      flex-analyze --uniprot P62988 --cis-threshold 3.5 --output result.json
    """

    if verbose:
        click.echo("=" * 80)
        click.echo("DSA Analysis Tool")
        click.echo("=" * 80)
        click.echo(f"\nParameters:")
        click.echo(f"  UniProt ID: {uniprot}")
        click.echo(f"  Max structures: {max_structures}")
        click.echo(f"  Seq ratio: {seq_ratio}")
        click.echo(f"  Cis threshold: {cis_threshold} A")
        click.echo(f"  Method: {method}")
        click.echo(f"  Output: {output}")
        click.echo()

    try:
        # パイプライン実行
        result = run_dsa_pipeline(
            uniprot_id=uniprot,
            max_structures=max_structures,
            seq_ratio=seq_ratio,
            cis_threshold=cis_threshold,
            method=method,
            output_dir=Path(output).parent,
            pdb_dir=Path(pdb_dir),
            verbose=verbose,
        )

        # JSON 出力
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        if verbose:
            click.echo(f"\nResults saved to: {output}")
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
