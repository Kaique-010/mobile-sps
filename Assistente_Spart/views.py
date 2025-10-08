from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from openai import OpenAI
import base64, tempfile, logging, time
from datetime import datetime
from .agenteReact import agenteReact, AGENT_TOOLS
from .tools.describer import gerar_descricao_tools
from .tools.qa_tools import faiss_context_qa
from core.utils import configurar_logger_colorido

# === Logger colorido ===
configurar_logger_colorido()
logger = logging.getLogger(__name__)

# === Descrição dinâmica das tools ===
descricao_tools = gerar_descricao_tools(AGENT_TOOLS)


class SpartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        inicio_total = time.time()
        client = OpenAI()

        # ======== CONTEXTO EMPRESA/FILIAL/BANCO ========
        slug = get_licenca_slug()
        banco = get_licenca_db_config(request)
        empresa_id = request.META.get("HTTP_X_EMPRESA", 1)
        filial_id = request.META.get("HTTP_X_FILIAL", 1)

        config = RunnableConfig(configurable={
            "thread_id": str(request.user.usua_codi),
            "empresa_id": str(empresa_id),
            "filial_id": str(filial_id),
            "banco": banco,
            "slug": slug,
        })

        # ======== ENTRADA DO USUÁRIO ========
        mensagem_usuario = None
        if "mensagem" in request.data:
            mensagem_usuario = request.data.get("mensagem")

        elif "audio" in request.FILES:
            audio_file = request.FILES["audio"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="pt"
                )
            mensagem_usuario = transcript.text

        if not isinstance(mensagem_usuario, str):
            return Response({"erro": "mensagem deve ser texto ou áudio"}, status=400)

        # ======== CONTEXTO FAISS OPCIONAL ========
        try:
            contexto_faiss = faiss_context_qa.invoke({"pergunta": mensagem_usuario})
        except Exception as e:
            logger.warning(f"[FAISS] Erro ao buscar contexto: {e}")
            contexto_faiss = None

        # ======== PROMPT UNIFICADO ========
        if contexto_faiss:
            prompt = f"""
{descricao_tools}

📎 Contexto de apoio (FAISS):
{contexto_faiss}

📍 Contexto atual:
- Empresa: {empresa_id}
- Filial: {filial_id}
- Banco: {banco}
- Slug: {slug}

💬 Pergunta: {mensagem_usuario}
"""
        else:
            prompt = f"""
{descricao_tools}

📍 Contexto atual:
- Empresa: {empresa_id}
- Filial: {filial_id}
- Banco: {banco}
- Slug: {slug}

💬 Pergunta: {mensagem_usuario}
"""

        logger.debug(f"[PROMPT_PREVIEW]\n{prompt[:600]}...\n---")

        mensagens = [HumanMessage(content=prompt)]

        # ======== EXECUÇÃO DO AGENTE ========
        resposta_texto = ""
        try:
            eventos = agenteReact.stream(
                {"messages": mensagens},
                config,
                stream_mode="updates"
            )

            try:
                for evento in eventos:
                    mensagens_evento = (
                        evento.get("messages")
                        if isinstance(evento, dict)
                        else getattr(evento, "messages", None)
                    )
                    if not mensagens_evento:
                        continue

                    for msg in mensagens_evento:
                        # === Mensagens da IA ===
                        if isinstance(msg, AIMessage):
                            conteudo = msg.content
                            if isinstance(conteudo, list):
                                conteudo = "\n".join(
                                    b.get("text") for b in conteudo
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                            if conteudo:
                                resposta_texto += f"\n{conteudo}"

                            tool_calls = (
                                getattr(msg, "tool_calls", None)
                                or getattr(msg, "additional_kwargs", {}).get("tool_calls")
                            )
                            if tool_calls:
                                for tc in tool_calls:
                                    nome = tc.get("name")
                                    args = tc.get("args")
                                    logger.debug(f"🧩 [TOOL_CALL] {nome} args={args}")

                        # === Retorno das ferramentas ===
                        elif isinstance(msg, ToolMessage):
                            conteudo_tool = (
                                msg.content
                                or msg.additional_kwargs.get("content")
                                or msg.additional_kwargs.get("text")
                                or ""
                            )
                            logger.debug(f"⚙️ [TOOL_OUTPUT] {conteudo_tool[:300]}...")
                            if conteudo_tool:
                                resposta_texto += f"\n{conteudo_tool}"

            finally:
                if hasattr(eventos, "close"):
                    eventos.close()

        except Exception as e:
            logger.exception("[SpartView] Falha na execução do agente")
            resposta_texto = f"❌ Erro interno ao processar: {e}"

        # ======== RESPOSTA FINAL ========
        if not resposta_texto.strip():
            resposta_texto = (
                "⚠️ O agente executou mas não retornou texto visível. "
                "Verifique os logs de TOOL_OUTPUT."
            )

        # ======== GERAR ÁUDIO TTS ========
        audio_base64 = ""
        try:
            tts_response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=resposta_texto
            )
            audio_base64 = base64.b64encode(tts_response.read()).decode("utf-8")
        except Exception as e:
            logger.warning(f"[SpartView] Falha ao gerar áudio TTS: {e}")

        fim_total = time.time()
        logger.info(f"✅ Tempo total da requisição: {round(fim_total - inicio_total, 2)}s")

        return Response({
            "resposta": resposta_texto.strip(),
            "resposta_audio": audio_base64
        })
