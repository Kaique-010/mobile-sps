from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

VOICE_PROMPTS = {
    "soprano": "Cante esta linha com timbre de soprano lírico, afinação clara e fraseado coral.",
    "contralto": "Cante esta linha com timbre de contralto quente, sustentação estável e boa dicção.",
    "tenor": "Cante esta linha com timbre de tenor claro, projeção média e precisão rítmica.",
    "baixo": "Cante esta linha com timbre de baixo profundo, ataque suave e ressonância estável.",
}


def synthesize_voice(voice: str, notes_description: str, output_path: Path) -> Path:
    """
    Gera áudio da voz selecionada.

    Ajuste OPENAI_TTS_MODEL para o modelo de voz disponível na sua conta.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = os.environ.get("OPENAI_TTS_MODEL", "gpt-5-voice")
    voice_style = os.environ.get("OPENAI_TTS_VOICE", "alloy")

    prompt = f"{VOICE_PROMPTS[voice]} Conteúdo musical: {notes_description}"

    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice_style,
        input=prompt,
        format="mp3",
    ) as response:
        response.stream_to_file(str(output_path))

    return output_path
