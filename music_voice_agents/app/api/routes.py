from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.agents.orchestrator import ScoreAgents
from app.schemas import AnalyzeResponse, SingRequest, SingResponse, VoiceListResponse
from app.services.storage import persist_upload, voice_audio_path
from app.services.tts import synthesize_voice

router = APIRouter(prefix="/api/scores", tags=["scores"])
agents = ScoreAgents()
SCORE_DB: dict[str, dict] = {}


@router.post("/upload")
async def upload_score(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    score_id, path = persist_upload(file.filename, content)
    SCORE_DB[score_id] = {"upload_path": str(path), "voices": []}
    return {"score_id": score_id, "upload_path": str(path)}


@router.post("/{score_id}/analyze", response_model=AnalyzeResponse)
def analyze_score(score_id: str) -> AnalyzeResponse:
    score = SCORE_DB.get(score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score não encontrado")

    result = agents.analyze_score(score_id=score_id, input_path=Path(score["upload_path"]))
    score["voices"] = result.voices
    score["normalized_musicxml_path"] = str(result.normalized_musicxml)

    return AnalyzeResponse(
        score_id=score_id,
        normalized_musicxml_path=str(result.normalized_musicxml),
        voices=result.voices,
    )


@router.get("/{score_id}/voices", response_model=VoiceListResponse)
def list_voices(score_id: str) -> VoiceListResponse:
    score = SCORE_DB.get(score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score não encontrado")

    voices = score.get("voices") or []
    return VoiceListResponse(score_id=score_id, voices=voices)


@router.post("/{score_id}/sing", response_model=SingResponse)
def sing_voice(score_id: str, payload: SingRequest) -> SingResponse:
    score = SCORE_DB.get(score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score não encontrado")

    if payload.voice not in (score.get("voices") or []):
        raise HTTPException(status_code=400, detail="Voz não disponível para esta partitura")

    output = voice_audio_path(score_id, payload.voice)

    # Placeholder de extração da trilha da voz selecionada.
    notes_description = f"Linha melódica da voz {payload.voice} extraída do MusicXML." 
    synthesize_voice(payload.voice, notes_description, output)

    return SingResponse(score_id=score_id, voice=payload.voice, audio_path=str(output))
