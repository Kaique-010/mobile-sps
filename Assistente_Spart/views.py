from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from openai import OpenAI
import base64, tempfile, logging, time
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
            logger.info("📝 Entrada via texto")

        elif "audio" in request.FILES:
            inicio_whisper = time.time()
            logger.info("🎤 Iniciando transcrição de áudio...")
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
            logger.info(f"✅ Transcrição concluída em {round(time.time() - inicio_whisper, 2)}s: {mensagem_usuario[:50]}...")

        if not isinstance(mensagem_usuario, str):
            return Response({"erro": "mensagem deve ser texto ou áudio"}, status=400)

        # ======== CONTEXTO FAISS OPCIONAL ========
        inicio_faiss = time.time()
        try:
            logger.info("🔍 Buscando contexto no FAISS...")
            contexto_faiss = faiss_context_qa.invoke({"pergunta": mensagem_usuario})
            logger.info(f"✅ FAISS concluído em {round(time.time() - inicio_faiss, 2)}s")
        except Exception as e:
            logger.warning(f"[FAISS] Erro ao buscar contexto em {round(time.time() - inicio_faiss, 2)}s: {e}")
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

        # ======== EXECUÇÃO DO AGENTE (SIMPLES) ========
        resposta_texto = ""
        inicio_agente = time.time()
        try:
            logger.info("🤖 Executando agente ReAct...")
            resultado = agenteReact.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config
            )
            logger.info(f"✅ Agente concluído em {round(time.time() - inicio_agente, 2)}s")
            
            # Extrai a resposta final
            mensagens = resultado.get("messages", [])
            
            # Pega a última mensagem do assistente
            for msg in reversed(mensagens):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                    conteudo = msg.content
                    if isinstance(conteudo, list):
                        conteudo = " ".join(
                            str(b.get("text", "")) for b in conteudo
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    if conteudo:
                        resposta_texto = str(conteudo).strip()
                        break
            
            logger.info(f"✅ Resposta gerada: {resposta_texto[:100]}...")
            
        except Exception as e:
            logger.exception("[SpartView] Erro ao executar agente")
            resposta_texto = f"❌ Erro ao processar sua solicitação: {str(e)}"

        # ======== FALLBACK ========
        if not resposta_texto:
            resposta_texto = "⚠️ O agente não retornou uma resposta. Tente novamente."

        # ======== GERAR ÁUDIO TTS ========
        audio_base64 = ""
        inicio_tts = time.time()
        try:
            logger.info("🔊 Gerando áudio TTS...")
            tts_response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=resposta_texto
            )
            audio_base64 = base64.b64encode(tts_response.read()).decode("utf-8")
            logger.info(f"✅ TTS concluído em {round(time.time() - inicio_tts, 2)}s")
        except Exception as e:
            logger.warning(f"[SpartView] Falha ao gerar áudio TTS em {round(time.time() - inicio_tts, 2)}s: {e}")

        fim_total = time.time()
        logger.info(f"✅ Tempo total: {round(fim_total - inicio_total, 2)}s")

        return Response({
            "resposta": resposta_texto,
            "resposta_audio": audio_base64
        })