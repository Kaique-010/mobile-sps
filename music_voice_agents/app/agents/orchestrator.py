from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.musicxml import infer_satb_voices, normalize_to_musicxml
from app.services.storage import parsed_musicxml_path


@dataclass
class AnalysisResult:
    score_id: str
    normalized_musicxml: Path
    voices: list[str]


class ScoreAgents:
    """
    Orquestrador de agentes.

    Observação: este scaffold mantém integração leve com Agno,
    com foco em fluxo e contratos da aplicação.
    """

    def analyze_score(self, score_id: str, input_path: Path) -> AnalysisResult:
        xml_path = parsed_musicxml_path(score_id)
        normalized = normalize_to_musicxml(input_path, xml_path)
        voices = infer_satb_voices(normalized)
        return AnalysisResult(
            score_id=score_id,
            normalized_musicxml=normalized,
            voices=voices,
        )
