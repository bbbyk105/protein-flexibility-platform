"""PDB/mmCIFパーサー"""

import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path
from Bio.PDB import PDBParser, MMCIFParser, Selection


def extract_ca_coords_from_file(
    file_path: str, chain_id: str = "A"
) -> Tuple[np.ndarray, List[Tuple[int, str]]]:
    """
    単一PDBファイルから全MODELのCα座標を抽出

    Args:
        file_path: PDBまたはmmCIFファイルのパス
        chain_id: 対象チェーンID

    Returns:
        (ca_coords, residue_info)
        - ca_coords: 形状 (M, N, 3) のCα座標配列
        - residue_info: [(residue_number, residue_name), ...] のリスト
    """
    file_path = Path(file_path)

    # パーサーの選択
    if file_path.suffix.lower() in [".cif", ".mmcif"]:
        parser = MMCIFParser(QUIET=True)
    else:
        parser = PDBParser(QUIET=True)

    structure = parser.get_structure("protein", str(file_path))

    # 全モデルを取得
    models = list(structure.get_models())
    M = len(models)

    if M == 0:
        raise ValueError(f"No models found in {file_path}")

    # 最初のモデルから残基情報を取得（全モデルで同じ配列を想定）
    first_chain = models[0][chain_id]
    residues = [res for res in first_chain.get_residues() if res.has_id("CA")]
    N = len(residues)

    if N == 0:
        raise ValueError(f"No CA atoms found in chain {chain_id}")

    # 残基情報を保存
    residue_info = [(res.get_id()[1], res.get_resname()) for res in residues]

    # 全モデルのCα座標を抽出
    ca_coords = np.zeros((M, N, 3), dtype=np.float64)

    for model_idx, model in enumerate(models):
        try:
            chain = model[chain_id]
            ca_atoms = [res["CA"] for res in chain.get_residues() if res.has_id("CA")]

            if len(ca_atoms) != N:
                raise ValueError(
                    f"Model {model_idx} has {len(ca_atoms)} CA atoms, " f"expected {N}"
                )

            for res_idx, ca_atom in enumerate(ca_atoms):
                ca_coords[model_idx, res_idx, :] = ca_atom.get_coord()

        except Exception as e:
            raise ValueError(f"Error processing model {model_idx}: {e}")

    return ca_coords, residue_info


def extract_ca_coords_from_files(
    file_paths: List[str], chain_id: str = "A"
) -> Tuple[np.ndarray, List[Tuple[int, str]]]:
    """
    複数PDBファイルからCα座標を抽出して結合

    各ファイルが複数MODELを含む場合、それらも展開する。

    Args:
        file_paths: PDB/mmCIFファイルパスのリスト
        chain_id: 対象チェーンID

    Returns:
        (ca_coords, residue_info)
        - ca_coords: 形状 (M, N, 3) のCα座標配列（全ファイルの全MODEL）
        - residue_info: 最初のファイルから取得した残基情報
    """
    all_coords = []
    residue_info = None
    expected_n = None

    for file_path in file_paths:
        coords, res_info = extract_ca_coords_from_file(file_path, chain_id)

        if residue_info is None:
            residue_info = res_info
            expected_n = coords.shape[1]
        else:
            # 全ファイルで残基数が一致することを確認
            if coords.shape[1] != expected_n:
                raise ValueError(
                    f"Residue count mismatch: {file_path} has {coords.shape[1]} "
                    f"residues, expected {expected_n}"
                )

        all_coords.append(coords)

    # 全構造を結合
    combined_coords = np.concatenate(all_coords, axis=0)

    return combined_coords, residue_info


def generate_mock_coords(
    num_structures: int = 10,
    num_residues: int = 50,
    noise_scale: float = 2.0,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, List[Tuple[int, str]]]:
    """
    テスト用のモックCα座標を生成

    Args:
        num_structures: 構造数
        num_residues: 残基数
        noise_scale: 揺らぎの大きさ（Å）
        seed: 乱数シード

    Returns:
        (ca_coords, residue_info)
    """
    if seed is not None:
        np.random.seed(seed)

    # 基準構造（直線状の配列）
    base_coords = np.zeros((num_residues, 3), dtype=np.float64)
    base_coords[:, 0] = np.arange(num_residues) * 3.8  # C-C結合距離程度

    # 揺らぎを追加
    ca_coords = np.zeros((num_structures, num_residues, 3), dtype=np.float64)
    for i in range(num_structures):
        noise = np.random.randn(num_residues, 3) * noise_scale
        ca_coords[i] = base_coords + noise

    # ダミーの残基情報
    residue_info = [(i + 1, "ALA") for i in range(num_residues)]

    return ca_coords, residue_info
