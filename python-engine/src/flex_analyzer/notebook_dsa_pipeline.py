"""
Notebook DSA 解析パイプライン - Colabコード完全再現版

Colab Notebook DSA_Cis_250317.ipynb の機能を完全に再現:
- 複数のUniProt IDの処理
- negative_pdbidの除外
- normal/substitution/chimera/delinsの分類と個別処理
- 複数のseqtype（normal, sub, nor+sub）での解析
- ヒートマップの比較表示（normal vs substitution vs all vs difference）
- CSVファイルへの出力（log, score, distance, cis, summary）
- バックアップ機能
- 上書き/追記オプション
"""

from __future__ import annotations

import os
import re
import csv
import shutil
import datetime
import gzip
import warnings
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from mimetypes import guess_type

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # GUIなし環境対応
import matplotlib.pyplot as plt
import seaborn as sns
import pytz

from .uniprot_data import UniprotData, convert_three
from .cif_data import CifData
from .sequence import sort_sequence, getcoord
from .distance import getdistance2
from .score import getscore, getscore_cis, compute_umf, compute_pair_statistics
from .cis import detect_cis_pairs
from .heatmap import generate_heatmap
from .pipelines.dsa_pipeline import save_distance_score_plot

# 定数
PDB_THRESHOLD = 1
CHAIN_THRESHOLD = 3  # 標準偏差を出すため、最低でも3つのChainが必要


def filter_pdb_list(pdblist: List[str], negative_pdbid: str) -> List[str]:
    """
    negative_pdbidに含まれるPDB IDをpdblistから除外

    Args:
        pdblist: PDB IDのリスト
        negative_pdbid: 除外するPDB ID（スペースまたはカンマ区切り）

    Returns:
        フィルタリング後のPDB IDリスト
    """
    if not negative_pdbid or negative_pdbid.strip() == "":
        return pdblist

    # negative_pdbidをスペースまたはカンマで分割
    negative_list = re.split(r"[,\s]+", negative_pdbid.strip())
    # 大文字に変換
    negative_list_upper = [neg.upper() for neg in negative_list]

    # pdblistから除外
    filtered = [item for item in pdblist if item.upper() not in negative_list_upper]

    return filtered


def count_pdb(uniprotid: str, method: str, negative_pdbid: str = "") -> bool:
    """
    PDBエントリ数が閾値以上かチェック

    Args:
        uniprotid: UniProt ID
        method: 構造決定手法（"X-ray", "NMR", "EM"など）
        negative_pdbid: 除外するPDB ID

    Returns:
        PDBエントリ数が閾値以上ならTrue
    """
    unidata = UniprotData(uniprotid)
    # methodの正規化
    if method == "X-ray diffraction":
        method = "X-ray"
    pdblist = unidata.pdblist(method)
    pdblist = filter_pdb_list(pdblist, negative_pdbid)

    return len(pdblist) >= PDB_THRESHOLD


