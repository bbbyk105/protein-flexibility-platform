"""高速実装のユニットテスト"""

import numpy as np
import pytest
from flex_analyzer.core import compute_dsa_and_flex_fast
from flex_analyzer.parser import generate_mock_coords


def test_output_shapes():
    """出力の形状が正しいことを確認"""
    ca_coords, _ = generate_mock_coords(num_structures=10, num_residues=30, seed=42)

    dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

    assert dsa_matrix.shape == (30, 30)
    assert std_matrix.shape == (30, 30)
    assert flex_scores.shape == (30,)


def test_non_negative_values():
    """全ての値が非負であることを確認"""
    ca_coords, _ = generate_mock_coords(num_structures=10, num_residues=20, seed=42)

    dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

    assert np.all(dsa_matrix >= 0)
    assert np.all(std_matrix >= 0)
    assert np.all(flex_scores >= 0)


def test_single_structure():
    """単一構造の場合の動作確認"""
    # 1つの構造のみ（揺らぎなし）
    ca_coords, _ = generate_mock_coords(num_structures=1, num_residues=10, noise_scale=0.0, seed=42)

    dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

    # 標準偏差は0に近いはず
    assert np.all(std_matrix < 1e-10)
    # flex_scoresも0に近いはず
    assert np.all(flex_scores < 1e-10)


def test_identical_structures():
    """全て同じ構造の場合"""
    base_coords, _ = generate_mock_coords(
        num_structures=1, num_residues=15, noise_scale=0.0, seed=42
    )

    # 同じ構造を10回繰り返す
    ca_coords = np.repeat(base_coords, 10, axis=0)

    dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

    # 構造が全て同じなので標準偏差は0
    assert np.all(std_matrix < 1e-10)
    assert np.all(flex_scores < 1e-10)


def test_high_flexibility_residue():
    """特定残基の可変性が高い場合"""
    num_structures = 20
    num_residues = 10

    # 基準構造
    base_coords = np.zeros((num_residues, 3))
    base_coords[:, 0] = np.arange(num_residues) * 3.8

    ca_coords = np.zeros((num_structures, num_residues, 3))

    for i in range(num_structures):
        ca_coords[i] = base_coords.copy()
        # 残基5だけ大きく動かす
        ca_coords[i, 5, :] += np.random.randn(3) * 10.0

    dsa_matrix, std_matrix, flex_scores = compute_dsa_and_flex_fast(ca_coords)

    # 残基5のflex_scoreが他より明らかに大きいはず
    assert flex_scores[5] > np.mean(flex_scores) * 2
