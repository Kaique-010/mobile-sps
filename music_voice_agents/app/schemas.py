from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    score_id: str
    normalized_musicxml_path: str
    voices: list[str]


class VoiceListResponse(BaseModel):
    score_id: str
    voices: list[str]


class SingRequest(BaseModel):
    voice: str = Field(pattern="^(soprano|contralto|tenor|baixo)$")


class SingResponse(BaseModel):
    score_id: str
    voice: str
    audio_path: str
