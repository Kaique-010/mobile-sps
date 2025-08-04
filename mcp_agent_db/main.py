from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import uvicorn
import os
from agente_inteligente_v2 import processar_pergunta_com_agente_v2, processar_pergunta_com_streaming_sync
from sql_generator import gerar_sql_da_pergunta
from conversation_memory import conversation_memory
from cache_manager import query_cache

# Configuração da aplicação
app = FastAPI(
    title="MCP Agent DB",
    description="API para consulta de bases de dados usando linguagem natural",
    version="1.0.3",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Montar arquivos estáticos
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    # Fallback se a pasta static não existir
    pass

executor = ThreadPoolExecutor(max_workers=4)

class PerguntaRequest(BaseModel):
    pergunta: str
    slug: str = "casaa"

class GraficoRequest(BaseModel):
    pergunta: str
    tipo_grafico: str = "bar"
    slug: str = "casaa"

def executar_agente_sync(pergunta):
    return processar_pergunta_com_agente_v2(pergunta)

def executar_agente_streaming_sync(pergunta):
    return processar_pergunta_com_streaming_sync(pergunta)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Página inicial da aplicação"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>MCP Agent DB</title></head>
            <body>
                <h1>🤖 MCP Agent DB API</h1>
                <p>API para consulta de bases de dados usando linguagem natural</p>
                <ul>
                    <li><a href="/docs">📚 Documentação da API</a></li>
                    <li><a href="/redoc">📖 ReDoc</a></li>
                </ul>
            </body>
        </html>
        """)

@app.get("/logo.png")
async def get_logo():
    """Servir logo da aplicação"""
    from fastapi.responses import FileResponse
    try:
        return FileResponse("logo.png")
    except:
        return JSONResponse({"error": "Logo não encontrada"}, status_code=404)

@app.get("/api/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "version": "1.0.3",
        "service": "MCP Agent DB"
    }

@app.get("/api/schemas")
async def listar_schemas():
    """Listar schemas disponíveis"""
    # Aqui você pode implementar a lógica para listar schemas
    return {
        "schemas": ["casaa"],
        "default": "casaa"
    }

@app.post("/api/consulta")
async def consultar(request: PerguntaRequest):
    """Realizar consulta em linguagem natural"""
    print(f"🔍 Recebido: {request.pergunta}")
    
    try:
        # Executar o agente em thread separada
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            executor, 
            executar_agente_sync, 
            request.pergunta
        )
        
        print(f"✅ Resposta do agente: {resposta[:100]}...")
        
        return JSONResponse(content={
            "pergunta": request.pergunta,
            "resposta": resposta,
            "slug": request.slug,
            "status": "success"
        })
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return JSONResponse(
            content={
                "pergunta": request.pergunta,
                "resposta": f"Erro ao processar consulta: {str(e)}",
                "slug": request.slug,
                "status": "error"
            }, 
            status_code=500
        )

@app.post("/api/grafico")
async def gerar_grafico(request: GraficoRequest):
    """Gerar gráfico a partir de consulta"""
    print(f"📊 Gerando gráfico: {request.pergunta}")
    
    try:
        # Adicionar instrução de gráfico à pergunta
        pergunta_com_grafico = f"Gere um gráfico {request.tipo_grafico} para: {request.pergunta}"
        
        # Executar o agente em thread separada
        loop = asyncio.get_event_loop()
        resposta = await loop.run_in_executor(
            executor, 
            executar_agente_sync, 
            pergunta_com_grafico
        )
        
        return JSONResponse(content={
            "pergunta": request.pergunta,
            "tipo_grafico": request.tipo_grafico,
            "resposta": resposta,
            "slug": request.slug,
            "status": "success"
        })
        
    except Exception as e:
        print(f"❌ Erro ao gerar gráfico: {str(e)}")
        return JSONResponse(
            content={
                "pergunta": request.pergunta,
                "resposta": f"Erro ao gerar gráfico: {str(e)}",
                "slug": request.slug,
                "status": "error"
            }, 
            status_code=500
        )

async def stream_agente_response(pergunta: str):
    """Gerador que simula o streaming real da resposta do agente"""
    try:
        # Enviar evento de início
        yield f"data: {json.dumps({'tipo': 'inicio', 'mensagem': f'🤖 Analisando: {pergunta}'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Enviar etapas do processamento
        etapas = [
            "🧠 Entendendo a pergunta...",
            "🔍 Identificando dados necessários...",
            "🛠️ Preparando consulta SQL...",
            "📊 Executando no banco de dados...",
            "✨ Formatando resposta..."
        ]
        
        for i, etapa in enumerate(etapas, 1):
            yield f"data: {json.dumps({'tipo': 'etapa', 'numero': i, 'mensagem': etapa})}\n\n"
            await asyncio.sleep(0.8)
        
        # Executar o agente em thread separada
        loop = asyncio.get_event_loop()
        resposta_completa = await loop.run_in_executor(
            executor, 
            executar_agente_sync, 
            pergunta
        )
        
        # Simular streaming da resposta palavra por palavra
        yield f"data: {json.dumps({'tipo': 'resposta_inicio', 'mensagem': '📝 Gerando resposta...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Dividir a resposta em chunks para simular digitação
        palavras = resposta_completa.split()
        resposta_parcial = ""
        
        for i, palavra in enumerate(palavras):
            resposta_parcial += palavra + " "
            
            # Enviar chunk da resposta
            yield f"data: {json.dumps({'tipo': 'resposta_chunk', 'texto': resposta_parcial, 'progresso': (i+1)/len(palavras)*100})}\n\n"
            
            # Velocidade variável baseada no tamanho da palavra
            delay = 0.03 if len(palavra) < 5 else 0.05
            await asyncio.sleep(delay)
        
        # Enviar evento de conclusão
        yield f"data: {json.dumps({'tipo': 'concluido', 'resposta_final': resposta_completa})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'tipo': 'erro', 'mensagem': f'❌ Erro: {str(e)}'})}\n\n"

@app.post("/api/consulta-streaming")
async def consultar_com_streaming_real(request: PerguntaRequest):
    """Streaming real usando Server-Sent Events"""
    print(f"🎬 Iniciando streaming real: {request.pergunta}")
    
    return StreamingResponse(
        stream_agente_response(request.pergunta),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/api/historico")
async def get_historico():
    """Retorna histórico da conversa"""
    return {
        "historico": conversation_memory.history,
        "contexto": conversation_memory.context,
        "sugestoes": conversation_memory.get_suggestions()
    }

@app.post("/api/limpar-cache")
async def limpar_cache():
    """Limpa cache de consultas"""
    query_cache.cache.clear()
    return {"message": "Cache limpo com sucesso"}

@app.post("/api/limpar-historico")
async def limpar_historico():
    """Limpa histórico da conversa"""
    conversation_memory.history.clear()
    conversation_memory.context = {
        'empresa_atual': None,
        'filial_atual': None,
        'periodo_atual': None,
        'ultimo_resultado': None,
        'topico_atual': None
    }
    return {"message": "Histórico limpo com sucesso"}

def main():
    """Função principal para executar a aplicação"""
    print("🚀 Iniciando MCP Agent DB...")
    print("📚 Documentação disponível em: http://localhost:8000/docs")
    print("🌐 Interface web em: http://localhost:8000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
