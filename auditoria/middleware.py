from django.utils import timezone
from .models import LogAcao
from core.middleware import get_licenca_slug, get_modulos_disponiveis
from rest_framework.request import Request
from django.forms.models import model_to_dict
from django.apps import apps
from django.utils import timezone
import logging
import json
import re
from datetime import date, datetime
from pprint import pformat
from decimal import Decimal
from core.utils import get_licenca_db_config

logger = logging.getLogger(__name__)

def converter_para_json_serializavel(obj):
    """Converte objetos Python para tipos serializáveis em JSON"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: converter_para_json_serializavel(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [converter_para_json_serializavel(item) for item in obj]
    else:
        return obj

class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    

    def extrair_modelo_e_id_da_url(self, url):
        """Extrai o nome do modelo e ID do objeto da URL"""
        # Padrões comuns de URL da API REST
        # /api/licenca/app/modelo/id/ ou /api/licenca/app/modelo/id
        padrao = r'/api/([^/]+)/([^/]+)/([^/]+)/?(?:([0-9]+)/?)?'
        match = re.search(padrao, url)
        
        if match:
            licenca_slug = match.group(1)  # casaa, por exemplo
            app_name = match.group(2)      # entidades
            modelo_name = match.group(3)   # entidades
            objeto_id = match.group(4)     # 77
            
            # Mapear nomes de apps para os nomes reais dos apps Django
            app_mapping = {
                'Assistente_Spart': 'Assistente_Spart',  
                'auditoria': 'auditoria',
                'boletos': 'Boletos',
                'caixadiario': 'CaixaDiario',
                'centraldeajuda': 'CentralDeAjuda',
                'centrodecustos': 'CentroDeCustos',
                'cfop': 'Cfop',
                'contas_a_pagar': 'contas_a_pagar',
                'contas_a_receber': 'contas_a_receber',
                'contratos': 'contratos',
                'controledevisitas': 'ControleDeVisitas',
                'dashboards': 'dashboards',
                'entidades': 'Entidades',
                'entradas_estoque': 'Entradas_Estoque',
                'enviocobranca': 'Enviocobranca',
                'financeiro': 'Financeiro',
                'importador': 'Importador',
                'licencas': 'Licencas',
                'listacasamento': 'listacasamento',
                'onboarding': 'Onboarding',
                'o_s': 'O_S',
                'ordemdeservico': 'OrdemdeServico',
                'orcamentos': 'Orcamentos',
                'parametros_admin': 'parametros_admin',
                'permissoes_modulos': 'permissoes_modulos',
                'produtos': 'Produtos',
                'pedidos': 'Pedidos',
                'pisos': 'Pisos',  
                'saidas_estoque': 'Saidas_Estoque',      
                'series': 'Series',     

            }
            
            # Mapear nomes de modelos com hífen para nomes reais dos modelos
            modelo_mapping = {
                
                'titulos-pagar': 'Titulospagar',
                'titulos-receber': 'Titulosreceber',
                'ordemdeservico': 'OrdemdeServico',
                'orcamentos': 'Orcamentos',
                'listacasamento': 'listacasamento',
                'contratos': 'contratos',
                'dashboards': 'dashboards',
                'auditoria': 'auditoria',
                'parametros_admin': 'parametros_admin',
                'permissoes_modulos': 'permissoes_modulos',
                'pisos': 'Pisos',
                'Assistente_Spart': 'Assistente_Spart',               

            }
            
            # Usar o nome real do app
            real_app_name = app_mapping.get(app_name.lower(), app_name)
            
            # Usar o nome real do modelo se houver mapeamento
            real_modelo_name = modelo_mapping.get(modelo_name, modelo_name)
            
            # Tentar obter o modelo real
            try:
                modelo = apps.get_model(real_app_name, real_modelo_name)
                logger.debug(f'Modelo encontrado: {real_app_name}.{real_modelo_name}')
                return modelo, objeto_id
            except LookupError:
                logger.debug(f'Modelo não encontrado: {real_app_name}.{real_modelo_name} (tentativa com {app_name}.{modelo_name})')
                # Tentar com o nome original como fallback
                try:
                    modelo = apps.get_model(app_name, modelo_name)
                    logger.debug(f'Modelo encontrado com fallback: {app_name}.{modelo_name}')
                    return modelo, objeto_id
                except LookupError:
                    logger.debug(f'Modelo não encontrado nem com fallback: {app_name}.{modelo_name}')
                    return None, objeto_id
        
        return None, None
    
    def obter_dados_objeto(self, modelo, objeto_id):
        """Obtém os dados atuais de um objeto antes da alteração"""
        if not modelo or not objeto_id:
            logger.debug(f'Modelo ou ID não fornecido: modelo={modelo}, objeto_id={objeto_id}')
            return None
        
        try:
            logger.debug(f'Tentando obter dados antes para {modelo.__name__} ID {objeto_id}')
            objeto = modelo.objects.get(pk=objeto_id)
            dados = model_to_dict(objeto)
            logger.debug(f'Dados antes capturados com sucesso: {len(dados)} campos')
            return dados
        except (modelo.DoesNotExist, ValueError) as e:
            logger.debug(f'Objeto não encontrado: {modelo.__name__} ID {objeto_id} - Erro: {str(e)}')
            return None
        except Exception as e:
            logger.error(f'Erro inesperado ao obter dados antes: {modelo.__name__} ID {objeto_id} - Erro: {str(e)}')
            return None
    
    def comparar_dados(self, dados_antes, dados_depois):
        """Compara dois dicionários e retorna as diferenças"""
        if not dados_antes or not dados_depois:
            return None
        
        alteracoes = {}
        
        # Verificar campos alterados
        for campo, valor_depois in dados_depois.items():
            valor_antes = dados_antes.get(campo)
            
            # Converter para string para comparação consistente
            str_antes = str(valor_antes) if valor_antes is not None else None
            str_depois = str(valor_depois) if valor_depois is not None else None
            
            if str_antes != str_depois:
                alteracoes[campo] = {
                    'antes': valor_antes,
                    'depois': valor_depois
                }
        
        # Verificar campos removidos
        for campo, valor_antes in dados_antes.items():
            if campo not in dados_depois:
                alteracoes[campo] = {
                    'antes': valor_antes,
                    'depois': None
                }
        
        return alteracoes if alteracoes else None
    
    def processar_dados_resposta(self, response):
        """Extrai dados da resposta para capturar estado posterior"""
        try:
            if hasattr(response, 'data') and response.data:
                return response.data
            elif hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                if content:
                    return json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            pass
        
        return None
    #Vamos chamar o middleware apenas para as rotas da api de todos os apps, em todos os metodos http
    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Ignorar logs para rotas de auditoria (exceto a rota principal)
        # Ignorar logs para rotas de auditoria e notificações
        if '/auditoria/logs/' in request.path or '/notificacoes/' in request.path:
            pass
            return self.get_response(request)

        # Ignorar logs para endpoints de configuração que podem ser acessados sem autenticação
        if '/parametros-admin/' in request.path and request.method == 'GET':
            pass
            return self.get_response(request)


        # Ignorar endpoint público de mapa de licenças
        if request.path.startswith('/api/licencas/mapa/'):
            return self.get_response(request)

        # Verificação de permissão por módulo
        try:
            parts = request.path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'api':
                # Endpoints públicos/essenciais (login, refresh, mapa)
                if (len(parts) >= 4 and parts[2] == 'licencas' and parts[3] == 'login') \
                   or (len(parts) >= 4 and parts[2] == 'entidades' and parts[3] == 'login') \
                   or (len(parts) >= 3 and parts[2] == 'auth'):
                    return self.get_response(request)

                # Documentação da API não deve ter associação a módulos
                if request.path.startswith('/api/schema/') \
                   or request.path.startswith('/api/schemas/') \
                   or request.path.startswith('/api/swagger'):
                    return self.get_response(request)

                # Endpoints de licenças (empresas/filiais e afins) não devem ser bloqueados
                if parts[2] in ['licencas', 'dashboards']:
                    return self.get_response(request)

                app_candidate = parts[2]
                modulos = getattr(request, 'modulos_disponiveis', []) or get_modulos_disponiveis()
                modulos_lower = {m.lower() for m in modulos}
                app_slug = app_candidate.lower()

                aliases = {
                    'os': ['o_s', 'ordemdeservico'],
                    'o_s': ['os', 'ordemdeservico'],
                    'ordemdeservico': ['o_s', 'os'],
                }
                candidates = {app_slug}
                for alt in aliases.get(app_slug, []):
                    candidates.add(alt)

                allowed = any(c in modulos_lower for c in candidates)
                if not allowed and not request.path.startswith('/api/auditoria/'):
                    from django.http import JsonResponse
                    return JsonResponse({'erro': 'Módulo não liberado para a empresa/filial atual.'}, status=403)
        except Exception:
            pass

        # Capturar dados antes da alteração (para PUT, PATCH, DELETE)
        dados_antes = None
        modelo = None
        objeto_id = None
        
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            pass
            modelo, objeto_id = self.extrair_modelo_e_id_da_url(request.path)
            pass
            if modelo and objeto_id:
                dados_antes = self.obter_dados_objeto(modelo, objeto_id)
                if dados_antes:
                    pass
                else:
                    logger.warning(f'Falha ao capturar dados antes para {modelo.__name__} ID {objeto_id}')
            else:
                pass

        # Tentar obter os dados da requisição ANTES de processar a resposta
        data = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if isinstance(request, Request):
                    # Capturar dados antes da view processar
                    data = getattr(request, '_cached_data', None)
                    if data is None:
                        data = request.data
                        request._cached_data = data
                else:
                    data = request.body.decode('utf-8') if request.body else None

                if isinstance(data, str):
                    data = json.loads(data)
            except Exception as e:
                logger.warning(f'Erro ao processar dados da requisição: {str(e)}')
                data = None

        # Processar a resposta
        response = self.get_response(request)

        try:
            # Capturar informações após o processamento da ação
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            method = request.method
            url = request.path
            ip = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Define a licença como 'auditoria' para endpoints de auditoria
            if request.path.startswith('/api/auditoria/'):
                licenca_slug = 'auditoria'

            else:
                licenca_slug = get_licenca_slug()

            # Log detalhado das informações capturadas
            pass

            # Debug log inicial
            pass

            # Verificações detalhadas de usuário e licença
            # Permitir endpoints públicos sem autenticação
            if (request.path.startswith('/api/licencas/mapa/') or 
                '/licencas/login/' in request.path or
                '/parametros-admin/configuracao-inicial/' in request.path):
                logger.info(f'Endpoint público acessado: {url}')
                return response

            if not user:
                logger.warning(f'Log ignorado - Usuário não autenticado: {url}')
                return response
            
            if not licenca_slug:
                logger.warning(f'Log ignorado - Licença não encontrada: {url} (usuário: {user})')
                return response

            # Dados já foram capturados antes do processamento da resposta
            # Remover a captura duplicada aqui

            # Capturar dados depois da alteração
            dados_depois = None
            campos_alterados = None
            
            if request.method in ['POST', 'PUT', 'PATCH']:
                dados_depois = self.processar_dados_resposta(response)
                
                # Para atualizações, comparar dados antes e depois
                if request.method in ['PUT', 'PATCH'] and dados_antes and dados_depois:
                    campos_alterados = self.comparar_dados(dados_antes, dados_depois)
                    pass
            
            # Para DELETE, usar dados_antes como dados_depois (o que foi excluído)
            elif request.method == 'DELETE' and dados_antes:
                dados_depois = dados_antes

            # Extrair informações do modelo se ainda não foram obtidas
            if not modelo or not objeto_id:
                modelo, objeto_id = self.extrair_modelo_e_id_da_url(request.path)
            
            # Extrair o nome da empresa da URL (licença)
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None  # casaa, por exemplo

            # Debug dos dados que serão salvos
            pass
            
            # Converter dados para tipos serializáveis em JSON
            # Serializar objetos Python diretamente (sem json.dumps) para JSONField
            banco = get_licenca_db_config(request)
            data_serializavel = converter_para_json_serializavel(data) if data else None
            dados_antes_serializavel = converter_para_json_serializavel(dados_antes) if dados_antes else None
            dados_depois_serializavel = converter_para_json_serializavel(dados_depois) if dados_depois else None
            campos_alterados_serializavel = converter_para_json_serializavel(campos_alterados) if campos_alterados else None
            
            # Ajuste: serializar para string JSON para evitar erros de encoding em bancos não UTF8
            dados_json = json.dumps(data_serializavel, ensure_ascii=False) if data_serializavel is not None else None
            dados_antes_json = json.dumps(dados_antes_serializavel, ensure_ascii=False) if dados_antes_serializavel is not None else None
            dados_depois_json = json.dumps(dados_depois_serializavel, ensure_ascii=False) if dados_depois_serializavel is not None else None
            campos_alterados_json = json.dumps(campos_alterados_serializavel, ensure_ascii=False) if campos_alterados_serializavel is not None else None

            try:
                if '/notasfiscais/notas-fiscais/notas/' in url and method in ['POST', 'PUT', 'PATCH']:
                    base_payload = dados_depois if dados_depois is not None else data
                    if base_payload is not None:
                        try:
                            printable = base_payload
                            if isinstance(printable, str):
                                try:
                                    printable = json.loads(printable)
                                except Exception:
                                    import ast
                                    try:
                                        printable = ast.literal_eval(printable)
                                    except Exception:
                                        printable = {"raw": printable}
                            printable = converter_para_json_serializavel(printable)
                            pass
                        except Exception:
                            pass
                        if isinstance(printable, dict):
                            try:
                                def fmt_nota(p):
                                    linhas = []
                                    nid = p.get('id') or p.get('nota')
                                    linhas.append(f"Nota id: {nid}")
                                    linhas.append(f"Modelo/Série/Número: {p.get('modelo')}-{p.get('serie')} #{p.get('numero')}")
                                    linhas.append(f"Datas: emissao={p.get('data_emissao')} saida={p.get('data_saida')}")
                                    emi = p.get('emitente') or {}
                                    linhas.append(f"Emitente: {emi.get('empr_nome')} CNPJ={emi.get('empr_docu')}")
                                    dest = p.get('destinatario') or {}
                                    doc = dest.get('enti_cnpj') or dest.get('enti_cpf') or ''
                                    linhas.append(f"Destinatario: {dest.get('enti_nome')} Doc={doc}")
                                    linhas.append(f"Status/Ambiente: {p.get('status')}/{p.get('ambiente')}")
                                    linhas.append(f"Chave: {p.get('chave_acesso')} Protocolo: {p.get('protocolo_autorizacao')}")
                                    itens = p.get('itens') or []
                                    linhas.append(f"Itens: {len(itens)}")
                                    for i, it in enumerate(itens, 1):
                                        linhas.append(f"  Item {i} id={it.get('id')} prod={it.get('produto')} quant={it.get('quantidade')} unit={it.get('unitario')} desc={it.get('desconto')} total={it.get('total')} cfop={it.get('cfop')} ncm={it.get('ncm')} cst_icms={it.get('cst_icms')} cst_pis={it.get('cst_pis')} cst_cofins={it.get('cst_cofins')}")
                                        imp = it.get('impostos') or {}
                                        if imp:
                                            linhas.append(f"    Impostos: icms_base={imp.get('icms_base')} aliq={imp.get('icms_aliquota')} icms_valor={imp.get('icms_valor')} ipi={imp.get('ipi_valor')} pis={imp.get('pis_valor')} cofins={imp.get('cofins_valor')} fcp={imp.get('fcp_valor')}")
                                    tr = p.get('transporte') or {}
                                    if tr:
                                        linhas.append(f"Transporte: modalidade={tr.get('modalidade_frete')} placa={tr.get('placa_veiculo')} uf={tr.get('uf_veiculo')} transportadora={tr.get('transportadora')}")
                                    return "\n".join(linhas)
                                pass
                            except Exception:
                                pass
                if '/notasfiscais/notas-fiscais/emitir/' in url and isinstance(dados_depois_serializavel, dict):
                    xml_str = dados_depois_serializavel.get('xml')
                    if xml_str:
                        try:
                            from xml.dom import minidom
                            parsed = minidom.parseString(xml_str)
                            pass
                        except Exception:
                            pass
            except Exception:
                pass
            
            # Criar o log no banco da licença
            log = LogAcao.objects.using(banco).create(
                usuario=user,
                data_hora=timezone.now(),
                tipo_acao=method,
                url=url,
                ip=ip,
                navegador=user_agent,
                dados=dados_json,
                dados_antes=dados_antes_json,
                dados_depois=dados_depois_json,
                campos_alterados=campos_alterados_json,
                objeto_id=objeto_id,
                modelo=modelo.__name__ if modelo else None,
                empresa=empresa,
                licenca=licenca_slug
            )

            logger.info(f'Log criado com sucesso: {log.id} - {method} {url}')
            pass

        except Exception as e:
            logger.error(f'Erro ao criar log de auditoria: {str(e)}')
            logger.error(f'URL que causou o erro: {request.path}')
            logger.error(f'Método que causou o erro: {request.method}')
            logger.exception('Detalhes completos do erro:')

        try:
            mods = getattr(request, 'modulos_disponiveis', []) or get_modulos_disponiveis()
            if isinstance(mods, list):
                response['X-Modulos'] = ','.join(sorted(set(mods)))
        except Exception:
            pass
        return response
