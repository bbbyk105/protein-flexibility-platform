"""mmCIF データ処理モジュール - Notebook DSA_Cis_250317.ipynb 準拠"""

import os
import gzip
import pandas as pd
from pathlib import Path
from Bio.PDB import PDBList
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from typing import List, Tuple
from mimetypes import guess_type


# PDB ダウンロード用
pdb_list = PDBList()


def downloadpdb(pdbid: str, pdir: str = "pdb_files/"):
    """
    PDB ファイルをダウンロード

    Args:
        pdbid: PDB ID
        pdir: 保存先ディレクトリ
    """
    pdb_list.retrieve_pdb_file(pdbid, pdir=pdir, file_format="mmCif")


def _open(pdbid: str, pdir: str = "pdb_files/"):
    """
    mmCIF ファイルを開く（gzip 対応）

    Args:
        pdbid: PDB ID
        pdir: ファイルディレクトリ

    Returns:
        file handle
    """
    file = pdbid.lower() + ".cif"
    ciffile = os.path.join(pdir, file)

    if guess_type(file)[1] == "gzip":
        return gzip.open(ciffile, mode="rt")
    else:
        return open(ciffile)


class CifData:
    """
    mmCIF ファイルを解析し、配列情報を取得

    Notebook の行 204-406 を再現
    """

    def __init__(self, pdbid: str, pdir: str = "pdb_files/"):
        """
        PDB ID から mmCIF ファイルをダウンロード・解析

        Args:
            pdbid: PDB ID
            pdir: ファイル保存ディレクトリ
        """
        self.pdbid = pdbid
        self.pdir = pdir

        # PDB ファイルをダウンロード
        downloadpdb(self.pdbid, pdir=self.pdir)

        # mmCIF を解析
        with _open(self.pdbid, pdir=self.pdir) as handle:
            mmcifdict = MMCIF2Dict(handle)

        # struct_ref_seq の解析
        self.struct_ref_seq = pd.DataFrame(
            {
                "strand_id": mmcifdict["_struct_ref_seq.pdbx_strand_id"],
                "accession": [i.upper() for i in mmcifdict["_struct_ref_seq.pdbx_db_accession"]],
                "seq_align_beg": mmcifdict["_struct_ref_seq.seq_align_beg"],
                "seq_align_end": mmcifdict["_struct_ref_seq.seq_align_end"],
            }
        )

        pdb_strand_id = mmcifdict["_pdbx_poly_seq_scheme.pdb_strand_id"]
        for i, struct_strand_id in enumerate(self.struct_ref_seq["strand_id"]):
            self.struct_ref_seq.at[i, "sort_index"] = pdb_strand_id.index(struct_strand_id)

        self.struct_ref_seq.sort_values("sort_index", inplace=True)

        # struct_ref_seq_dif の解析（変異情報）
        try:
            self.struct_ref_seq_dif = pd.DataFrame(
                {
                    "strand_id": mmcifdict["_struct_ref_seq_dif.pdbx_pdb_strand_id"],
                    "seq_num": mmcifdict["_struct_ref_seq_dif.pdbx_auth_seq_num"],
                    "db_seq_num": mmcifdict["_struct_ref_seq_dif.pdbx_seq_db_seq_num"],
                    "details": [i.lower() for i in mmcifdict["_struct_ref_seq_dif.details"]],
                }
            )

            # 不要な details を除外
            self.struct_ref_seq_dif = self.struct_ref_seq_dif[
                ~self.struct_ref_seq_dif["details"].isin(
                    ["expression tag", "linker", "conflict", "microgeterogeneity"]
                )
            ]
        except KeyError:
            # 変異情報がない場合
            self.struct_ref_seq_dif = pd.DataFrame(
                {"strand_id": [], "seq_num": [], "db_seq_num": []}
            )

        # Chain 情報の解析
        self.chain = []
        self.chainid = []
        self.hetero_info = []
        self.ind = -1
        hetero_pdb_seq_num = ""

        for pdb_mon_id, pdb_seq_num, hetero, chainid in zip(
            mmcifdict["_pdbx_poly_seq_scheme.pdb_mon_id"],
            mmcifdict["_pdbx_poly_seq_scheme.pdb_seq_num"],
            mmcifdict["_pdbx_poly_seq_scheme.hetero"],
            mmcifdict["_pdbx_poly_seq_scheme.pdb_strand_id"],
        ):
            self.ind += 1

            if hetero == "n":
                hetero_pdb_seq_num = ""
                if pdb_mon_id != "?":
                    self.chain.append(pdb_mon_id + ", " + pdb_seq_num)
                    self.chainid.append(chainid)
                else:
                    self.chain.append(None)
                    self.chainid.append(chainid)
            else:
                if pdb_seq_num == hetero_pdb_seq_num:
                    self.hetero_info.append(self.ind)
                    continue
                else:
                    if pdb_mon_id != "?":
                        self.chain.append(pdb_mon_id + ", " + pdb_seq_num)
                        self.chainid.append(chainid)
                        hetero_pdb_seq_num = pdb_seq_num
                    else:
                        self.chain.append(None)
                        self.chainid.append(chainid)

        # sort_index の更新
        for j, strandid in enumerate(self.struct_ref_seq["strand_id"]):
            self.struct_ref_seq.at[j, "sort_index"] = self.chainid.index(strandid)

        # 原子座標の解析
        atom_coord = pd.DataFrame(
            {
                "model_num": mmcifdict["_atom_site.pdbx_PDB_model_num"],
                "asym_id": mmcifdict["_atom_site.auth_asym_id"],
                "comp_id": mmcifdict["_atom_site.auth_comp_id"],
                "seq_id": mmcifdict["_atom_site.auth_seq_id"],
                "atom_id": mmcifdict["_atom_site.auth_atom_id"],
                "Cartn_x": mmcifdict["_atom_site.Cartn_x"],
                "Cartn_y": mmcifdict["_atom_site.Cartn_y"],
                "Cartn_z": mmcifdict["_atom_site.Cartn_z"],
                "alt_id": mmcifdict["_atom_site.label_alt_id"],
                "group_PDB": mmcifdict["_atom_site.group_PDB"],
                "ins_code": mmcifdict["_atom_site.pdbx_PDB_ins_code"],
            }
        )

        atom_coord["asym_id"] = atom_coord["asym_id"].astype(str)

        # alt_id の処理（重複除去）
        atom_coord["original_index"] = atom_coord.index
        alt_id_dot = atom_coord[atom_coord["alt_id"].str.contains("\\.")]
        alt_id_not_dot = atom_coord[~atom_coord["alt_id"].str.contains("\\.")]
        alt_id_not_dot_unique = alt_id_not_dot.drop_duplicates(subset=["seq_id", "atom_id"])

        atom_coord = pd.concat([alt_id_dot, alt_id_not_dot_unique])
        atom_coord = atom_coord.sort_values("original_index")
        atom_coord = atom_coord.drop(columns=["original_index"])
        atom_coord = atom_coord[(atom_coord["group_PDB"] == "ATOM")].drop(
            columns=["alt_id", "group_PDB"]
        )

        # 原子座標を CSV に保存
        atom_coord_dir = os.path.join(self.pdir, "../atom_coord/")
        if not os.path.exists(atom_coord_dir):
            os.makedirs(atom_coord_dir)

        atom_coord.to_csv(os.path.join(atom_coord_dir, f"{self.pdbid}.csv"), index=False)

    def mutationjudge(self, uniprotids: List[str], pdbid: str) -> str:
        """
        変異判定（normal / substitution / chimera / delins）

        Notebook の行 304-344 を再現

        Args:
            uniprotids: UniProt ID のリスト
            pdbid: PDB ID

        Returns:
            変異タイプ: "normal" | "substitution" | "chimera" | "delins" | "UniProt ID mismatch"
        """
        # PDB に含まれる全 Chain の UniProt ID 情報
        m_pd = self.struct_ref_seq[["strand_id", "accession"]]

        # 入力 UniProt ID と一致した Chain のみ抽出
        unim_pd = m_pd[m_pd["accession"].isin(uniprotids)]

        # 一致した Chain がない場合
        if unim_pd["accession"].count() == 0:
            print(f"{uniprotids} not matched. UniProt ID(s) in this PDB is listed below")
            exunim_pd = m_pd[m_pd["accession"] != (uniprotids and pdbid)]
            print(exunim_pd["accession"].unique())
            return "UniProt ID mismatch"

        # Chimera 判定（同じ Chain に複数回同じ UniProt ID が登場）
        if unim_pd.duplicated().sum() != 0:
            return "chimera"

        m_id = list(unim_pd["strand_id"])  # 一致した Chain 番号

        # 変異情報を取得
        mdif_pd = self.struct_ref_seq_dif[self.struct_ref_seq_dif["strand_id"].isin(m_id)]

        # 変異情報がなければ normal
        if len(mdif_pd) == 0:
            return "normal"

        # 変異の種類を確認
        mdif_pd_details = mdif_pd["details"].unique()

        if "engineered mutation" in mdif_pd_details:
            print("engineered mutation")
            return "substitution"
        elif "microheterogeneity" in mdif_pd_details:
            print("microheterogeneity")
            return "normal"

        # Chimera 判定（Chain 重複）
        s_list = list(m_pd["strand_id"])
        if len(s_list) != len(set(s_list)):
            return "chimera"

        # Delins 判定
        for i in m_id:
            strand_mdif_pd = mdif_pd[mdif_pd["strand_id"] == i]
            seq_num_list = list(strand_mdif_pd["seq_num"])
            db_seq_num_list = list(strand_mdif_pd["db_seq_num"])

            if len(seq_num_list) != len(set(seq_num_list)):
                return "delins"
            elif len(db_seq_num_list) != len(set(db_seq_num_list)):
                return "delins"

        return "substitution"

    def getsequence(self, uniprotids: List[str]) -> List:
        """
        配列情報の取得

        Notebook の行 347-406 を再現

        Args:
            uniprotids: UniProt ID のリスト

        Returns:
            chain リスト（pdb_mon_id + ", " + pdb_seq_num の形式）
        """
        firstLoop = True
        struct = self.struct_ref_seq[
            self.struct_ref_seq["accession"].isin(uniprotids)
        ].drop_duplicates(subset=["strand_id"])

        for row in struct.itertuples():
            if row.accession in uniprotids:
                sort_index = int(row.sort_index)
                align_beg = sort_index + int(row.seq_align_beg) - 1
                align_end = sort_index + int(row.seq_align_end)
                chain = self.chain[align_beg:align_end]

                # 変異情報の処理
                mutat_info = self.struct_ref_seq_dif[
                    self.struct_ref_seq_dif["strand_id"] == row.strand_id
                ].drop(columns="strand_id")

                if len(mutat_info) != 0:
                    # Deletion の処理
                    deletion = mutat_info[(mutat_info["seq_num"] == "?")].index
                    if len(deletion) != 0:
                        mutat_info.drop(deletion, inplace=True)
                        chain_num = (
                            pd.Series(chain)
                            .map(lambda x: int(x.split(", ")[1]) if isinstance(x, str) else x)
                            .diff()
                        )
                        deletion = chain_num[(chain_num != 1)].dropna()
                        for index, i in zip(deletion.index, deletion):
                            chain[index:index] = [None] * int(i)

                    # Insertion の処理
                    insertion = mutat_info[(mutat_info["db_seq_num"] == "?")]["seq_num"]
                    if len(insertion) != 0:
                        mutat_info.drop(insertion.index, inplace=True)
                        insertion = insertion.values.tolist()
                        print(insertion)
                        for i in chain:
                            if isinstance(i, str):
                                for n in insertion:
                                    if n == i.split(", ")[1]:
                                        insertion.remove(n)
                                        chain.remove(i)

                    # Delins の処理（重複）
                    dup_mutat = mutat_info[mutat_info.duplicated(subset=["seq_num"], keep=False)]
                    if len(dup_mutat) != 0:
                        mutat_info.drop(dup_mutat.index, inplace=True)
                        for i in dup_mutat["seq_num"].drop_duplicates():
                            chain_num = pd.Series(chain).map(
                                lambda x: int(x.split(", ")[1]) if isinstance(x, str) else x
                            )
                            num = len(dup_mutat[dup_mutat["seq_num"] == i]) - 1
                            index = chain_num[chain_num == int(i)].index[0] + 1
                            chain[index:index] = [None] * num

                    # Delins の処理（挿入）
                    dup_mutat = mutat_info[mutat_info.duplicated(subset=["db_seq_num"], keep=False)]
                    if len(dup_mutat) != 0:
                        mutat_info.drop(dup_mutat.index, inplace=True)
                        insertion = []
                        for i in dup_mutat["db_seq_num"].drop_duplicates():
                            insertion += (
                                dup_mutat[dup_mutat["db_seq_num"] == i]["seq_num"]
                                .reset_index(drop=True)
                                .drop([0])
                                .values.tolist()
                            )

                        m = 0
                        for i in range(len(chain)):
                            i = chain[i + m]
                            if isinstance(i, str):
                                for n in insertion:
                                    if n == i.split(", ")[1]:
                                        insertion.remove(n)
                                        chain.pop(i + m)
                                        m -= 1
                                        break

                return chain

        return []
