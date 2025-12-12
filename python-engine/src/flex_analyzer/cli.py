"""CLI エントリーポイント - DSA 解析"""

from __future__ import annotations

import click
from pathlib import Path

from .pipelines import run_dsa_pipeline
from .notebook_dsa_pipeline import run_notebook_dsa_analysis


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

    # ========================================================================
    # PNG 保存パスの決定
    # ========================================================================
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # heatmap.png と distance_score.png を同じディレクトリに保存
    heatmap_png_path = output_path.with_name("heatmap.png")
    distance_score_png_path = output_path.with_name("distance_score.png")

    if verbose:
        click.echo(f"  Heatmap PNG: {heatmap_png_path}")
        click.echo(f"  Distance-Score PNG: {distance_score_png_path}")
        click.echo()

    try:
        # ====================================================================
        # パイプライン実行
        # ====================================================================
        result = run_dsa_pipeline(
            uniprot_id=uniprot,
            max_structures=max_structures,
            seq_ratio=seq_ratio,
            cis_threshold=cis_threshold,
            method=method,
            output_dir=output_path.parent,
            pdb_dir=Path(pdb_dir),
            verbose=verbose,
            heatmap_png_path=heatmap_png_path,
            distance_score_png_path=distance_score_png_path,
        )

        # ====================================================================
        # JSON 出力
        # ====================================================================
        with output_path.open("w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        if verbose:
            click.echo(f"\n✅ Results saved to: {output_path}")
            click.echo(f"✅ Heatmap PNG saved to: {heatmap_png_path}")
            click.echo(f"✅ Distance-Score PNG saved to: {distance_score_png_path}")
            click.echo("\nSummary:")
            click.echo(f"  UMF: {result.umf:.4f}")
            click.echo(f"  Structures used: {result.num_structures}")
            click.echo(f"  Residues: {result.num_residues}")
            click.echo(f"  Cis pairs: {result.cis_info.cis_num}")
            click.echo(f"  Mixed pairs: {result.cis_info.mix}")

        click.echo("\n✅ Analysis completed successfully.")

    except Exception as e:
        click.echo(f"\nError: {str(e)}", err=True)
        if verbose:
            import traceback

            click.echo("\nFull traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@click.command()
@click.option("--uniprot-ids", required=True, help="UniProt ID(s) (comma or space separated)")
@click.option(
    "--method",
    default="X-ray",
    help="PDB method filter: X-ray, NMR, EM (default: X-ray)",
)
@click.option(
    "--seq-ratio",
    default=0.2,
    type=float,
    help="Sequence alignment ratio threshold (default: 0.2)",
)
@click.option(
    "--negative-pdbid",
    default="",
    help="PDB IDs to exclude (space or comma separated)",
)
@click.option(
    "--cis-threshold",
    default=3.3,
    type=float,
    help="Distance threshold for cis detection in Angstroms (default: 3.3)",
)
@click.option(
    "--output-dir",
    default="output",
    type=click.Path(),
    help="Output directory (default: output)",
)
@click.option(
    "--pdb-dir",
    default="pdb_files",
    type=click.Path(),
    help="Directory to store PDB files (default: pdb_files)",
)
@click.option(
    "--export/--no-export",
    default=True,
    help="Export CSV files (default: True)",
)
@click.option(
    "--heatmap/--no-heatmap",
    default=True,
    help="Generate heatmap (default: True)",
)
@click.option(
    "--proc-cis/--no-proc-cis",
    default=True,
    help="Process cis analysis (default: True)",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=True,
    help="Overwrite existing data (default: True)",
)
@click.option(
    "--verbose/--no-verbose",
    default=True,
    help="Enable verbose output (default: True)",
)
def notebook_main(
    uniprot_ids: str,
    method: str,
    seq_ratio: float,
    negative_pdbid: str,
    cis_threshold: float,
    output_dir: str,
    pdb_dir: str,
    export: bool,
    heatmap: bool,
    proc_cis: bool,
    overwrite: bool,
    verbose: bool,
):
    """
    Notebook DSA Analysis - Colabコード完全再現版

    Colab Notebook DSA_Cis_250317.ipynb の機能を完全に再現:
    - 複数のUniProt IDの処理
    - negative_pdbidの除外
    - normal/substitution/chimera/delinsの分類と個別処理
    - 複数のseqtype（normal, sub, nor+sub）での解析
    - ヒートマップの比較表示
    - CSVファイルへの出力
    - バックアップ機能
    - 上書き/追記オプション
    """
    if verbose:
        click.echo("=" * 80)
        click.echo("Notebook DSA Analysis Tool")
        click.echo("=" * 80)
        click.echo("\nParameters:")
        click.echo(f"  UniProt ID(s): {uniprot_ids}")
        click.echo(f"  Method: {method}")
        click.echo(f"  Seq ratio: {seq_ratio}")
        click.echo(f"  Cis threshold: {cis_threshold} A")
        click.echo(f"  Negative PDB IDs: {negative_pdbid if negative_pdbid else '(none)'}")
        click.echo(f"  Output directory: {output_dir}")
        click.echo(f"  PDB directory: {pdb_dir}")
        click.echo(f"  Export CSV: {export}")
        click.echo(f"  Generate heatmap: {heatmap}")
        click.echo(f"  Process cis: {proc_cis}")
        click.echo(f"  Overwrite: {overwrite}")
        click.echo()

    try:
        run_notebook_dsa_analysis(
            uniprot_ids=uniprot_ids,
            method=method,
            seq_ratio=seq_ratio,
            negative_pdbid=negative_pdbid,
            export=export,
            heatmap=heatmap,
            verbose=verbose,
            proc_cis=proc_cis,
            cis_threshold=cis_threshold,
            overwrite=overwrite,
            output_dir=Path(output_dir),
            pdb_dir=Path(pdb_dir),
        )

        if verbose:
            click.echo("\n✅ Analysis completed successfully.")

    except Exception as e:
        click.echo(f"\nError: {str(e)}", err=True)
        if verbose:
            import traceback

            click.echo("\nFull traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


if __name__ == "__main__":
    import sys

    # コマンドライン引数でnotebookモードを判定
    if len(sys.argv) > 1 and sys.argv[1] == "notebook":
        sys.argv = sys.argv[1:]  # "notebook"を削除
        notebook_main()
    else:
        main()
