from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Set, Tuple

import numpy as np
import requests
from requests.exceptions import HTTPError

from src.flex_analyzer.parser import extract_ca_coords_from_files
from src.flex_analyzer.models import ResidueData, StructureSet


# UniProt エントリ JSON のエンドポイント
UNIPROT_ENTRY_API = "https://rest.uniprot.org/uniprotkb/{uniprot_id}?format=json"

# PDB ダウンロードURL
RCSB_PDB_DOWNLOAD = "https://files.rcsb.org/download/{pdb_id}.pdb"


# ========= UniProt / PDB 取得まわり =========


def _fetch_uniprot_json(uniprot_id: str) -> dict:
    """単一 UniProt エントリの JSON を取得するヘルパー。"""
    url = UNIPROT_ENTRY_API.format(uniprot_id=uniprot_id)
    print(f"[UniProt] エントリ取得: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _resolve_active_uniprot_id(uniprot_id: str, _visited: Optional[Set[str]] = None) -> str:
    """
    Inactive (DEMERGED) な UniProt ID の場合、
    inactiveReason.mergeDemergeTo を辿って Active な ID を返す。
    """
    if _visited is None:
        _visited = set()
    if uniprot_id in _visited:
        raise RuntimeError(f"UniProt ID のリダイレクトがループしました: {uniprot_id}")
    _visited.add(uniprot_id)

    data = _fetch_uniprot_json(uniprot_id)
    entry_type = data.get("entryType")

    if entry_type == "Inactive":
        inactive_reason = data.get("inactiveReason", {}) or {}
        merge_targets = inactive_reason.get("mergeDemergeTo") or []
        if merge_targets:
            new_id = merge_targets[0]
            print(
                f"  ⚠️ UniProt {uniprot_id} は Inactive (DEMERGED) です。"
                f" 代わりに {new_id} を使います。"
            )
            return _resolve_active_uniprot_id(new_id, _visited=_visited)
        raise RuntimeError(f"UniProt {uniprot_id} は Inactive ですが移行先が不明です。")

    # Active な場合はそのまま
    return uniprot_id


def _fetch_pdb_ids_for_active_uniprot(uniprot_id: str) -> List[str]:
    """
    Active な UniProt ID から PDB ID 一覧を取得する。

    JSON のどこに PDB Cross-Ref が入っているかは
    エントリによって異なるので、複数パターンを見る。
    """
    data = _fetch_uniprot_json(uniprot_id)

    pdb_ids: List[str] = []

    # パターン A: 新しい JSON 構造
    for xref in data.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "PDB" and xref.get("id"):
            pdb_ids.append(xref["id"].upper())

    # パターン B: 古い JSON 構造
    for xref in data.get("dbReferences", []):
        if xref.get("type") == "PDB" and xref.get("id"):
            pdb_ids.append(xref["id"].upper())

    pdb_ids = sorted(set(pdb_ids))

    if not pdb_ids:
        print("  [DEBUG] UniProt JSON のトップレベルキー:")
        print("    " + ", ".join(str(k) for k in data.keys()))
        raise RuntimeError(f"UniProt {uniprot_id} に対応する PDB が見つかりませんでした")

    return pdb_ids


def fetch_pdb_ids_from_uniprot(uniprot_id_input: str) -> Tuple[str, List[str]]:
    """
    ユーザー入力の UniProt ID から:
      - Active な UniProt ID を決定し
      - そこから PDB ID 一覧を取得する

    Returns:
        (resolved_uniprot_id, pdb_ids)
    """
    resolved_id = _resolve_active_uniprot_id(uniprot_id_input)
    pdb_ids = _fetch_pdb_ids_for_active_uniprot(resolved_id)
    return resolved_id, pdb_ids


def download_pdb(pdb_id: str, base_dir: Path) -> Optional[Path]:
    """
    単一 PDB を RCSB からダウンロードして保存する。
    すでに存在する場合はダウンロードしない。

    RCSB 側に存在しない（404）場合は None を返してスキップできるようにする。
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    pdb_id = pdb_id.upper()
    out_path = base_dir / f"{pdb_id}.pdb"

    if out_path.exists():
        print(f"  ✓ {pdb_id}.pdb は既に存在します（スキップ）")
        return out_path

    url = RCSB_PDB_DOWNLOAD.format(pdb_id=pdb_id)
    print(f"  ↓ {pdb_id}.pdb をダウンロード: {url}")

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 404:
            print(f"  ⚠️ {pdb_id}.pdb は RCSB に存在しないためスキップします (404)")
            return None
        resp.raise_for_status()
    except HTTPError as e:
        # その他のHTTPエラーはとりあえずそのまま投げる
        raise

    out_path.write_bytes(resp.content)
    return out_path


# ========= 残基数ミスマッチ除外まわり =========


def _extract_coords_with_filtering(
    pdb_paths: List[Path],
) -> Tuple[np.ndarray, list, List[Path], List[Path]]:
    """
    extract_ca_coords_from_files を使いつつ、
    「残基数が合わない PDB を自動で除外」しながら最終的に
    きれいな coords_all, residues_info を返すヘルパー。

    Returns:
        coords_all: np.ndarray (M_total, N, 3)
        residues_info: List[Tuple[res_num, res_name]]
        used_paths: 実際に使った PDB ファイルの Path リスト
        removed_paths: 残基数不一致で除外された PDB ファイルの Path リスト
    """
    remaining = list(pdb_paths)
    removed: List[Path] = []

    while True:
        try:
            coords_all, residues_info = extract_ca_coords_from_files([str(p) for p in remaining])
            if removed:
                print(
                    f"\n[Info] 部分配列などで除外された PDB: "
                    f"{', '.join(p.name for p in removed)}"
                )
            return coords_all, residues_info, remaining, removed

        except ValueError as e:
            msg = str(e)
            if "Residue count mismatch" not in msg:
                # 想定外のエラーはそのまま投げる
                raise

            bad: Optional[Path] = None
            for p in remaining:
                if str(p) in msg or p.name in msg:
                    bad = p
                    break

            if bad is None:
                # 特定できないならあきらめて上に投げる
                raise

            print(f"  ⚠️ {bad.name} は残基数が異なるため除外します: {msg}")
            remaining.remove(bad)
            removed.append(bad)

            if len(remaining) < 2:
                raise RuntimeError(
                    "フルレングス構造が十分に残らなかったため、解析を継続できません。"
                )


def _build_residue_data(residues_info) -> List[ResidueData]:
    """
    extract_ca_coords_from_files が返す residues_info から ResidueData のリストを構築する。

    residues_info の想定: List[Tuple[int, str]] = (res_num, res_name)
    """
    residues: List[ResidueData] = []
    for idx, (res_num, res_name) in enumerate(residues_info):
        residues.append(
            ResidueData(
                index=idx,
                residue_number=int(res_num),
                residue_name=str(res_name),
                flex_score=0.0,
                dsa_score=0.0,
            )
        )
    return residues


# ========= 公開API: StructureSetを作る =========


def build_structure_set_from_uniprot(
    uniprot_id: str,
    max_structures: int = 20,
    base_dir: Path = Path("data"),
) -> StructureSet:
    """
    UniProt ID から:
      - Active UniProt ID 解決
      - PDB ID 取得
      - PDB ダウンロード
      - 残基数ミスマッチ & 404 PDB を除外
      - ResidueData リスト構築
    までを行い、StructureSet として返す。

    Args:
        uniprot_id: ユーザーが入力する UniProt ID（InactiveでもOK）
        max_structures: 解析に使う最大PDB数（デフォルト20）
        base_dir: PDBを保存する基準ディレクトリ

    Returns:
        StructureSet オブジェクト
    """
    print("=" * 60)
    print(f"🔍 UniProt ID: {uniprot_id} の構造を自動取得して準備します")
    print("=" * 60)

    # 1) Active ID & PDB ID 一覧取得
    resolved_id, all_pdb_ids = fetch_pdb_ids_from_uniprot(uniprot_id)
    print(f"見つかった PDB ID: {len(all_pdb_ids)} 個")
    print("  " + ", ".join(all_pdb_ids[:20]) + (" ..." if len(all_pdb_ids) > 20 else ""))

    # 2) max_structures を適用
    if max_structures is not None:
        selected_pdb_ids = all_pdb_ids[:max_structures]
    else:
        selected_pdb_ids = all_pdb_ids

    print(f"\n解析候補 PDB ID（最大 {max_structures} 個）:")
    print("  " + ", ".join(selected_pdb_ids))

    # 3) PDB ダウンロード（キャッシュ利用）
    #    ディレクトリ名は「入力された UniProt ID」にぶら下げる（既存仕様と合わせる）
    data_dir = base_dir / uniprot_id
    pdb_paths: List[Path] = []
    for pid in selected_pdb_ids:
        path = download_pdb(pid, data_dir)
        if path is not None:
            pdb_paths.append(path)

    print(f"\nダウンロード済み PDB ファイル数: {len(pdb_paths)}")

    if not pdb_paths:
        raise RuntimeError("有効な PDB ファイルを1つも取得できなかったため、解析を継続できません。")

    # 4) 残基数ミスマッチPDBを自動で除外しながら Cα 座標と残基情報を取得
    coords_all, residues_info, used_paths, removed_paths = _extract_coords_with_filtering(pdb_paths)

    used_pdb_ids = [p.stem.upper() for p in used_paths]
    excluded_pdb_ids = [p.stem.upper() for p in removed_paths]

    print(f"\n最終的に解析に使用する PDB ID ({len(used_pdb_ids)} 個):")
    print("  " + ", ".join(used_pdb_ids))

    # 5) ResidueData の構築
    residues = _build_residue_data(residues_info)

    # 6) StructureSet を構築して返す
    chain_ids = ["A"] * len(used_pdb_ids)  # とりあえず全部 A チェーン想定

    structure_set = StructureSet(
        uniprot_id_input=uniprot_id,
        uniprot_id_resolved=resolved_id,
        coords=coords_all,
        residues=residues,
        pdb_ids=used_pdb_ids,
        chain_ids=chain_ids,
        source="uniprot_pdb",
        excluded_pdbs=excluded_pdb_ids,
    )

    return structure_set
