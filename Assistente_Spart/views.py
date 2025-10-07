from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from openai import OpenAI
import base64, tempfile, logging

from .agenteReact import agenteReact
from .tools.qa_tools import faiss_context_qa

logger = logging.getLogger(__name__)


class SpartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        client = OpenAI()

        # ======== CONTEXTO EMPRESA/FILIAL/BANCO ========
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.META.get("HTTP_X_EMPRESA", 1)
        filial_id = self.request.META.get("HTTP_X_FILIAL", 1)

        config = RunnableConfig(configurable={
            "thread_id": str(self.request.user.usua_codi),
            "empresa_id": str(empresa_id),
            "filial_id": str(filial_id),
            "banco": banco,
            "slug": slug,
        })

        # ======== ENTRADA DO USUÁRIO ========
        mensagem_usuario = None
        if "mensagem" in self.request.data:
            mensagem_usuario = self.request.data.get("mensagem")

        elif "audio" in self.request.FILES:
            audio_file = self.request.FILES["audio"]
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
            contexto_faiss = faiss_context_qa(mensagem_usuario)
        except Exception as e:
            logger.warning(f"[FAISS] Erro ao buscar contexto: {e}")
            contexto_faiss = None

        # ======== MENSAGEM UNIFICADA ========
        prompt = ""
        if contexto_faiss:
            prompt += f"Contexto de apoio (use se necessário):\n{contexto_faiss}\n\n"
        prompt += f"""
                Você é um assistente corporativo com acesso às seguintes ferramentas:
                - identificar_intencao(mensagem): analisa o texto e descobre o que o usuário quer fazer.
                - executar_intencao(mensagem, banco, empresa_id, filial_id): executa ações de cadastro e consulta de produtos.
                - cadastrar_produtos(prod_nome, prod_ncm, banco, empresa_id, filial_id): cria produtos novos.
                - consultar_saldo(produto_codigo, banco, empresa_id, filial_id): consulta saldo de um produto.

                Sempre que o usuário pedir algo relacionado a produtos, você DEVE chamar
                'executar_intencao' diretamente. Quando chamar, envie SEMPRE argumentos nomeados:
                mensagem="{mensagem_usuario}", banco="{banco}", empresa_id="{empresa_id}", filial_id="{filial_id}", slug="{slug}".
                Essa ferramenta decide internamente se deve chamar cadastrar_produtos ou consultar_saldo.

                Não responda sem usar ferramentas quando o tema for produtos.

                Pergunta: {mensagem_usuario}
                """

        mensagens = [HumanMessage(content=prompt)]

        # ======== EXECUÇÃO DO AGENTE ========
        resposta_texto = ""
        try:
            eventos = agenteReact.stream(
                {"messages": mensagens},
                config,
                stream_mode="values"  # mostra tool outputs e erros
            )

            for evento in eventos:
                # Cada evento é um dicionário ou mensagem intermediária
                mensagens_evento = evento.get("messages") if isinstance(evento, dict) else getattr(evento, "messages", None)
                if not mensagens_evento:
                    continue

                for msg in mensagens_evento:
                    if isinstance(msg, AIMessage):
                        conteudo = msg.content
                        if isinstance(conteudo, list):
                            conteudo = "\n".join(
                                b.get("text") for b in conteudo if isinstance(b, dict) and b.get("type") == "text"
                            )
                        if conteudo:
                            resposta_texto += f"\n{conteudo}"
                        # Log tool_calls
                        tool_calls = getattr(msg, "tool_calls", None) or getattr(msg, "additional_kwargs", {}).get("tool_calls")
                        if tool_calls:
                            for tc in tool_calls:
                                nome = tc.get("name")
                                args = tc.get("args")
                                logger.debug(f"[TOOL_CALL] {nome} args={args}")

                    elif isinstance(msg, ToolMessage):
                        logger.debug(f"[TOOL_OUTPUT] {msg.content or msg.additional_kwargs}")
                        if msg.content:
                            resposta_texto += f"\n{msg.content}"
                            # Encerrar processamento após primeiro output de ferramenta para evitar duplicidade
                            eventos.close() if hasattr(eventos, "close") else None
                            return Response({
                                "resposta": resposta_texto.strip(),
                                "resposta_audio": ""
                            })

        except Exception as e:
            logger.exception("[SpartView] Falha na execução do agente")
            resposta_texto = f"Erro interno ao processar: {e}"

        # ======== RESPOSTA FINAL ========
        if not resposta_texto.strip():
            resposta_texto = "Desculpe, não consegui gerar uma resposta no momento."

        # ======== GERAR ÁUDIO TTS ========
        audio_base64 = ""
        try:
            tts_response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=resposta_texto
            )
            audio_base64 = base64.b64encode(tts_response.read()).decode("utf-8")
        except Exception:
            logger.warning("[SpartView] Falha ao gerar áudio TTS")
            audio_base64 = ""

        return Response({
            "resposta": resposta_texto.strip(),
            "resposta_audio": audio_base64
        })
