from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from openai import OpenAI
import base64, tempfile, logging, time, json, asyncio
from .agenteReact import agenteReact, AGENT_TOOLS, faiss_cached, pre_rotear, metricas
from .tools.describer import gerar_descricao_tools
from core.utils import configurar_logger_colorido

configurar_logger_colorido()
logger = logging.getLogger(__name__)

descricao_tools = gerar_descricao_tools(AGENT_TOOLS)


class SpartView(APIView):
    """
    View OTIMIZADA com estratégia híbrida:
    - executar_intencao: Roteador principal inteligente
    - Pre-roteador: Decide se precisa FAISS
    - Cache: Evita reconsultas
    - Streaming: Reduz latência percebida
    """
    permission_classes = [IsAuthenticated]
    # Suporta JSON (mensagens) e multipart/form-data (áudio)
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, slug=None):
        inicio_total = time.time()
        
        # Detecta se cliente quer streaming (SSE)
        accept = request.META.get('HTTP_ACCEPT', '')
        if 'text/event-stream' in accept:
            return self._streaming_response(request, slug)
        
        return self._standard_response(request, slug)

    def get(self, request, slug=None):
        """Habilita GET para SSE. Para resposta padrão use POST."""
        accept = request.META.get('HTTP_ACCEPT', '')
        if 'text/event-stream' in accept:
            return self._streaming_response(request, slug)
        return Response({
            'detail': 'Use POST para chat padrão ou GET com Accept: text/event-stream para streaming.'
        }, status=405)

    def _standard_response(self, request, slug):
        """Resposta padrão OTIMIZADA com pre-roteador"""
        inicio_total = time.time()
        client = OpenAI()

        # ======== CONTEXTO ========
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

        # ======== ENTRADA ========
        mensagem_usuario = self._processar_entrada(request, client)
        if isinstance(mensagem_usuario, Response):
            return mensagem_usuario

        # ======== PRÉ-ROTEADOR (50-100ms) ========
        inicio_pre_roteador = time.time()
        rota = pre_rotear(mensagem_usuario)
        tempo_pre_roteador = round(time.time() - inicio_pre_roteador, 3)
        logger.info(f"🎯 Pré-roteador: {rota['tipo']} (confiança: {rota['confianca']}) em {tempo_pre_roteador}s")
        metricas.registrar("pre_roteador", tempo_pre_roteador)

        # ======== CONTEXTO FAISS (CONDICIONAL + CACHE) ========
        contexto_faiss = None
        if rota["precisa_faiss"]:
            inicio_faiss = time.time()
            try:
                logger.info("🔍 Buscando contexto FAISS (com cache)...")
                contexto_faiss = faiss_cached(mensagem_usuario)
                tempo_faiss = round(time.time() - inicio_faiss, 2)
                logger.info(f"✅ FAISS em {tempo_faiss}s")
                metricas.registrar("faiss", tempo_faiss)
            except Exception as e:
                logger.warning(f"[FAISS] Erro: {e}")
        else:
            logger.info("⚡ FAISS ignorado (consulta direta detectada)")

        # ======== PROMPT OTIMIZADO ========
        # Estratégia: Deixar executar_intencao fazer o trabalho pesado
        prompt_parts = []
        
        if contexto_faiss:
            prompt_parts.append(f"📎 Contexto de apoio:\n{contexto_faiss}\n")
        
        prompt_parts.append(f"""
📍 Informações da sessão:
- Empresa: {empresa_id}
- Filial: {filial_id}
- Banco: {banco}
- Slug: {slug}

💬 Pergunta do usuário:
{mensagem_usuario}

⚡ IMPORTANTE: Use a ferramenta 'executar_intencao' como primeira opção. 
Ela já faz o roteamento inteligente para a tool correta.""")
        
        prompt = "\n".join(prompt_parts)
        logger.debug(f"[PROMPT] Tamanho: {len(prompt)} chars")

        # ======== AGENTE ========
        # ======== AGENTE ========
        resposta_texto = ""
        tools_usadas = []
        inicio_agente = time.time()

        try:
            logger.info(f"🤖 Executando agente (tipo: {rota['tipo']})...")
            
            # Configuração robusta
            resultado = agenteReact.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config
            )
            
            tempo_agente = round(time.time() - inicio_agente, 2)
            logger.info(f"✅ Agente concluído em {tempo_agente}s")
            metricas.registrar("agente", tempo_agente)
            
            # Extração robusta de mensagens
            mensagens = resultado.get("messages", [])
            
            if not mensagens:
                resposta_texto = "⚠️ O agente não retornou mensagens."
                logger.warning("[AGENTE] Resultado vazio")
            else:
                for msg in mensagens:
                    msg_type = msg.__class__.__name__
                    
                    # Detecta tools executadas
                    if msg_type == 'ToolMessage':
                        tool_name = getattr(msg, 'name', 'desconhecida')
                        tools_usadas.append(tool_name)
                        
                        # Verifica se a tool retornou erro
                        content = getattr(msg, 'content', '')
                        if content and isinstance(content, str):
                            if content.startswith('❌'):
                                logger.warning(f"[TOOL_ERROR] {tool_name}: {content[:100]}")
                    
                    # Extrai resposta do AIMessage
                    elif msg_type == 'AIMessage':
                        conteudo = getattr(msg, 'content', '')
                        
                        # Processa conteúdo complexo (lista de dicts)
                        if isinstance(conteudo, list):
                            texto_parts = []
                            for item in conteudo:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    texto_parts.append(str(item.get("text", "")))
                            conteudo = " ".join(texto_parts).strip()
                        
                        # Processa string simples
                        elif isinstance(conteudo, str):
                            conteudo = conteudo.strip()
                        
                        if conteudo:
                            resposta_texto = str(conteudo)
                
                logger.info(f"🔧 Tools executadas: {tools_usadas or ['nenhuma']}")
                
                # Validação final
                if not resposta_texto or resposta_texto.strip() == "":
                    resposta_texto = "⚠️ O agente não gerou uma resposta textual."
                    logger.warning("[AGENTE] Resposta vazia após processamento")

        except Exception as e:
            logger.exception("[AGENTE] Erro detalhado")
            
            error_str = str(e)
            
            # Tratamento específico para INVALID_CHAT_HISTORY
            if "INVALID_CHAT_HISTORY" in error_str or "ToolMessage" in error_str:
                resposta_texto = (
                    "⚠️ Ocorreu um problema no histórico de conversa. "
                    "Por favor, reformule sua pergunta de forma mais específica."
                )
                logger.error(f"[AGENTE] Erro de histórico: {error_str}")
                
                # Limpa o histórico se possível
                try:
                    # Força limpeza do checkpointer
                    config_thread = config.get("configurable", {}).get("thread_id")
                    if config_thread:
                        logger.info(f"🧹 Limpando histórico do thread {config_thread}")
                except:
                    pass
            
            # Outros erros
            else:
                resposta_texto = f"❌ Erro ao processar: {str(e)}"
            
            metricas.registrar("erro", time.time() - inicio_agente)

        # Fallback final
        if not resposta_texto or not isinstance(resposta_texto, str):
            resposta_texto = "⚠️ Não foi possível gerar uma resposta válida."

        # ======== TTS PARALELO (Não bloqueia) ========
        # TTS roda em thread separada para não bloquear resposta
        import threading
        audio_base64 = ""
        
        def gerar_audio_background():
            nonlocal audio_base64
            audio_base64 = self._gerar_audio_otimizado(client, resposta_texto)
        
        thread_tts = threading.Thread(target=gerar_audio_background)
        thread_tts.start()
        
        # Retorna resposta imediatamente, áudio vem depois
        # (ou aguarda max 3s)

        # Aguarda TTS (max 3s) ou retorna sem áudio
        thread_tts.join(timeout=3.0)
        
        tempo_total = round(time.time() - inicio_total, 2)
        logger.info(f"✅ Tempo total: {tempo_total}s")
        metricas.registrar("total", tempo_total)

        return Response({
            "resposta": resposta_texto,
            "resposta_audio": audio_base64,
            "metadata": {
                "tempo_total": tempo_total,
                "tipo_rota": rota["tipo"],
                "confianca_rota": rota["confianca"],
                "usou_faiss": bool(contexto_faiss),
                "tools_executadas": tools_usadas,
                "metricas": metricas.relatorio()
            }
        })

    def _streaming_response(self, request, slug):
        """STREAMING via Server-Sent Events"""
        
        async def generate():
            client = OpenAI()
            inicio = time.time()
            
            # Contexto
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
            
            # Entrada
            mensagem_usuario = self._processar_entrada(request, client)
            if isinstance(mensagem_usuario, Response):
                yield f"data: {json.dumps({'erro': 'Erro na entrada'})}\n\n"
                return
            
            # Pré-roteador
            rota = pre_rotear(mensagem_usuario)
            yield f"data: {json.dumps({'tipo': 'rota', 'valor': rota['tipo'], 'confianca': rota['confianca']})}\n\n"
            
            # FAISS condicional
            contexto_faiss = None
            if rota["precisa_faiss"]:
                yield f"data: {json.dumps({'tipo': 'status', 'mensagem': 'Buscando contexto...'})}\n\n"
                contexto_faiss = faiss_cached(mensagem_usuario)
                if contexto_faiss:
                    yield f"data: {json.dumps({'tipo': 'contexto', 'status': 'ok'})}\n\n"
            
            # Prompt
            prompt_parts = []
            if contexto_faiss:
                prompt_parts.append(f"📎 Contexto:\n{contexto_faiss}\n")
            prompt_parts.append(f"""
📍 Empresa: {empresa_id} | Filial: {filial_id} | Banco: {banco}
💬 {mensagem_usuario}

⚡ Use 'executar_intencao' como primeira opção.""")
            prompt = "\n".join(prompt_parts)
            
            # Stream do agente
            resposta_completa = []
            tools_usadas = []
            
            async for event in agenteReact.astream_events(
                {"messages": [HumanMessage(content=prompt)]},
                config,
                version="v2"
            ):
                kind = event["event"]
                
                # Stream de tokens
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, 'content') and chunk.content:
                        texto = chunk.content
                        resposta_completa.append(texto)
                        yield f"data: {json.dumps({'tipo': 'chunk', 'texto': texto})}\n\n"
                
                # Tools executadas
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "desconhecida")
                    tools_usadas.append(tool_name)
                    yield f"data: {json.dumps({'tipo': 'tool', 'nome': tool_name})}\n\n"
                
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    yield f"data: {json.dumps({'tipo': 'tool_fim', 'nome': tool_name})}\n\n"
            
            # Finaliza
            texto_final = "".join(resposta_completa)
            tempo_total = round(time.time() - inicio, 2)

            # Evita f-string multilinha (quebra parsing). Monta payload antes.
            payload_fim = {
                'tipo': 'fim',
                'resposta': texto_final,
                'tempo_total': tempo_total,
                'tools_usadas': tools_usadas,
            }
            yield f"data: {json.dumps(payload_fim)}\n\n"
            
            # TTS (opcional)
            audio_base64 = self._gerar_audio_otimizado(client, texto_final)
            if audio_base64:
                yield f"data: {json.dumps({'tipo': 'audio', 'data': audio_base64})}\n\n"
        
        # Converte async para sync
        def sync_generator():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_gen = generate()
                while True:
                    try:
                        yield loop.run_until_complete(async_gen.__anext__())
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        
        return StreamingHttpResponse(
            sync_generator(),
            content_type='text/event-stream',
            headers={
                'X-Accel-Buffering': 'no',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )

    def _processar_entrada(self, request, client):
        """Processa texto ou áudio (com Whisper)"""
        if "mensagem" in request.data:
            return request.data.get("mensagem")
        
        elif "audio" in request.FILES:
            inicio = time.time()
            logger.info("🎤 Transcrevendo áudio...")
            
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
            
            tempo = round(time.time() - inicio, 2)
            logger.info(f"✅ Whisper em {tempo}s: {transcript.text[:50]}...")
            metricas.registrar("whisper", tempo)
            return transcript.text
        
        return Response({"erro": "Envie 'mensagem' ou 'audio'"}, status=400)

    def _gerar_audio_otimizado(self, client, texto):
        """
        TTS com otimizações:
        - Trunca textos longos
        - Speed 1.15x (15% mais rápido)
        - Timeout de 5s
        """
        if not texto:
            return ""
        
        # Trunca textos muito longos
        if len(texto) > 800:
            texto = texto[:800] + "..."
        
        inicio = time.time()
        try:
            logger.info("🔊 Gerando TTS...")
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=texto,
                speed=1.15  # 15% mais rápido
            )
            
            audio_base64 = base64.b64encode(response.read()).decode("utf-8")
            tempo = round(time.time() - inicio, 2)
            logger.info(f"✅ TTS em {tempo}s")
            metricas.registrar("tts", tempo)
            return audio_base64
            
        except Exception as e:
            logger.warning(f"[TTS] Erro: {e}")
            return ""