def prep(
    uniprotid: str,
    method: str,
    negative_pdbid: str = "",
    pdb_dir: Path = Path("pdb_files"),
    verbose: bool = True,
) -> Tuple[pd.DataFrame, List[List[str]]]:
    """
    データ準備（Notebookのprep関数を再現）

    Args:
        uniprotid: UniProt ID
        method: 構造決定手法
        negative_pdbid: 除外するPDB ID
        pdb_dir: PDBファイル保存ディレクトリ
        verbose: ログ出力

    Returns:
        (seqdata, all_pdblist)
        - seqdata: 配列データ
        - all_pdblist: [nor_pdblist, sub_pdblist, chi_pdblist, din_pdblist]
    """
    unidata = UniprotData(uniprotid)
    uniprotids = unidata.get_id()
    id_str = str(uniprotids)
    fasta = unidata.fasta()
    sequence = convert_three(fasta)
    seqdata = pd.DataFrame(sequence, columns=[id_str])
    len_seqdata = len(seqdata)

    # methodの正規化
    method_normalized = method
    if method == "X-ray diffraction":
        method_normalized = "X-ray"
    pdblist = unidata.pdblist(method_normalized)
    pdblist = filter_pdb_list(pdblist, negative_pdbid)

    if verbose:
        print(f"  Processing {len(pdblist)} PDB entries ...")

    nor_pdblist: List[str] = []
    sub_pdblist: List[str] = []
    chi_pdblist: List[str] = []
    din_pdblist: List[str] = []

    for n, pdbid in enumerate(pdblist):
        try:
            cifdata = CifData(pdbid, pdir=str(pdb_dir))
            mut_judge = cifdata.mutationjudge(uniprotids, pdbid)

            if verbose:
                print(f" ({n+1}/{len(pdblist)}) judge: {pdbid} {mut_judge}")

            if mut_judge == "normal":
                nor_pdblist.append(pdbid)
            elif mut_judge == "substitution":
                sub_pdblist.append(pdbid)
            elif mut_judge == "chimera":
                chi_pdblist.append(pdbid)
            elif mut_judge == "delins":
                din_pdblist.append(pdbid)
            else:
                continue

            beg, end = unidata.position(pdbid)
            df_beg = pd.DataFrame(index=list(range(beg - 1)))
            df_end = pd.DataFrame(index=list(range(len_seqdata - end)))

            # getsequenceはDataFrameを返す（Notebookコード準拠）
            # 複数チェーンがある場合もDataFrameで返される
            raw_seq = cifdata.getsequence(uniprotids)

            if isinstance(raw_seq, pd.DataFrame) and not raw_seq.empty:
                # DataFrameをそのまま使用（列名は既に "pdbid chain" 形式）
                seq_df = raw_seq.copy()
                seq = pd.concat([df_beg, seq_df, df_end])
                seq.reset_index(inplace=True, drop=True)
                seqdata = pd.concat([seqdata, seq], axis=1)
            elif isinstance(raw_seq, list) and len(raw_seq) > 0:
                # リストの場合はDataFrameに変換（後方互換性）
                seq_df = pd.DataFrame(raw_seq, columns=[f"{pdbid} A"])
                seq = pd.concat([df_beg, seq_df, df_end])
                seq.reset_index(inplace=True, drop=True)
                seqdata = pd.concat([seqdata, seq], axis=1)
            else:
                if verbose:
                    print(f"  WARNING: {pdbid} の配列が取得できませんでした")

        except Exception as e:
            if verbose:
                print(f"  ERROR processing {pdbid}: {e}")
            continue

    all_pdblist = [nor_pdblist, sub_pdblist, chi_pdblist, din_pdblist]

    if verbose:
        total = len(nor_pdblist) + len(sub_pdblist) + len(chi_pdblist) + len(din_pdblist)
        print(
            f" Data Preparation Finished: {total}/{len(pdblist)} PDB entries, "
            f"{len(seqdata.columns)-1} chains as {uniprotid}"
        )
        print(
            f" (Normal PDB: {len(nor_pdblist)}, Substitution PDB: {len(sub_pdblist)}, "
            f"Chimera PDB: {len(chi_pdblist)}, DelIns PDB: {len(din_pdblist)})"
        )

    return seqdata, all_pdblist


