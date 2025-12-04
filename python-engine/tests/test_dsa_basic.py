# python-engine/tests/test_dsa_basic.py

import numpy as np

from src.flex_analyzer.dsa import (
    compute_dsa_stats,
    dsa_stats_to_dict,
)


def test_dsa_simple_case_umf_and_per_residue():
    """
    距離が [1.0, 2.0, 3.0] の 1 ペアだけを持つ、超シンプルなケース。

    期待値:
        mean = 2.0
        std (ddof=0) = sqrt(((1-2)^2 + (2-2)^2 + (3-2)^2) / 3) = sqrt(2/3)
        score = mean / std
        UMF = score （ペアが1個しかないので）
        per_residue_scores も両残基とも score と同じ
    """
    # K=3構造, N=2残基
    distances = np.array([1.0, 2.0, 3.0], dtype=float)
    K = len(distances)
    N = 2

    coords = np.zeros((K, N, 3), dtype=float)
    for k, d in enumerate(distances):
        coords[k, 0, :] = [0.0, 0.0, 0.0]
        coords[k, 1, :] = [d, 0.0, 0.0]

    stats = compute_dsa_stats(coords)

    # 形状チェック
    assert stats.num_structures == K
    assert stats.num_residues == N

    # 期待される mean / std / score を手計算
    mean = distances.mean()
    var = ((distances - mean) ** 2).mean()  # ddof=0
    std = float(np.sqrt(var))
    expected_score = mean / max(std, 1e-4)

    # UMF は score の平均（＝このケースでは score 自身）
    assert abs(stats.umf - expected_score) < 1e-6

    # per_residue_scores も両方とも同じ score になるはず
    assert len(stats.per_residue_scores) == N
    for s in stats.per_residue_scores:
        assert abs(s - expected_score) < 1e-6


def test_dsa_zero_std_uses_epsilon():
    """
    全構造で距離が同じケース（std=0）でも落ちずに
    std=1e-4 として score を計算しているか確認する。
    """
    distances = np.array([5.0, 5.0, 5.0], dtype=float)
    K = len(distances)
    N = 2

    coords = np.zeros((K, N, 3), dtype=float)
    for k, d in enumerate(distances):
        coords[k, 0, :] = [0.0, 0.0, 0.0]
        coords[k, 1, :] = [d, 0.0, 0.0]

    stats = compute_dsa_stats(coords)

    # std=0 → 1e-4 に置換されている前提
    expected_score = distances[0] / 1e-4
    # UMF はその score（ペア1個だけ）
    assert abs(stats.umf - expected_score) < 1e-3

    # per_residue_scores もその値付近になる
    for s in stats.per_residue_scores:
        assert abs(s - expected_score) < 1e-3


def test_dsa_stats_to_dict_shape_and_keys():
    """
    dsa_stats_to_dict が JSON 化しやすい dict を返しているか確認。
    """
    # 小さめのダミー座標（3構造×4残基）
    K, N = 3, 4
    coords = np.zeros((K, N, 3), dtype=float)
    # 適当にノイズ
    for k in range(K):
        for i in range(N):
            coords[k, i, :] = [i * 3.8, 0.0, 0.0] + np.random.randn(3) * 0.1

    stats = compute_dsa_stats(coords)
    d = dsa_stats_to_dict(stats)

    # 必須キーの存在確認
    for key in [
        "num_structures",
        "num_residues",
        "umf",
        "pair_score_mean",
        "pair_score_std",
        "main_plot_points",
        "per_residue_scores",
        "cis",
    ]:
        assert key in d

    # 型チェックざっくり
    assert d["num_structures"] == K
    assert d["num_residues"] == N
    assert isinstance(d["umf"], float)

    # per_residue_scores 長さ
    prs = d["per_residue_scores"]
    assert isinstance(prs, list)
    assert len(prs) == N

    # main_plot_points は {"mean_distance": float, "score": float} のリスト
    mpp = d["dsa_main_plot"] if "dsa_main_plot" in d else d["main_plot_points"]
    assert isinstance(mpp, list)
    if mpp:
        pt = mpp[0]
        assert "mean_distance" in pt and "score" in pt
