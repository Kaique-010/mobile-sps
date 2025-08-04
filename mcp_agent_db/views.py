from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import time
import traceback
from core.middleware import get_licenca_slug, get_modulos_disponiveis
from .cache_manager import query_cache
from .conversation_memory import conversation_memory
from . import get_consultar_banco_dados, get_processar_pergunta_com_agente_v2
from .schema_loader import listar_schemas_disponiveis

@require_http_methods(["GET"])
def health_check(request, slug=None):
    """Endpoint de verificação de saúde"""
    try:
        slug = get_licenca_slug()
        modulos = get_modulos_disponiveis()
        
        return JsonResponse({
            "status": "healthy",
            "timestamp": time.time(),
            "slug": slug,
            "modulos_count": len(modulos) if modulos else 0,
            "version": "1.0.4"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def list_schemas(request, slug=None):
    """Lista schemas disponíveis"""
    try:
        slug = get_licenca_slug()
        schemas = listar_schemas_disponiveis()
        
        return JsonResponse({
            "schemas": schemas,
            "slug": slug,
            "count": len(schemas)
        })
    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def consulta_view(request, slug=None):
    """Endpoint principal para consultas"""
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta', '').strip()
        
        if not pergunta:
            return JsonResponse({
                "error": "Pergunta é obrigatória"
            }, status=400)
        
        slug = get_licenca_slug()
        
        # Importar e usar a função interna diretamente para evitar problemas de callback do LangChain
        from .consulta_tool import consultar_banco_dados_interno
        
        # Executar consulta usando a função interna
        resultado = consultar_banco_dados_interno(pergunta, slug)
        
        # Padronizar resposta
        response_data = {
            "success": True,
            "pergunta": pergunta,
            "resposta": resultado,
            "slug": slug,
            "timestamp": time.time(),
            "tipo": "consulta_regular"
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        print(traceback.format_exc())
        return JsonResponse({
            "success": False,
            "error": "JSON inválido"
        }, status=400)
    except Exception as e:
        print(traceback.format_exc())
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def grafico_view(request, slug=None):
    """Endpoint para geração de gráficos"""
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta', '').strip()
        tipo_grafico = data.get('tipo_grafico', 'bar')
        
        if not pergunta:
            return JsonResponse({
                "error": "Pergunta é obrigatória"
            }, status=400)
        
        slug = get_licenca_slug()
        processar_pergunta_com_agente_v2 = get_processar_pergunta_com_agente_v2()
        
        # Adicionar contexto de gráfico à pergunta
        pergunta_grafico = f"Gere um gráfico {tipo_grafico} para: {pergunta}"
        
        # Processar com agente inteligente
        resultado = processar_pergunta_com_agente_v2(pergunta_grafico, request.user if request.user.is_authenticated else None)
        
        response_data = {
            "success": True,
            "pergunta": pergunta,
            "tipo_grafico": tipo_grafico,
            "resposta": resultado,
            "slug": slug,
            "timestamp": time.time(),
            "tipo": "grafico"
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "JSON inválido"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def consulta_streaming_view(request, slug=None):
    """Endpoint para consultas com streaming"""
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta', '').strip()
        
        if not pergunta:
            return JsonResponse({
                "error": "Pergunta é obrigatória"
            }, status=400)
        
        def generate_stream():
            try:
                slug = get_licenca_slug()
                
                # Enviar início
                yield f"data: {json.dumps({'tipo': 'inicio', 'mensagem': 'Iniciando processamento...', 'timestamp': time.time()})}\n\n"
                time.sleep(0.3)
                
                # Etapas de processamento mais detalhadas
                etapas = [
                    {"nome": "Analisando pergunta...", "descricao": "Interpretando a consulta do usuário"},
                    {"nome": "Carregando schema...", "descricao": "Obtendo estrutura do banco de dados"},
                    {"nome": "Gerando SQL...", "descricao": "Criando consulta SQL otimizada"},
                    {"nome": "Executando consulta...", "descricao": "Processando dados no banco"},
                    {"nome": "Formatando resultados...", "descricao": "Preparando resposta final"},
                    {"nome": "Gerando insights...", "descricao": "Analisando dados para insights"}
                ]
                
                for i, etapa in enumerate(etapas):
                    progresso = ((i + 1) / len(etapas)) * 100
                    yield f"data: {json.dumps({'tipo': 'etapa', 'mensagem': etapa['nome'], 'descricao': etapa['descricao'], 'progresso': progresso, 'etapa': i+1, 'total_etapas': len(etapas)})}\n\n"
                    time.sleep(0.5)
                
                # Processar pergunta
                yield f"data: {json.dumps({'tipo': 'resposta_inicio', 'mensagem': 'Processando consulta...'})}\n\n"
                
                # Usar a função interna para evitar problemas de callback
                from .consulta_tool import consultar_banco_dados_interno
                resultado = consultar_banco_dados_interno(pergunta, slug)
                
                # Simular chunks de resposta para demonstrar streaming
                if isinstance(resultado, str) and len(resultado) > 100:
                    chunks = [resultado[i:i+50] for i in range(0, len(resultado), 50)]
                    for i, chunk in enumerate(chunks):
                        progresso = ((i + 1) / len(chunks)) * 100
                        yield f"data: {json.dumps({'tipo': 'resposta_chunk', 'texto': ''.join(chunks[:i+1]), 'progresso': progresso})}\n\n"
                        time.sleep(0.2)
                
                # Resultado final
                yield f"data: {json.dumps({'tipo': 'concluido', 'resposta_final': resultado, 'success': True, 'timestamp': time.time()})}\n\n"
                
            except Exception as e:
                print(f"Erro no streaming: {traceback.format_exc()}")
                yield f"data: {json.dumps({'tipo': 'erro', 'mensagem': str(e), 'success': False})}\n\n"
        
        response = StreamingHttpResponse(generate_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        # Remove the problematic Connection header - it's handled by the web server
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "JSON inválido"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@require_http_methods(["GET"])
def historico_view(request, slug=None):
    """Retorna histórico da conversa"""
    try:
        slug = get_licenca_slug()
        historico = conversation_memory.get_history()
        
        return JsonResponse({
            "success": True,
            "historico": historico,
            "slug": slug,
            "count": len(historico),
            "timestamp": time.time()
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def limpar_cache_view(request, slug=None):
    """Limpa cache de consultas"""
    try:
        slug = get_licenca_slug()
        query_cache.clear_all()
        
        return JsonResponse({
            "success": True,
            "message": "Cache limpo com sucesso",
            "slug": slug,
            "timestamp": time.time()
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def limpar_historico_view(request, slug=None):
    """Limpa histórico da conversa"""
    try:
        slug = get_licenca_slug()
        conversation_memory.clear_history()
        
        return JsonResponse({
            "success": True,
            "message": "Histórico limpo com sucesso",
            "slug": slug,
            "timestamp": time.time()
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

def index_view(request, slug=None):
    """Interface web principal"""
    try:
        slug = get_licenca_slug()
        modulos = get_modulos_disponiveis()
        
        context = {
            'slug': slug,
            'modulos_count': len(modulos) if modulos else 0,
            'api_base_url': f'/api/{slug}/mcp-agent'
        }
        
        return render(request, 'mcp_agent_db/index.html', context)
    except Exception as e:
        context = {
            'error': str(e),
            'slug': 'erro',
            'modulos_count': 0,
            'api_base_url': '/api/erro/mcp-agent'
        }
        return render(request, 'mcp_agent_db/index.html', context)

def docs_view(request, slug=None):
    """Documentação da API"""
    try:
        slug = get_licenca_slug()
        
        context = {
            'slug': slug,
            'api_base_url': f'/api/{slug}/mcp-agent'
        }
        
        return render(request, 'mcp_agent_db/docs.html', context)
    except Exception as e:
        context = {
            'error': str(e),
            'slug': 'erro',
            'api_base_url': '/api/erro/mcp-agent'
        }
        return render(request, 'mcp_agent_db/docs.html', context)