from django.conf import settings
from django.db import connections, OperationalError
from Produtos.models import Ncm
import requests

def ensure_savexml1_connection():
    """
    Garante que a conexão com o banco savexml1 (Tabela TIPI/NCM compartilhada) exista.
    Assume que o banco reside no mesmo host do banco padrão.
    """
    if 'savexml1' not in settings.DATABASES:
        # Clona a configuração do banco default
        db_conf = settings.DATABASES['default'].copy()
        # Altera o nome do banco para savexml1
        db_conf['NAME'] = 'savexml1'
        # Adiciona à configuração em tempo de execução
        settings.DATABASES['savexml1'] = db_conf

def buscar_sugestoes_brasil_api(ncm_codigo):
    """
    Busca sugestões de NCM na BrasilAPI (gratuita e atualizada).
    Retorna lista de dicionários com sugestões.
    """
    sugestoes = []
    try:
        # Busca por NCMs similares (mesma posição - 4 primeiros dígitos)
        # A BrasilAPI permite busca por código ou descrição
        prefixo = ncm_codigo[:4]
        response = requests.get(f"https://brasilapi.com.br/api/ncm/v1?search={prefixo}", timeout=5)
        
        if response.status_code == 200:
            dados = response.json()
            # Filtra para pegar apenas os que começam com o prefixo e não são o próprio código inválido
            similares = [
                item for item in dados 
                if item['codigo'].replace('.', '').startswith(prefixo) 
                and item['codigo'].replace('.', '') != ncm_codigo
            ]
            
            # Ordena e limita
            similares = sorted(similares, key=lambda x: x['codigo'])[:5]
            
            if similares:
                sugestoes.append({
                    'tipo': 'titulo_sugestao_api',
                    'mensagem': "Sugestões da BrasilAPI (Tabela TIPI Atualizada):"
                })
                for item in similares:
                    codigo_limpo = item['codigo'].replace('.', '')
                    sugestoes.append({
                        'codigo': codigo_limpo,
                        'descricao': item['descricao'],
                        'tipo': 'similar_api',
                        'mensagem': f"{codigo_limpo} ({item['descricao']})"
                    })
                    
    except Exception as e:
        print(f"Erro ao consultar BrasilAPI: {e}")
        
    return sugestoes

def buscar_sugestoes_ncm(ncm_codigo):
    """
    Busca sugestões de NCM na tabela compartilhada (savexml1) baseada no código informado.
    Retorna uma lista de dicionários com código e descrição.
    """
    ensure_savexml1_connection()
    
    sugestoes = []
    try:
        # 1. Tenta buscar o NCM exato no banco compartilhado
        # Se existir lá, mas deu erro 778 na SEFAZ, provavelmente está extinto
        ncm_exato = Ncm.objects.using('savexml1').filter(ncm_codi=ncm_codigo).first()
        if ncm_exato:
            sugestoes.append({
                'codigo': ncm_exato.ncm_codi,
                'descricao': ncm_exato.ncm_desc,
                'tipo': 'exato_compartilhado',
                'mensagem': f"O NCM {ncm_codigo} consta na tabela interna, mas foi rejeitado pela SEFAZ (provavelmente extinto)."
            })

        # 2. Busca por similaridade na BrasilAPI (Tabela Oficial e Atualizada)
        # Prioriza a API pois ela tem a tabela TIPI mais recente
        sugestoes_api = buscar_sugestoes_brasil_api(ncm_codigo)
        if sugestoes_api:
            sugestoes.extend(sugestoes_api)
        else:
            # Fallback: Se API falhar, busca na tabela interna
            if len(ncm_codigo) >= 4:
                prefixo = ncm_codigo[:4]
                # Busca NCMs que NÃO sejam o próprio (já que ele deu erro)
                similares = Ncm.objects.using('savexml1').filter(ncm_codi__startswith=prefixo).exclude(ncm_codi=ncm_codigo).order_by('ncm_codi')[:5]
                
                if similares:
                    sugestoes.append({
                        'tipo': 'titulo_sugestao',
                        'mensagem': "Tente um destes NCMs ativos do mesmo grupo (Base Interna):"
                    })
                    for ncm in similares:
                        sugestoes.append({
                            'codigo': ncm.ncm_codi,
                            'descricao': ncm.ncm_desc,
                            'tipo': 'similar',
                            'mensagem': f"{ncm.ncm_codi} ({ncm.ncm_desc})"
                        })
                
    except Exception as e:
        # Falha silenciosa para não quebrar o fluxo principal se o banco compartilhado estiver inacessível
        print(f"Erro ao buscar sugestões de NCM: {e}")
        return []

    return sugestoes
