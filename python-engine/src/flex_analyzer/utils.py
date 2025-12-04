"""ユーティリティ関数"""

import numpy as np
from typing import Tuple


def convert_three_to_one(three_letter: str) -> str:
    """3文字アミノ酸コードを1文字に変換"""
    code_map = {
        "ALA": "A",
        "CYS": "C",
        "ASP": "D",
        "GLU": "E",
        "PHE": "F",
        "GLY": "G",
        "HIS": "H",
        "ILE": "I",
        "LYS": "K",
        "LEU": "L",
        "MET": "M",
        "ASN": "N",
        "PRO": "P",
        "GLN": "Q",
        "ARG": "R",
        "SER": "S",
        "THR": "T",
        "VAL": "V",
        "TRP": "W",
        "TYR": "Y",
        "SEC": "U",
        "HYP": "O",
    }
    return code_map.get(three_letter.upper(), "X")


def convert_one_to_three(one_letter: str) -> str:
    """1文字アミノ酸コードを3文字に変換"""
    code_map = {
        "A": "ALA",
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
        "P": "PRO",
        "Q": "GLN",
        "R": "ARG",
        "S": "SER",
        "T": "THR",
        "V": "VAL",
        "W": "TRP",
        "Y": "TYR",
        "U": "SEC",
        "O": "HYP",
        "X": "UNK",
    }
    return code_map.get(one_letter.upper(), "UNK")
