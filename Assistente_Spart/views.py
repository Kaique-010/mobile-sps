from rest_framework.views import APIView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug, get_modulos_disponiveis
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from langchain_core.messages import HumanMessage
from .agenteReact import agenteReact
from .tools.qa_tools import faiss_condicional_qa, faiss_context_qa
from openai import OpenAI
import base64
import tempfile

class SpartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        client = OpenAI()

        # 1. Pega banco correto (multi-empresa)
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.META.get("HTTP_X_EMPRESA", 1)
        filial_id = self.request.META.get("HTTP_X_FILIAL", 1)
        
        print(f'banco: {banco}')
        print(f'empresa_id: {empresa_id}')
        print(f'filial_id: {filial_id}')
        
        config = {
            "configurable": {
                "thread_id": str(self.request.user.usua_codi),
                "empresa_id": str(empresa_id),
                "filial_id": str(filial_id),
                "banco": banco,
                "slug": slug,
            }
        }

        # 2. Verifica se veio áudio ou texto
        mensagem_usuario = None
        if "mensagem" in self.request.data:
            mensagem_usuario = self.request.data.get("mensagem")

        elif "audio" in self.request.FILES: 
            audio_file = self.request.FILES["audio"]

            # cria arquivo temporário pra Whisper
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # transcreve com Whisper
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="pt"
                )
            mensagem_usuario = transcript.text

        if not isinstance(mensagem_usuario, str):
            return Response({"erro": "mensagem deve ser texto ou áudio"}, status=400)

        # 3. Tenta obter contexto via FAISS
        contexto_faiss = None
        try:
            contexto_faiss = faiss_context_qa(mensagem_usuario)
        except Exception:
            contexto_faiss = None

        # 4. Sempre responde com a LLM; se houver contexto FAISS, injeta como orientação
        mensagens = []
        if contexto_faiss:
            mensagens.append(HumanMessage(content=f"Use o contexto abaixo como referência principal. Se necessário, utilize as ferramentas (FAISS/SQLite/RAG) para complementar e responder de forma objetiva. Se o contexto não cobrir, peça mais informações.\n\nContexto:\n{contexto_faiss}"))
        mensagens.append(HumanMessage(content=mensagem_usuario))

        for evento in agenteReact.stream(
            {"messages": mensagens},
            config,
            stream_mode="values"
        ):
            resposta_texto = evento["messages"][-1].content

        # 5. Gera áudio com TTS
        tts_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=resposta_texto
        )
        audio_base64 = base64.b64encode(tts_response.read()).decode("utf-8")

        return Response({
            "resposta": resposta_texto,
            "resposta_audio": audio_base64  # frontend toca como mp3/wav
        })
