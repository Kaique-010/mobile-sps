from __future__ import annotations

from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PARSED_DIR = DATA_DIR / "parsed"
AUDIO_DIR = DATA_DIR / "audio"


for folder in (DATA_DIR, UPLOAD_DIR, PARSED_DIR, AUDIO_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def persist_upload(filename: str, content: bytes) -> tuple[str, Path]:
    score_id = str(uuid4())
    suffix = Path(filename).suffix or ".bin"
    output = UPLOAD_DIR / f"{score_id}{suffix}"
    output.write_bytes(content)
    return score_id, output


def parsed_musicxml_path(score_id: str) -> Path:
    return PARSED_DIR / f"{score_id}.musicxml"


def voice_audio_path(score_id: str, voice: str) -> Path:
    return AUDIO_DIR / f"{score_id}_{voice}.mp3"
