from __future__ import annotations

from pathlib import Path

from music21 import converter, stream

SATB = ["soprano", "contralto", "tenor", "baixo"]


def normalize_to_musicxml(input_path: Path, output_path: Path) -> Path:
    """Converte o arquivo de entrada para MusicXML normalizado."""
    score = converter.parse(str(input_path))
    score.write("musicxml", fp=str(output_path))
    return output_path


def infer_satb_voices(musicxml_path: Path) -> list[str]:
    """Heurística inicial: tenta mapear partes para SATB; fallback em todas as vozes."""
    score: stream.Score = converter.parse(str(musicxml_path))
    names: list[str] = []

    for part in score.parts:
        part_name = (part.partName or "").lower()
        if "sopr" in part_name:
            names.append("soprano")
        elif "alto" in part_name or "contr" in part_name:
            names.append("contralto")
        elif "tenor" in part_name:
            names.append("tenor")
        elif "bass" in part_name or "baixo" in part_name:
            names.append("baixo")

    unique = sorted(set(names))
    return unique or SATB.copy()
