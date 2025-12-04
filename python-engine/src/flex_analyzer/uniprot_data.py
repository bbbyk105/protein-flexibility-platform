"""UniProt データ取得モジュール - Notebook DSA_Cis_250317.ipynb 準拠"""

import requests
import pandas as pd
from lxml import etree
from typing import List, Tuple, Optional


class UniprotData:
    """
    UniProt XML データにアクセスし、情報を取得

    Notebook の行 94-185 を再現 + 自動リダイレクト機能
    """

    def __init__(self, uniprot_id: str, auto_redirect: bool = True):
        """
        UniProt ID から XML データを取得（自動リダイレクト対応）

        Args:
            uniprot_id: UniProt accession ID
            auto_redirect: Inactive/Obsolete ID を自動的にリダイレクトするか
        """
        self.original_id = uniprot_id
        self.resolved_id = uniprot_id
        self.is_redirected = False

        # まず REST API で状態を確認
        if auto_redirect:
            resolved = self._check_and_resolve(uniprot_id)
            if resolved != uniprot_id:
                self.resolved_id = resolved
                self.is_redirected = True
                print(
                    f"  ⚠️ UniProt {uniprot_id} は Inactive (DEMERGED) です。代わりに {resolved} を使います。"
                )

        # XML データを取得
        url = f"https://www.uniprot.org/uniprot/{self.resolved_id}.xml"

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        self.xml = etree.fromstring(response.content)
        self.nsmap = self.xml.nsmap

        # XML が正しく取得できたか確認
        entry = self.xml.find("./entry", self.nsmap)
        if entry is None:
            raise KeyError(f"No entry found in UniProt XML for {self.resolved_id}")

    def _check_and_resolve(self, uniprot_id: str) -> str:
        """
        UniProt REST API で ID の状態を確認し、必要に応じて解決

        Args:
            uniprot_id: UniProt ID

        Returns:
            解決された UniProt ID（アクティブな ID）
        """
        # REST API で JSON を取得
        rest_url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}?format=json"

        try:
            response = requests.get(rest_url, timeout=10)

            # 404 の場合は obsolete かもしれないので、履歴を確認
            if response.status_code == 404:
                return self._check_obsolete_history(uniprot_id)

            response.raise_for_status()
            data = response.json()

            # entryType が "Inactive" の場合
            entry_type = data.get("entryType")
            if entry_type == "Inactive":
                # inactiveReason を確認
                inactive_reason = data.get("inactiveReason", {})
                reason_type = inactive_reason.get("inactiveReasonType")

                if reason_type == "DEMERGED":
                    # DEMERGED の場合、merged_into を取得
                    merged_into = inactive_reason.get("mergeDemergeTo", [])
                    if merged_into:
                        return merged_into[0]

                elif reason_type == "MERGED":
                    # MERGED の場合も同様
                    merged_into = inactive_reason.get("mergeDemergeTo", [])
                    if merged_into:
                        return merged_into[0]

            # アクティブな場合はそのまま返す
            primary_accession = data.get("primaryAccession")
            if primary_accession:
                return primary_accession

            return uniprot_id

        except Exception as e:
            # エラーの場合は元の ID をそのまま返す
            print(f"  ⚠️ ID 解決中にエラー: {e}")
            return uniprot_id

    def _check_obsolete_history(self, uniprot_id: str) -> str:
        """
        Obsolete な ID の履歴を確認

        Args:
            uniprot_id: UniProt ID

        Returns:
            解決された UniProt ID
        """
        # UniProt の履歴 API を使用
        history_url = (
            f"https://rest.uniprot.org/uniprotkb/search?query=accession_id:{uniprot_id}&format=json"
        )

        try:
            response = requests.get(history_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    # 最初の結果の primaryAccession を返す
                    return results[0].get("primaryAccession", uniprot_id)
        except:
            pass

        return uniprot_id

    def get_original_id(self) -> str:
        """
        元の（入力された）UniProt ID を取得

        Returns:
            元の UniProt ID
        """
        return self.original_id

    def get_resolved_id(self) -> str:
        """
        解決された（実際に使用する）UniProt ID を取得

        Returns:
            解決された UniProt ID
        """
        return self.resolved_id

    def get_id(self) -> List[str]:
        """
        UniProt ID 取得（複数の場合あり）

        Returns:
            UniProt ID のリスト
        """
        return [accession.text for accession in self.xml.findall("./entry/accession", self.nsmap)]

    def fasta(self) -> str:
        """
        FASTA 配列の取得

        Returns:
            アミノ酸配列（改行なし）
        """
        sequence = self.xml.find("./entry/sequence", self.nsmap).text
        # 改行を削除
        return "".join(sequence.split())

    def get_fullname(self) -> str:
        """
        タンパク質のフルネーム取得

        Returns:
            Full name
        """
        fullname_elem = self.xml.find("./entry/protein/*/fullName", self.nsmap)
        return fullname_elem.text if fullname_elem is not None else ""

    def get_organism(self) -> str:
        """
        生物種名取得

        Returns:
            Organism name
        """
        organism_elem = self.xml.find('./entry/organism/name[@type="scientific"]', self.nsmap)
        return organism_elem.text if organism_elem is not None else ""

    def getpdbdata(self, method: Optional[str] = None) -> pd.DataFrame:
        """
        PDB ID、method、resolution の取得（修正版：property の type 属性ベース）

        Args:
            method: フィルタリングする実験手法（例: "X-ray", "NMR"）
                   None の場合は全ての method を取得
                   "X-ray diffraction" は自動的に "X-ray" に正規化

        Returns:
            PDB data DataFrame (転置済み)
            - columns: PDB IDs
            - index: ['method', 'resolution', 'position']

        Note:
            UniProt XML の property 要素は順不同なので、type 属性を見て判定する。
            method の表記は "X-ray", "NMR", "EM" など（"X-ray diffraction" ではない）
        """
        # method の正規化（"X-ray diffraction" → "X-ray"）
        if method == "X-ray diffraction":
            method = "X-ray"

        pdbid = []
        data = []

        for dbReference in self.xml.findall('./entry/dbReference[@type="PDB"]', self.nsmap):
            method_val: Optional[str] = None
            resolution: Optional[str] = None
            chains: Optional[str] = None

            # property を type 属性ベースで取得
            for prop in dbReference.findall("property", self.nsmap):
                prop_type = prop.attrib.get("type")
                prop_value = prop.attrib.get("value")

                if prop_type == "method":
                    method_val = prop_value
                elif prop_type == "resolution":
                    resolution = prop_value
                elif prop_type == "chains":
                    chains = prop_value

            # method フィルタ（None ならフィルタしない）
            if method is not None and method_val != method:
                continue

            # NMR の場合は resolution が None のまま
            # （UniProt XML では NMR 構造に resolution プロパティがない）

            pdbid.append(dbReference.attrib["id"])
            data.append([method_val, resolution, chains])

        self.pdbdata = pd.DataFrame(
            data, index=pdbid, columns=["method", "resolution", "position"]
        ).T

        return self.pdbdata

    def pdblist(self, method: str = "") -> List[str]:
        """
        PDB ID リスト取得

        Args:
            method: フィルタリングする実験手法
                   空文字列 "" の場合は全ての method を取得

        Returns:
            PDB ID のリスト
        """
        try:
            return self.pdbdata.columns.tolist()
        except AttributeError:
            # method が空文字列の場合は None を渡す（フィルタなし）
            filter_method = None if method == "" else method
            return self.getpdbdata(filter_method).columns.tolist()

    def position(self, pdbid: str) -> Tuple[int, int]:
        """
        position 情報の取得

        Args:
            pdbid: PDB ID

        Returns:
            (beg, end): 配列の開始・終了位置（1-based）
        """
        positiondata = self.pdbdata.at["position", pdbid]

        # chains プロパティは "A=1-76, B=1-76" のような形式
        # 複数チェーンの場合は最初のチェーンの範囲を使う
        if positiondata is None or pd.isna(positiondata):
            # position 情報がない場合は全配列を使う想定
            return (1, len(self.fasta()))

        # カンマ区切りで分割
        chains_list = positiondata.split(", ")

        if len(chains_list) == 1:
            # 単一チェーン
            _, posi = chains_list[0].split("=")
            beg, end = posi.split("-")
            beg = int(beg)
            end = int(end)
        else:
            # 複数チェーン（最小と最大を取得）
            beg = []
            end = []
            for chain_info in chains_list:
                _, posi = chain_info.split("=")
                align_beg, align_end = posi.split("-")
                beg.append(int(align_beg))
                end.append(int(align_end))
            beg = min(beg)
            end = max(end)

        return beg, end


def convert_three(sequence: str) -> List[str]:
    """
    1文字アミノ酸コードを3文字に変換

    Args:
        sequence: 1文字コードの配列

    Returns:
        3文字コードのリスト
    """
    dic = {
        "A": "ALA",
        "B": "D|N",
        "C": "CYS",
        "D": "ASP",
        "E": "GLU",
        "F": "PHE",
        "G": "GLY",
        "H": "HIS",
        "I": "ILE",
        "K": "LYS",
        "L": "LEU",
        "M": "MET",
        "N": "ASN",
        "O": "HYP",
        "P": "PRO",
        "Q": "GLN",
        "R": "ARG",
        "S": "SER",
        "T": "THR",
        "U": "SEC",
        "V": "VAL",
        "W": "TRP",
        "X": "any",
        "Y": "TYR",
        "Z": "E|Q",
    }
    return [dic[char] for char in sequence]