def generate_log_content(
    pdbdata: pd.DataFrame,
    len_sequence: int,
    trimsequence: pd.DataFrame,
    score: pd.DataFrame,
    cis_info: List[List[float]],
    umf: Optional[float] = None,
    pair_score_mean: Optional[float] = None,
    pair_score_std: Optional[float] = None,
) -> pd.DataFrame:
    """
    ログコンテンツを生成（元の実装を使用）

    Args:
        pdbdata: PDBデータ
        len_sequence: 配列長
        trimsequence: トリミング後の配列
        score: スコアデータ
        cis_info: cis情報 [[cis_dist_mean, cis_dist_std, cis_score_mean, cis_num, mix]]
        umf: UMF値（元の実装から計算、Noneの場合は計算）
        pair_score_mean: ペアスコア平均（元の実装から計算、Noneの場合は計算）
        pair_score_std: ペアスコア標準偏差（元の実装から計算、Noneの場合は計算）

    Returns:
        ログDataFrame
    """
    if not cis_info or len(cis_info) == 0:
        cis_dist_mean, cis_dist_std, cis_score_mean, cis_num, mix = 0.0, 0.0, 0.0, 0, 0
    else:
        cis_dist_mean, cis_dist_std, cis_score_mean, cis_num, mix = cis_info[0]

    cols = trimsequence.columns.values[1:]
    pdbids = [i.split(" ")[0] for i in cols]

    # 分解能平均値の計算（chainの重複を許可）
    reso_list = []
    for pdbid in pdbids:
        try:
            reso = pdbdata.at["resolution", pdbid]
            reso = "".join(char for char in str(reso) if char.isdigit() or char == ".")
            if reso:
                reso_list.append(float(reso))
        except (KeyError, ValueError):
            continue

    if reso_list:
        reso_ave = Decimal(str(np.mean(reso_list))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        reso_ave = Decimal("0.00")

    # 分解能平均値の計算（chainの重複を認めない）
    seted = sorted(set(pdbids), key=pdbids.index)
    resolution_sum = 0
    count = 0
    for pdbid in seted:
        try:
            resolution = pdbdata.at["resolution", pdbid]
            resolution_sum += float(str(resolution).split(" ")[0])
            count += 1
        except (KeyError, ValueError):
            continue

    # UMFとペアスコア統計が提供されていない場合は計算
    if umf is None:
        umf = compute_umf(score)
    if pair_score_mean is None or pair_score_std is None:
        pair_score_mean, pair_score_std = compute_pair_statistics(score)

    return pd.DataFrame(
        {
            "Entries": [len(seted)],
            "Chains": [len(pdbids)],
            "Length": [len(trimsequence)],
            "Length(%)": [round((len(trimsequence) * 100 / len_sequence), 1)],
            "Resolution": [float(reso_ave)],
            "UMF": [round(umf, 1)],  # 元の実装を使用
            "cis/Length(%)": [round((cis_num * 100 / len(trimsequence)), 2)],
            "mean_cisDist": [round(cis_dist_mean, 2)],
            "std_cisDist": [round(cis_dist_std, 2)],
            "mean_cisScore": [round(cis_score_mean, 2)],
            "cis": [cis_num],
            "mix": [mix],
        }
    )


def run_DSA(
    uniprotid: str,
    seqdata: pd.DataFrame,
    export: bool,
    seqtype: str,
    seq_ratio: float,
    cis_threshold: float,
    pdb_dir: Path = Path("pdb_files"),
    output_dir: Path = Path("output"),
    verbose: bool = True,
    method: str = "X-ray",
) -> Tuple[pd.DataFrame, str]:
    """
    DSA解析を実行（Notebookのrun_DSA関数を再現）

    Args:
        uniprotid: UniProt ID
        seqdata: 配列データ
        export: CSV出力するか
        seqtype: シーケンスタイプ（'normal', 'sub', 'nor+sub'）
        seq_ratio: 配列アライメント閾値
        cis_threshold: cis判定の距離閾値
        pdb_dir: PDBファイル保存ディレクトリ
        output_dir: 出力ディレクトリ
        verbose: ログ出力

    Returns:
        (score, log_output)
    """
    unidata = UniprotData(uniprotid)
    uniprotids = unidata.get_id()
    str_ids = str(uniprotids)

    trimsequence = sort_sequence(str_ids, seqdata, seq_ratio)

    # trimsequenceをCSVに保存
    if export:
        trimsequence.to_csv(output_dir / f"trimsequence_{uniprotid}.csv", index=False)

    trimseqcol = trimsequence.columns.values[1:]

    if len(trimseqcol) > CHAIN_THRESHOLD - 1:
        atom_coord_dir = str(pdb_dir.parent / "atom_coord") + "/"
        atomcoord = getcoord(trimsequence, atom_coord_dir=atom_coord_dir)
        distance = getdistance2(atomcoord)
        score = getscore(distance, ddof=0)

        # 元の実装を使用してUMFとペアスコア統計を計算
        umf = compute_umf(score)
        pair_score_mean, pair_score_std = compute_pair_statistics(score)

        # distance DataFrameをCSVに書き出す
        if export:
            residue_pairs = list(combinations(atomcoord.index, 2))
            residue_num1_list = [pair[0] + 1 for pair in residue_pairs]
            residue_num2_list = [pair[1] + 1 for pair in residue_pairs]
            residue_num_df = pd.DataFrame(
                {"residue_num1": residue_num1_list, "residue_num2": residue_num2_list}
            )
            distance_cols = distance.columns[2:]
            distance_data_df = distance[distance_cols].copy()
            merged_df = pd.concat([residue_num_df, distance_data_df], axis=1)
            merged_df.to_csv(output_dir / f"distance_{uniprotid}.csv", index=False, header=False)

        # cis解析（元の実装を使用）
        cis_dist, cis_info_dict = detect_cis_pairs(distance, cis_threshold=cis_threshold)

        # cis_infoをリスト形式に変換（後方互換性のため）
        if cis_info_dict:
            cis_info = [
                [
                    cis_info_dict["cis_dist_mean"],
                    cis_info_dict["cis_dist_std"],
                    cis_info_dict["cis_score_mean"],
                    cis_info_dict["cis_num"],
                    cis_info_dict["mix"],
                ]
            ]
        else:
            cis_info = [[0, 0, 0, 0, 0]]

        # 解析結果の出力
        fasta = unidata.fasta()
        sequence = convert_three(fasta)
        # pdbdataを取得（まだ取得していない場合）
        if not hasattr(unidata, "pdbdata") or unidata.pdbdata is None:
            unidata.getpdbdata(method)
        # 既に計算済みのumf、pair_score_mean、pair_score_stdを使用
        # （355-357行目で計算済み）
        log = generate_log_content(
            unidata.pdbdata,
            len(sequence),
            trimsequence,
            score,
            cis_info,
            umf=umf,
            pair_score_mean=pair_score_mean,
            pair_score_std=pair_score_std,
        )
        log_output = log.to_string(index=False)

        # Distance–Score Plotを保存（元の実装を使用）
        if export:
            try:
                save_distance_score_plot(
                    score_df=score,
                    output_dir=output_dir,
                    title=uniprotid,
                )
                if verbose:
                    print(f"  Distance-Score plot saved: {output_dir / 'distance_score.png'}")
            except Exception as e:
                if verbose:
                    print(f"  WARNING: Failed to save Distance-Score plot: {e}")

        # 解析結果の保存
        if export:

            def export_to_csv(
                uniprotid: str,
                seq_ratio: float,
                outputdataname: str,
                outputdata: pd.DataFrame,
                seqtype: str,
            ):
                filepath = (
                    output_dir / f"{uniprotid}_{str(seq_ratio)}_{outputdataname}_{seqtype}.csv"
                )
                outputdata.to_csv(filepath, index=False)
                if outputdataname == "log":
                    unidata.pdbdata.to_csv(filepath, mode="a", index=False)
                    trimsequence.to_csv(filepath, mode="a")

            export_to_csv(uniprotid, seq_ratio, "cis", cis_dist, seqtype)

        return score, log_output
    else:
        log = "\n\nLess than 3 chains"
        df_blank = pd.DataFrame()
        return df_blank, log


def generate_comparison_heatmap(
    sc_nor: pd.DataFrame,
    sc_sub: pd.DataFrame,
    sc_all: pd.DataFrame,
    uniprotid: str,
    output_path: Path,
    verbose: bool = True,
) -> None:
    """
    比較ヒートマップを生成（normal vs substitution vs all vs difference）
    元の実装（heatmap.py）を使用して2x2グリッド形式で表示

    Args:
        sc_nor: normalスコア
        sc_sub: substitutionスコア
        sc_all: allスコア
        uniprotid: UniProt ID
        output_path: 出力パス
        verbose: ログ出力
    """
    from .heatmap import generate_heatmap

    # 元の実装を使用してヒートマップ配列を生成
    hm_nor = generate_heatmap(sc_nor)
    hm_sub = generate_heatmap(sc_sub)
    hm_all = generate_heatmap(sc_all)
    hm_dif = hm_sub - hm_nor

    # 2x2グリッドで表示
    import matplotlib

    matplotlib.use("Agg")  # GUIなし環境対応
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig, axes = plt.subplots(2, 2, figsize=(12, 12), sharex=True, sharey=True, tight_layout=True)
    fig.suptitle(uniprotid, fontsize=16, y=0.995)

    axes[0, 0].set_title("normal", fontsize=12)
    axes[0, 1].set_title("substitution", fontsize=12)
    axes[1, 0].set_title("normal&substitution", fontsize=12)
    axes[1, 1].set_title("substitution-normal", fontsize=12)

    # スケールを自動調整（有効な値の1%と99%パーセンタイルを使用）
    def get_auto_scale(hm: np.ndarray) -> tuple[float, float]:
        valid_values = hm[~np.isnan(hm)]
        if len(valid_values) == 0:
            return 0.0, 100.0
        vmin = float(np.nanpercentile(valid_values, 1))
        vmax = float(np.nanpercentile(valid_values, 99))
        return vmin, vmax

    # normal
    vmin_nor, vmax_nor = get_auto_scale(hm_nor)
    sns.heatmap(
        hm_nor,
        vmax=vmax_nor,
        vmin=vmin_nor,
        square=True,
        cmap="rainbow_r",
        cbar=True,
        ax=axes[0, 0],
        cbar_kws={"shrink": 0.8},
        mask=np.isnan(hm_nor),
    )

    # substitution
    vmin_sub, vmax_sub = get_auto_scale(hm_sub)
    sns.heatmap(
        hm_sub,
        vmax=vmax_sub,
        vmin=vmin_sub,
        square=True,
        cmap="rainbow_r",
        cbar=True,
        ax=axes[0, 1],
        cbar_kws={"shrink": 0.8},
        mask=np.isnan(hm_sub),
    )

    # normal&substitution
    vmin_all, vmax_all = get_auto_scale(hm_all)
    sns.heatmap(
        hm_all,
        vmax=vmax_all,
        vmin=vmin_all,
        square=True,
        cmap="rainbow_r",
        cbar=True,
        ax=axes[1, 0],
        cbar_kws={"shrink": 0.8},
        mask=np.isnan(hm_all),
    )

    # substitution-normal (差分、発散型カラーマップ)
    vmin_dif, vmax_dif = get_auto_scale(hm_dif)
    # 差分の場合は対称的な範囲を使用
    abs_max = max(abs(vmin_dif), abs(vmax_dif))
    sns.heatmap(
        hm_dif,
        square=True,
        vmax=abs_max,
        vmin=-abs_max,
        center=0,
        cmap="RdBu_r",  # 発散型カラーマップ（赤-白-青）
        cbar=True,
        ax=axes[1, 1],
        cbar_kws={"shrink": 0.8},
        mask=np.isnan(hm_dif),
    )

    # 軸ラベルの設定（画像に合わせて）
    max_res = max(hm_nor.shape[0], hm_sub.shape[0], hm_all.shape[0])
    if max_res > 0:
        # Y軸（左側）: 横書き、18刻み
        tick_positions_y = list(range(0, max_res, max(1, max_res // 10)))
        tick_labels_y = [str(i) for i in tick_positions_y]
        for ax in axes[:, 0]:
            ax.set_yticks(tick_positions_y)
            ax.set_yticklabels(tick_labels_y, rotation=0, fontsize=8)

        # X軸（下側）: 縦書き、3刻み程度
        tick_positions_x = list(range(0, max_res, max(1, max_res // 10)))
        tick_labels_x = [str(i) for i in tick_positions_x]
        for ax in axes[1, :]:
            ax.set_xticks(tick_positions_x)
            ax.set_xticklabels(tick_labels_x, rotation=90, fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, format="png", dpi=300, bbox_inches="tight")
    if verbose:
        print(f"  Comparison heatmap saved: {output_path}")
    plt.close()


def run_notebook_dsa_analysis(
    uniprot_ids: str,
    method: str = "X-ray",
    seq_ratio: float = 0.2,
    negative_pdbid: str = "",
    export: bool = True,
    heatmap: bool = True,
    verbose: bool = True,
    proc_cis: bool = True,
    cis_threshold: float = 3.3,
    overwrite: bool = True,
    output_dir: Path = Path("output"),
    pdb_dir: Path = Path("pdb_files"),
) -> None:
    """
    Notebook DSA解析のメイン関数（Colabコードを完全再現）

    Args:
        uniprot_ids: UniProt ID（カンマまたはスペース区切り）
        method: 構造決定手法
        seq_ratio: 配列アライメント閾値
        negative_pdbid: 除外するPDB ID
        export: CSV出力するか
        heatmap: ヒートマップを生成するか
        verbose: ログ出力
        proc_cis: cis解析を行うか
        cis_threshold: cis判定の距離閾値
        overwrite: 上書きするか
        output_dir: 出力ディレクトリ
        pdb_dir: PDBファイル保存ディレクトリ
    """
    # 出力ディレクトリ設定
    output_dir.mkdir(parents=True, exist_ok=True)

    # エラーファイル設定
    errfilename = output_dir / "error.txt"
    filename = output_dir / "summary.csv"

    # フィールド名
    fieldnames = [
        "uniprotid",
        "seq_ratio",
        "fullName",
        "organism",
        "Entries",
        "Chains",
        "Length",
        "Length(%)",
        "Resolution",
        "UMF",
        "cis/Length(%)",
        "mean_cisDist",
        "std_cisDist",
        "mean_cisScore",
        "cis",
        "mix",
    ]

    # 既存データの読み込み
    existing_data = []
    if filename.exists():
        jst = pytz.timezone("Asia/Tokyo")
        timestamp = datetime.datetime.now(jst).strftime("%Y%m%d_%H%M%S")
        backup_filename = output_dir / f"summary_backup_{timestamp}.csv"
        shutil.copy2(filename, backup_filename)
        if verbose:
            print(f"Backup created: {backup_filename}")

        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                existing_data.append(row)
    else:
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    # UniProt IDの分割
    ids = [x.strip() for x in re.split(r"[,\s]+", uniprot_ids.strip())]

    # 各UniProt IDを処理
    for i, uniprotid in enumerate(ids):
        try:
            if verbose:
                print(
                    "#####################################################################################"
                )
                print(f"Processing {uniprotid} ...")

            unidata = UniprotData(uniprotid)
            fullName = unidata.get_fullname()
            organism = unidata.get_organism()

            if verbose:
                print(f"{fullName} from {organism}")
                print("### Preparation #########################################")

            pngfilepath = output_dir / f"{uniprotid}_{str(seq_ratio)}_heatmap.png"
            txtfilepath = output_dir / f"{uniprotid}_{str(seq_ratio)}_summary.txt"

            # methodの正規化
            method_normalized = method
            if method == "X-ray diffraction":
                method_normalized = "X-ray"

            if not count_pdb(uniprotid, method_normalized, negative_pdbid):
                print("Less than 3 PDB entries")
                if verbose:
                    print("###############################################")
                continue

            seqdata, all_pdblist = prep(
                uniprotid, method_normalized, negative_pdbid, pdb_dir, verbose
            )
            seqdata1 = seqdata.filter(like=uniprotid)

            # normal & mutant
            if verbose:
                print("")
                print("### normal & mutant #####################################")

            normal = True
            substitution = True
            seqtype = "nor+sub"
            pdbtuple = tuple(all_pdblist[0] + all_pdblist[1])

            if verbose:
                print(f"PDB: {pdbtuple}")
                print(f"{len(pdbtuple)} entries were processed")

            seqdata2 = seqdata.loc[:, seqdata.columns.str.startswith(tuple(pdbtuple))]
            if verbose:
                print(f"{seqdata2.shape[1]} chains are being processed ...")

            nor_seqdata = pd.concat([seqdata1, seqdata2], axis=1)
            sub_seqdata = pd.concat([seqdata1, seqdata2], axis=1)
            norsub_seqdata = pd.concat([seqdata1, seqdata2], axis=1)

            sc_nor, log_nor = run_DSA(
                uniprotid,
                nor_seqdata,
                export,
                seqtype,
                seq_ratio,
                cis_threshold,
                pdb_dir,
                output_dir,
                verbose,
                method_normalized,
            )
            sc_sub, log_sub = run_DSA(
                uniprotid,
                sub_seqdata,
                export,
                seqtype,
                seq_ratio,
                cis_threshold,
                pdb_dir,
                output_dir,
                verbose,
                method_normalized,
            )
            sc_all, log_all = run_DSA(
                uniprotid,
                norsub_seqdata,
                export,
                seqtype,
                seq_ratio,
                cis_threshold,
                pdb_dir,
                output_dir,
                verbose,
                method_normalized,
            )

            # log_allをパース
            lines = log_all.strip().split("\n")
            if len(lines) == 1:
                continue

            data_log_all_columns = lines[0].split()
            data_log_all = [float(x) if "." in x else int(x) for x in lines[1].split()]
            df_la = pd.DataFrame([data_log_all], columns=data_log_all_columns)

            if verbose:
                print(df_la.to_string(index=False))

            new_data = [
                {
                    "uniprotid": uniprotid,
                    "seq_ratio": seq_ratio,
                    "fullName": fullName,
                    "organism": organism,
                    "Entries": df_la["Entries"][0],
                    "Chains": df_la["Chains"][0],
                    "Length": df_la["Length"][0],
                    "Length(%)": df_la["Length(%)"][0],
                    "Resolution": df_la["Resolution"][0],
                    "UMF": df_la["UMF"][0],
                    "cis/Length(%)": df_la["cis/Length(%)"][0],
                    "mean_cisDist": df_la["mean_cisDist"][0],
                    "std_cisDist": df_la["std_cisDist"][0],
                    "mean_cisScore": df_la["mean_cisScore"][0],
                    "cis": df_la["cis"][0],
                    "mix": df_la["mix"][0],
                }
            ]

            # SUMMARY
            if verbose:
                print("")

            with open(txtfilepath, mode="w") as f:
                print(
                    f"### {uniprotid} (seq_ratio= {seq_ratio}) Summary ######################",
                    file=f,
                )
                print(fullName, file=f)
                print(organism, file=f)
                print(log_all, file=f)

            with open(txtfilepath, mode="r") as f:
                if verbose:
                    print(f.read())

            # まとめCSV
            for new_entry in new_data:
                found = False
                for i, existing_entry in enumerate(existing_data):
                    if new_entry["uniprotid"] == existing_entry["uniprotid"]:
                        if new_entry["seq_ratio"] == float(existing_entry["seq_ratio"]):
                            if overwrite:
                                existing_data[i] = new_entry
                            found = True
                            break
                if not found:
                    existing_data.append(new_entry)

            # ヒートマップ生成
            if heatmap:
                generate_comparison_heatmap(sc_nor, sc_sub, sc_all, uniprotid, pngfilepath, verbose)

            if verbose:
                print(f"Processing {uniprotid} Finished")
                print(
                    "#####################################################################################"
                )
                print("")

        except Exception as e:
            print(f"Error processing {uniprotid}: {e}\n")
            err_message = f"Error processing {uniprotid}: {e}\n"
            with open(errfilename, "a") as err:
                err.write(err_message)
            continue

    # CSVファイルに書き込み（既存データと新規データをマージ）
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # 既存データを書き込み
        for row in existing_data:
            writer.writerow(row)
        # 新規データを書き込み（重複チェック済み）
        # 注意: new_dataは既にexisting_dataにマージされているため、ここでは書き込まない

    if verbose:
        print(f"Update '{filename}'")
        print("Job Completed")
