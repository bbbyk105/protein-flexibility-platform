# heatmap.py

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd


def generate_heatmap(score: pd.DataFrame) -> np.ndarray:
    """
    Score DataFrame から N×N ヒートマップを生成（Notebook 相当）
    """
    ij = score.iloc[:, 0].str.split(", ", expand=True).astype(int)
    ij_arr = ij.to_numpy()
    n_residues = int(ij_arr.max())

    heatmap = np.full((n_residues, n_residues), np.nan, dtype=float)

    if "score" in score.columns:
        values = score["score"].to_numpy()
    else:
        values = score.iloc[:, 4].to_numpy()

    for (i, j), s in zip(ij_arr, values):
        i0, j0 = i - 1, j - 1
        heatmap[i0, j0] = s
        # 対称にしたければ下も埋める:
        # heatmap[j0, i0] = s

    return heatmap


def heatmap_to_list(heatmap: np.ndarray) -> List[List[Optional[float]]]:
    """
    NumPy 配列を JSON 用の 2 次元リストに変換（NaN は None）
    """
    result: List[List[Optional[float]]] = []
    for row in heatmap:
        result.append([None if np.isnan(v) else float(v) for v in row])
    return result


def save_heatmap_png(
    heatmap: np.ndarray,
    out_path: Path,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
) -> None:
    """
    ヒートマップ配列から PNG を保存するヘルパー

    - vmin/vmaxが指定されていない場合、データから自動計算
    - NaN は白抜き
    """
    import matplotlib.pyplot as plt  # 遅延 import

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 有効な値（NaNでない値）を取得
    valid_values = heatmap[~np.isnan(heatmap)]

    if len(valid_values) == 0:
        # データがない場合はデフォルト値を使用
        if vmin is None:
            vmin = 0.0
        if vmax is None:
            vmax = 100.0
    else:
        # 自動調整: 1%と99%パーセンタイルを使用して外れ値を除外
        if vmin is None:
            vmin = float(np.nanpercentile(valid_values, 1))
        if vmax is None:
            vmax = float(np.nanpercentile(valid_values, 99))

    hm_vis = np.where(np.isnan(heatmap), np.nan, np.clip(heatmap, vmin, vmax))

    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)
    im = ax.imshow(
        hm_vis,
        vmin=vmin,
        vmax=vmax,
        cmap="rainbow_r",  # Notebook と同じ
        origin="lower",
        aspect="auto",
    )
    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Score", fontsize=12)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", transparent=True, dpi=300)
    plt.close(fig)
