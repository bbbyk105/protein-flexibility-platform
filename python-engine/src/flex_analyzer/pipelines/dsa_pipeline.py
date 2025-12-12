"""DSA 解析統合パイプライン - Notebook DSA_Cis_250317.ipynb の完全再現"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ..models import NotebookDSAResult, PairScore, PerResidueScore, Heatmap, CisInfo
from ..uniprot_data import UniprotData, convert_three
from ..cif_data import CifData
from ..sequence import sort_sequence, getcoord
from ..distance import getdistance2
from ..score import getscore, compute_umf, compute_pair_statistics
from ..cis import detect_cis_pairs
from ..heatmap import generate_heatmap, heatmap_to_list, save_heatmap_png
from ..per_residue import per_residue_scores_fast


def save_distance_score_plot(score_df: pd.DataFrame, output_dir: Path, title: str) -> None:
    """
    Cα–Cα distance (x) vs DSA score (y) の散布図を PNG で保存する。
    output_dir/distance_score.png に保存。

    改善版:
    - より見やすいプロット（サイズ、色、グリッド）
    - 外れ値の自動クリップ
    - 統計情報の表示
    """
    import matplotlib

    matplotlib.use("Agg")  # GUI なし環境対応
    import matplotlib.pyplot as plt

    # 必要なカラムだけ取り出し
    df = score_df.copy()

    # 無限大/NaN は落とす
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["distance mean", "score"])

    if df.empty:
        print(f"[save_distance_score_plot] WARNING: 有効なデータがありません")
        return  # データ無ければ何もしない

    distances = df["distance mean"].to_numpy()
    scores = df["score"].to_numpy()

    # 外れ値のクリップ（1%と99%パーセンタイル）
    try:
        score_min = float(np.nanpercentile(scores, 1))
        score_max = float(np.nanpercentile(scores, 99))
        dist_min = float(np.nanpercentile(distances, 1))
        dist_max = float(np.nanpercentile(distances, 99))

        mask = (
            (scores >= score_min)
            & (scores <= score_max)
            & (distances >= dist_min)
            & (distances <= dist_max)
        )
        distances = distances[mask]
        scores = scores[mask]
    except Exception:
        # 何かあっても、とりあえずそのまま描く
        pass

    if len(distances) == 0:
        print(f"[save_distance_score_plot] WARNING: クリップ後データがありません")
        return  # クリップ後データが無ければ何もしない

    png_path = output_dir / "distance_score.png"
    output_dir.mkdir(parents=True, exist_ok=True)  # ディレクトリが存在することを確認

    # より見やすいプロット設定
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)

    # 散布図の作成（色とサイズを改善）
    scatter = ax.scatter(
        distances,
        scores,
        s=8,  # ポイントサイズを少し大きく
        alpha=0.6,  # 透明度を調整
        c=scores,  # スコアに応じた色付け
        cmap="viridis",  # カラーマップ
        edgecolors="none",
        linewidths=0.5,
    )

    # 軸ラベルとタイトル
    ax.set_xlabel("Cα–Cα distance (Å)", fontsize=13, fontweight="bold")
    ax.set_ylabel("DSA score (mean / std)", fontsize=13, fontweight="bold")
    ax.set_title(f"{title} – Distance vs Score", fontsize=15, fontweight="bold", pad=15)

    # グリッドの改善
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.8)
    ax.set_axisbelow(True)

    # カラーバーの追加
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("Score", fontsize=11, fontweight="bold")

    # 統計情報をテキストで表示
    mean_score = np.nanmean(scores)
    std_score = np.nanstd(scores)
    mean_dist = np.nanmean(distances)

    stats_text = f"Mean score: {mean_score:.2f} ± {std_score:.2f}\nMean distance: {mean_dist:.2f} Å"
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        family="monospace",
    )

    plt.tight_layout()
    try:
        plt.savefig(png_path, dpi=300, bbox_inches="tight")
        print(f"[save_distance_score_plot] SUCCESS: Saved to {png_path}")
    except Exception as e:
        print(f"[save_distance_score_plot] ERROR: Failed to save PNG: {e}")
        raise
    finally:
        plt.close(fig)


def run_dsa_pipeline(
    uniprot_id: str,
    max_structures: int = 20,
    seq_ratio: float = 0.9,
    cis_threshold: float = 3.8,
    method: str = "X-ray diffraction",
    output_dir: Path = Path("output"),
    pdb_dir: Path = Path("pdb_files"),
    verbose: bool = True,
    heatmap_png_path: Optional[Path] = None,
) -> NotebookDSAResult:
    """
    Notebook DSA 解析の完全な再現パイプライン

    Args:
        uniprot_id: UniProt accession ID
        max_structures: 解析する最大 PDB 構造数
        seq_ratio: 配列アライメント閾値 (0.0-1.0)
        cis_threshold: Cis 判定の距離閾値 (Å)
        method: PDB 取得時のメソッドフィルタ
        output_dir: 出力ディレクトリ
        pdb_dir: PDB ファイル保存ディレクトリ
        verbose: ログ出力の有効化

    Returns:
        NotebookDSAResult
    """
    if verbose:
        print("=" * 80)
        print(f"DSA Analysis Pipeline - {uniprot_id}")
        print("=" * 80)

    # ディレクトリ作成
    output_dir.mkdir(parents=True, exist_ok=True)
    pdb_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: UniProt データ取得
    if verbose:
        print("\n[Step 1] Fetching UniProt data...")

    unidata = UniprotData(uniprot_id)
    uniprotids = unidata.get_id()
    fasta = unidata.fasta()
    sequence = convert_three(fasta)
    fullname = unidata.get_fullname()
    organism = unidata.get_organism()

    if verbose:
        print(f"  Protein: {fullname}")
        print(f"  Organism: {organism}")
        print(f"  Sequence length: {len(sequence)}")

    # Step 2: PDB リスト取得
    if verbose:
        print(f"\n[Step 2] Fetching PDB list (method: {method})...")

    pdblist = unidata.pdblist(method)

    if max_structures is not None and len(pdblist) > max_structures:
        pdblist = pdblist[:max_structures]

    if verbose:
        print(f"  Found {len(pdblist)} PDB entries")
        print(f"  Selected: {', '.join(pdblist[:10])}{'...' if len(pdblist) > 10 else ''}")

    # Step 3: PDB データ取得と配列構築
    if verbose:
        print("\n[Step 3] Processing PDB structures...")

    # UniProt 配列を 1 列目として持つ DataFrame
    seqdata = pd.DataFrame(sequence, columns=[uniprotids[0]])
    seqdata.index.name = uniprotids[0]

    nor_pdblist: List[str] = []
    sub_pdblist: List[str] = []
    chi_pdblist: List[str] = []
    din_pdblist: List[str] = []
    excluded_pdbs: List[str] = []

    for i, pdbid in enumerate(pdblist):
        if verbose:
            print(f"  [{i+1}/{len(pdblist)}] Processing {pdbid}...", end=" ")

        try:
            cifdata = CifData(pdbid, pdir=str(pdb_dir))
            mut_judge = cifdata.mutationjudge(uniprotids, pdbid)

            if verbose:
                print(f"[{mut_judge}]")

            # 変異タイプごとに分類
            if mut_judge == "normal":
                nor_pdblist.append(pdbid)
            elif mut_judge == "substitution":
                sub_pdblist.append(pdbid)
            elif mut_judge == "chimera":
                chi_pdblist.append(pdbid)
            elif mut_judge == "delins":
                din_pdblist.append(pdbid)
            else:
                excluded_pdbs.append(pdbid)
                continue

            # 配列情報を取得（Notebook 相当）
            beg, end = unidata.position(pdbid)
            df_beg = pd.DataFrame(index=list(range(beg - 1)))
            df_end = pd.DataFrame(index=list(range(len(sequence) - end)))

            # UniProt に対応した配列（Series or DataFrame を想定）
            raw_seq = cifdata.getsequence(uniprotids)

            # DataFrame 化
            seq = pd.DataFrame(raw_seq)

            # ★重要★: 列名を "pdbid chain" 形式にする
            #
            # 既存 Notebook 版では列ラベルが PDB ID だけだったが、
            # 今回の getcoord() は「列名から pdbid / chain を split() で取り出す」
            # 仕様なので、ここで統一して付けておく。
            #
            # - 単一列の場合: 「その PDB には対象チェーンが 1 本だけ」とみなして
            #                  ダミーで 'A' を付けて "1A00 A" のようにする
            # - 複数列の場合: 元の列名をチェーンラベルとみなして "1A00 <col>" にする
            if len(seq.columns) == 1:
                seq.columns = [f"{pdbid} A"]
            else:
                seq.columns = [f"{pdbid} {col}" for col in seq.columns]

            # 前後のギャップを埋める
            seq = pd.concat([df_beg, seq, df_end])
            seq.reset_index(inplace=True, drop=True)

            # 全体の seqdata に横方向に結合
            seqdata = pd.concat([seqdata, seq], axis=1)

        except Exception as e:
            if verbose:
                print(f"[ERROR: {str(e)}]")
            excluded_pdbs.append(pdbid)
            continue

    total_used = len(nor_pdblist) + len(sub_pdblist) + len(chi_pdblist) + len(din_pdblist)

    if verbose:
        print(f"\n  Summary:")
        print(f"    Normal: {len(nor_pdblist)}")
        print(f"    Substitution: {len(sub_pdblist)}")
        print(f"    Chimera: {len(chi_pdblist)}")
        print(f"    DelIns: {len(din_pdblist)}")
        print(f"    Excluded: {len(excluded_pdbs)}")
        print(f"    Total used: {total_used}/{len(pdblist)}")

    if total_used < 2:
        raise RuntimeError("Less than 2 valid structures. Cannot proceed with analysis.")

    # Step 4: 配列トリミング・アライメント
    if verbose:
        print("\n[Step 4] Sequence trimming and alignment...")

    trimsequence = sort_sequence(uniprotids[0], seqdata, seq_ratio)
    num_chains = len(trimsequence.columns) - 1

    if verbose:
        print(f"  trimsequence columns: {list(trimsequence.columns)}")
        print(f"  Chains after trimming: {num_chains}")

    if num_chains < 2:
        raise RuntimeError("Less than 2 chains after trimming. Cannot proceed.")

    # Step 5: 座標取得
    if verbose:
        print("\n[Step 5] Extracting CA coordinates...")

    atom_coord_dir = str(pdb_dir.parent / "atom_coord") + "/"
    atomcoord = getcoord(trimsequence, atom_coord_dir=atom_coord_dir)

    num_residues = len(atomcoord)
    if verbose:
        print(f"  Residues: {num_residues}")

    # Step 6: 距離計算
    if verbose:
        print("\n[Step 6] Computing distances...")

    distance = getdistance2(atomcoord)

    if verbose:
        print(f"  Computed {len(distance)} residue pairs")

    # Step 7: Score 計算
    if verbose:
        print("\n[Step 7] Computing DSA scores...")

    score = getscore(distance, ddof=0)
    umf = compute_umf(score)
    pair_score_mean, pair_score_std = compute_pair_statistics(score)

    if verbose:
        print(f"  UMF: {umf:.4f}")
        print(f"  Pair score mean: {pair_score_mean:.4f}")
        print(f"  Pair score std: {pair_score_std:.4f}")

    # ★ Distance–Score プロット PNG の保存 ★
    # heatmap_png_path が指定されている場合 → そのディレクトリに distance_score.png を出す
    # （= 今の go-api/storage/<jobId>/heatmap.png と同じ場所）
    if heatmap_png_path is not None:
        plot_dir = Path(heatmap_png_path).parent
    else:
        # それ以外は従来通り output_dir に保存
        plot_dir = output_dir

    if verbose:
        print(f"\n[Step 7.5] Saving distance-score plot...")

    save_distance_score_plot(
        score_df=score,
        output_dir=plot_dir,
        title=uniprot_id,
    )

    if verbose:
        print(f"  Distance-Score plot saved: {plot_dir / 'distance_score.png'}")

    # Step 8: Cis 検出
    if verbose:
        print(f"\n[Step 8] Detecting cis peptide bonds (threshold: {cis_threshold} Å)...")

    cis_dist, cis_info = detect_cis_pairs(distance, cis_threshold=cis_threshold)

    if verbose:
        print(f"  Cis pairs (all structures): {cis_info['cis_num']}")
        print(f"  Mixed cis/trans pairs: {cis_info['mix']}")

    # Step 9: ヒートマップ生成
    if verbose:
        print("\n[Step 9] Generating heatmap...")

    heatmap_array = generate_heatmap(score)
    heatmap_list = heatmap_to_list(heatmap_array)

    # ★ ここで PNG を保存
    if heatmap_png_path is not None:
        if verbose:
            print(f"  Saving heatmap PNG to: {heatmap_png_path}")
        save_heatmap_png(
            heatmap_array,
            Path(heatmap_png_path),
            title=uniprot_id,
        )

    # Step 10: Per-residue スコア計算
    if verbose:
        print("\n[Step 10] Computing per-residue scores...")

    per_residue_array = per_residue_scores_fast(score, num_residues)

    # Step 11: 結果の構築
    if verbose:
        print("\n[Step 11] Building result object...")

    # PairScore リスト
    pair_scores: List[PairScore] = []
    for _, row in score.iterrows():
        # 先頭列（"0, 1" みたいな文字列）から i, j を取り出す
        i, j = map(int, str(row.iloc[0]).split(", "))

        dm = row["distance mean"]
        ds = row["distance std"]
        sc = row["score"]

        # NaN / inf は None にしておく（JSON で null になる）
        def _to_optional_float(x):
            if pd.isna(x):
                return None
            if isinstance(x, (float, int)) and not np.isfinite(x):
                return None
            return float(x)

        pair_scores.append(
            PairScore(
                i=i,
                j=j,
                residue_pair=str(row["residue pair"]),
                distance_mean=_to_optional_float(dm),
                distance_std=_to_optional_float(ds),
                score=_to_optional_float(sc),
            )
        )

    # PerResidueScore リスト
    per_residue_scores: List[PerResidueScore] = []
    # ★ NaN を埋めて string にキャストしておく（Pydantic 側が str を要求）
    uniprot_col = atomcoord.iloc[:, 0].fillna("NA").astype(str)
    for idx, (res_name, res_score) in enumerate(zip(uniprot_col, per_residue_array)):
        per_residue_scores.append(
            PerResidueScore(
                index=idx,
                residue_number=idx + 1,  # 1-based
                residue_name=res_name,
                score=float(res_score) if not pd.isna(res_score) else 0.0,
            )
        )

    # 使用した PDB ID リスト
    used_pdb_ids = nor_pdblist + sub_pdblist + chi_pdblist + din_pdblist

    # 最終結果
    result = NotebookDSAResult(
        uniprot_id=uniprot_id,
        num_structures=len(used_pdb_ids),
        num_residues=num_residues,
        pdb_ids=used_pdb_ids,
        excluded_pdbs=excluded_pdbs,
        seq_ratio=seq_ratio,
        method=method,
        umf=umf,
        pair_score_mean=pair_score_mean,
        pair_score_std=pair_score_std,
        pair_scores=pair_scores,
        per_residue_scores=per_residue_scores,
        heatmap=Heatmap(size=num_residues, values=heatmap_list),
        cis_info=CisInfo(**cis_info),
    )

    if verbose:
        print("\n" + "=" * 80)
        print("Analysis complete!")
        print("=" * 80)

    return result
