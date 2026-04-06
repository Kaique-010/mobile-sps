# Music Voice Agents (Agno + GPT Voice)

Projeto base para um **novo repositório** com dois agentes principais:

1. **Agente OCR/Parser**: lê partitura (PDF, imagem ou MusicXML) e converte para um objeto estruturado.
2. **Agente Cantor (TTS)**: canta a voz selecionada (Soprano, Contralto, Tenor ou Baixo) usando geração de voz com modelos da OpenAI.

## Fluxo proposto

1. Upload da partitura.
2. Normalização para MusicXML estruturado.
3. Agente de Harmonia classifica partes/vozes e progressões.
4. Separação de vozes (SATB).
5. Seleção da voz no frontend.
6. Geração de áudio da voz selecionada via OpenAI TTS.

## Stack

- **FastAPI** (API + upload)
- **Agno** (orquestração dos agentes)
- **music21** (parse e manipulação MusicXML/MIDI)
- **OpenAI API** (TTS vocal)
- Front-end simples (HTML/JS) para upload e seleção de voz

## Executar localmente

```bash
cd music_voice_agents
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8090
```

Acesse: `http://localhost:8090`

## Variáveis de ambiente

- `OPENAI_API_KEY` (obrigatória)
- `OPENAI_TTS_MODEL` (default: `gpt-5-voice`)
- `OPENAI_TTS_VOICE` (default: `alloy`)

## Endpoints principais

- `POST /api/scores/upload` → upload de partitura
- `POST /api/scores/{score_id}/analyze` → parse + separação SATB
- `GET /api/scores/{score_id}/voices` → lista vozes disponíveis
- `POST /api/scores/{score_id}/sing` → gera áudio da voz selecionada

## Observação

Este scaffold deixa os agentes prontos para evolução:
- adicionar OCR real para PDF/imagem (ex.: pipeline de visão),
- enriquecer o Agente de Harmonia,
- sincronizar playback com cursor da partitura no frontend.
