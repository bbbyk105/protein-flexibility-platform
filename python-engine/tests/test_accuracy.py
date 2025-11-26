"""高速版と参照版の一致検証テスト"""

import numpy as np
import pytest
from flex_analyzer.core import compute_dsa_and_flex_fast
from flex_analyzer.reference import compute_dsa_and_flex_reference
from flex_analyzer.parser import generate_mock_coords


def test_fast_vs_reference_small():
    """小規模データで高速版と参照版が一致することを確認"""
    # 小規模なモックデータ
    ca_coords, _ = generate_mock_coords(num_structures=5, num_residues=10, noise_scale=1.0, seed=42)

    # 両方の実装で計算
    dsa_fast, std_fast, flex_fast = compute_dsa_and_flex_fast(ca_coords)
    dsa_ref, std_ref, flex_ref = compute_dsa_and_flex_reference(ca_coords)

    # 数値誤差を考慮した一致確認
    np.testing.assert_allclose(dsa_fast, dsa_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(std_fast, std_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(flex_fast, flex_ref, rtol=1e-10, atol=1e-12)


def test_fast_vs_reference_medium():
    """中規模データで高速版と参照版が一致することを確認"""
    ca_coords, _ = generate_mock_coords(
        num_structures=20, num_residues=50, noise_scale=2.0, seed=123
    )

    dsa_fast, std_fast, flex_fast = compute_dsa_and_flex_fast(ca_coords)
    dsa_ref, std_ref, flex_ref = compute_dsa_and_flex_reference(ca_coords)

    np.testing.assert_allclose(dsa_fast, dsa_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(std_fast, std_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(flex_fast, flex_ref, rtol=1e-10, atol=1e-12)


def test_symmetry():
    """距離行列の対称性を確認"""
    ca_coords, _ = generate_mock_coords(num_structures=10, num_residues=30, seed=999)

    dsa_fast, std_fast, _ = compute_dsa_and_flex_fast(ca_coords)

    # 対称行列であることを確認
    np.testing.assert_allclose(dsa_fast, dsa_fast.T, rtol=1e-10)
    np.testing.assert_allclose(std_fast, std_fast.T, rtol=1e-10)


def test_diagonal_is_zero():
    """対角成分が0であることを確認"""
    ca_coords, _ = generate_mock_coords(num_structures=10, num_residues=20, seed=777)

    dsa_fast, std_fast, _ = compute_dsa_and_flex_fast(ca_coords)

    np.testing.assert_array_equal(np.diag(dsa_fast), np.zeros(20))
    np.testing.assert_array_equal(np.diag(std_fast), np.zeros(20))


@pytest.mark.parametrize(
    "num_structures,num_residues",
    [
        (3, 15),
        (10, 25),
        (15, 40),
    ],
)
def test_various_sizes(num_structures, num_residues):
    """様々なサイズで一致を確認"""
    ca_coords, _ = generate_mock_coords(
        num_structures=num_structures, num_residues=num_residues, seed=42
    )

    dsa_fast, std_fast, flex_fast = compute_dsa_and_flex_fast(ca_coords)
    dsa_ref, std_ref, flex_ref = compute_dsa_and_flex_reference(ca_coords)

    np.testing.assert_allclose(dsa_fast, dsa_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(std_fast, std_ref, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(flex_fast, flex_ref, rtol=1e-10, atol=1e-12)
