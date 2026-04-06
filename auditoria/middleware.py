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
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
UserModel = get_user_model()

def resolver_usuario_no_banco(usuario, banco):
    if not usuario:
        return None
    pk = getattr(usuario, 'pk', None)
    if pk is None:
        return None
    try:
        return UserModel.objects.using(banco).filter(pk=pk).first()
    except Exception:
        return None

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
        # Padrões comuns de URL da API REST e WEB
        # /api/licenca/app/modelo/id/ ou /web/licenca/app/action/id
        # Atualizado para suportar listagens (sem modelo/ação explícito) e ações extras
        padrao = r'/(?:api|web)/([^/]+)/([^/]+)(?:/([^/]+))?/?(?:([0-9]+))?'
        match = re.search(padrao, url)
        
        if match:
            licenca_slug = match.group(1)  # casaa, por exemplo
            app_name = match.group(2)      # entidades
            modelo_name = match.group(3)   # entidades ou ação
            objeto_id = match.group(4)     # 77
            
            # Se não tiver modelo_name (ex: /web/slug/app/), infere do app
            if not modelo_name:
                modelo_name = 'infer_from_app'
            
            # Se o terceiro segmento for numérico, assume que é o ID e o modelo deve ser inferido do app
            if modelo_name and modelo_name.isdigit():
                objeto_id = modelo_name
                modelo_name = 'infer_from_app'
            
            # Mapear nomes de apps para os nomes reais dos apps Django
            app_mapping = {
                'Assistente_Spart': 'Assistente_Spart',  
                'assistente_spart': 'Assistente_Spart',
                'assistente': 'Assistente_Spart',
                'auditoria': 'auditoria',
                'gestao-obras': 'GestaoObras',
                'gestaoobras': 'GestaoObras',
                'boletos': 'boletos',
                'caixadiario': 'CaixaDiario',
                'caixa-diario': 'CaixaDiario',
                'centraldeajuda': 'centraldeajuda',
                'centrodecustos': 'CentrodeCustos',
                'cfop': 'CFOP',
                'cfops': 'CFOP',
                'contas_a_pagar': 'contas_a_pagar',
                'contas_a_receber': 'contas_a_receber',
                'contratos': 'contratos',
                'controledevisitas': 'controledevisitas',
                'dashboards': 'dashboards',
                'entidades': 'Entidades',
                'entradas_estoque': 'Entradas_Estoque',
                'enviocobranca': 'EnvioCobranca',
                'financeiro': 'Financeiro',
                'importador': 'importador',
                'licencas': 'Licencas',
                'listacasamento': 'listacasamento',
                'onboarding': 'onboarding',
                'o_s': 'O_S',
                'ordemdeservico': 'OrdemdeServico',
                'orcamentos': 'Orcamentos',
                'parametros_admin': 'parametros_admin',
                'permissoes_modulos': 'permissoes_modulos',
                'produtos': 'Produtos',
                'pedidos': 'Pedidos',
                'pisos': 'Pisos',  
                'saidas_estoque': 'Saidas_Estoque',
                'notasfiscais': 'Notas_Fiscais',
                'notas_fiscais': 'Notas_Fiscais',
                'series': 'series',     
                'transportes': 'transportes',

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
                'assistente_spart': 'Assistente_Spart',
                'assistente': 'Assistente_Spart',
                'notas-fiscais': 'Nota',
                'pedidos-geral': 'PedidoVenda',
                'pedidos': 'PedidoVenda',
                'entidades': 'Entidades',
                'caixa': 'Caixageral',
                'movicaixa': 'Movicaixa',
                'ctes': 'Cte',
                'veiculos': 'Veiculos',
                'regras': 'RegraICMS',
                'ncm-fiscal-padrao': 'NcmFiscalPadrao',
                'ncmfiscalpadrao': 'NcmFiscalPadrao',
                'criar': 'ignore',
                'novo': 'ignore',
                'adicionar': 'ignore',
                'cadastrar': 'ignore',
                'editar': 'ignore',
                'visualizar': 'ignore',
                'excluir': 'ignore',
                'imprimir': 'ignore',
                'transformar': 'ignore',
                'detalhe': 'ignore',
                'dashboard': 'ignore',
                'por-cliente': 'ignore',
                'emitir-nfe': 'ignore',
                'cancelar': 'ignore',
                'duplicar': 'ignore',
                'baixar': 'ignore',
                'faturar': 'ignore',
                'preco': 'ignore',
                'autocomplete': 'ignore',
                'processamento': 'ignore',
                'venda': 'ignore',
                'saldo': 'ignore',
                'resumo': 'ignore',
                'abertos': 'ignore',
                'obras': 'Obra',
                'etapas': 'ObraEtapa',
                'materiais': 'ObraMaterialMovimento',
                'financeiro': 'ObraLancamentoFinanceiro',
                'processos': 'ObraProcesso',
            }
            
            # Usar o nome real do app
            real_app_name = app_mapping.get(app_name.lower(), app_name)
            
            # Usar o nome real do modelo se houver mapeamento
            real_modelo_name = modelo_mapping.get(modelo_name, modelo_name)

            if app_name.lower() == 'produtos' and real_modelo_name == 'NcmFiscalPadrao':
                real_app_name = 'CFOP'

            if real_modelo_name == 'ignore' or real_modelo_name == 'infer_from_app':
                if app_name.lower() == 'orcamentos':
                    real_modelo_name = 'Orcamentos'
                elif app_name.lower() == 'pedidos':
                    real_modelo_name = 'PedidoVenda'
                elif app_name.lower() in ('caixadiario', 'caixa-diario'):
                    real_modelo_name = 'Caixageral'
                elif app_name.lower() == 'entidades':
                    real_modelo_name = 'Entidades'
                elif app_name.lower() == 'produtos':
                    real_modelo_name = 'Produtos'
                elif app_name.lower() == 'notasfiscais' or app_name.lower() == 'notas_fiscais':
                    real_modelo_name = 'Nota'
                elif app_name.lower() == 'financeiro':
                    # Financeiro é muito genérico, mas pode ser Títulos
                    pass
                elif app_name.lower() == 'transportes':
                    # Transportes não tem um modelo único, melhor ignorar do que tentar carregar
                    pass
            
            # Tentar obter o modelo real
            try:
                # Evita tentar carregar modelos "ignore" ou "infer_from_app" que falharam na inferência
                if real_modelo_name in ('ignore', 'infer_from_app'):
                    return None, objeto_id

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
            
            # Tratamento especial para Entidades duplicadas (forçar empresa 1)
            if modelo.__name__ == 'Entidades':
                 # Tenta filtrar com enti_empr=1 primeiro
                 qs = modelo.objects.filter(pk=objeto_id)
                 if hasattr(modelo, 'enti_empr'):
                     qs = qs.filter(enti_empr=1)
                 objeto = qs.first()
                 
                 # Se não achar com filtro de empresa, tenta sem (fallback)
                 if not objeto:
                     objeto = modelo.objects.filter(pk=objeto_id).first()
            else:
                objeto = modelo.objects.filter(pk=objeto_id).first()

            if not objeto:
                logger.debug(f'Objeto não encontrado via filter().first(): {modelo.__name__} ID {objeto_id}')
                return None
                
            dados = model_to_dict(objeto)
            logger.debug(f'Dados antes capturados com sucesso: {len(dados)} campos')
            return dados
        except (ValueError) as e:
            logger.debug(f'Erro de valor ao obter objeto: {modelo.__name__} ID {objeto_id} - Erro: {str(e)}')
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
        if not request.path.startswith('/api/') and not request.path.startswith('/web/'):
            return self.get_response(request)

        # Ignorar logs para rotas de auditoria e notificações
        if '/auditoria/' in request.path or '/notificacoes/' in request.path:
            pass
            return self.get_response(request)

        # Ignorar logs para endpoints de configuração que podem ser acessados sem autenticação
        if '/parametros-admin/' in request.path and request.method == 'GET':
            pass
            return self.get_response(request)


        # Ignorar endpoint público de mapa de licenças e signup de trial
        if request.path.startswith('/api/licencas/mapa/') or request.path.startswith('/api/planos/signup/trial/'):
            return self.get_response(request)

        try:
            parts = request.path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'api':
                # Endpoints públicos/essenciais (login, refresh, auth)
                if (len(parts) >= 4 and parts[2] == 'licencas' and parts[3] == 'login') \
                   or (len(parts) >= 4 and parts[2] == 'entidades' and parts[3] == 'login') \
                   or (len(parts) >= 3 and parts[2] == 'auth') \
                   or (len(parts) >= 2 and parts[1] in ('schema', 'swagger')):
                    pass
                else:
                    app_candidate = parts[2]
                    # Rotas especiais cujo app real é notas_fiscais
                    # /api/emitir/<slug>/<id>/, /api/imprimir/<slug>/<id>/ e /api/calcular/<slug>/<id>/
                    if parts[1] in ('emitir', 'imprimir', 'calcular') and len(parts) >= 3:
                        app_candidate = 'notas_fiscais'
                    modulos = getattr(request, 'modulos_disponiveis', []) or get_modulos_disponiveis()
                    modulos_lower = {str(m).lower() for m in modulos}
                    app_slug = str(app_candidate).lower()

                    aliases = {
                        'os': ['o_s', 'ordemdeservico'],
                        'o_s': ['os', 'ordemdeservico'],
                        'ordemdeservico': ['o_s', 'os'],
                        # Normalizações para notas fiscais
                        'notasfiscais': ['notas_fiscais', 'notas-fiscais', 'notas fiscais'],
                        'notas_fiscais': ['notasfiscais', 'notas-fiscais', 'notas fiscais'],
                        'notas-fiscais': ['notasfiscais', 'notas_fiscais', 'notas fiscais'],
                         'assistente': ['assistente_spart'],
                         'assistente_spart': ['assistente'],
                         'cfops': ['cfop'],
                        'gestao-obras': ['gestaoobras'],
                        'gestaoobras': ['gestao-obras'],
                    }
                    candidates = {app_slug}
                    for alt in aliases.get(app_slug, []):
                        candidates.add(alt)

                    allowed = any(c in modulos_lower for c in candidates)
                    if not allowed and not request.path.startswith('/api/auditoria/'):
                        from django.http import JsonResponse

                        licenca_slug = get_licenca_slug()
                        empresa = getattr(request, 'empresa', None)
                        filial = getattr(request, 'filial', None)

                        logger.warning(
                            "Módulo bloqueado para licença=%s empresa=%s filial=%s app=%s modulos_liberados=%s",
                            licenca_slug,
                            empresa,
                            filial,
                            app_slug,
                            sorted(modulos_lower),
                        )

                        return JsonResponse(
                            {
                                'erro': 'Módulo não liberado para a empresa/filial atual.',
                                'modulo_bloqueado': app_slug,
                                'modulos_liberados': sorted(modulos_lower),
                                'licenca': licenca_slug,
                                'empresa': empresa,
                                'filial': filial,
                            },
                            status=403,
                        )
        except Exception:
            pass

        # Determinar método lógico (para tratar POST em Web como DELETE/PUT se URL indicar)
        logical_method = request.method
        if request.method == 'POST':
            path_lower = request.path.lower()
            if path_lower.endswith('/excluir/') or '/delete/' in path_lower or '/remover/' in path_lower or '/cancelar/' in path_lower or '/deletar/' in path_lower:
                logical_method = 'DELETE'
            elif path_lower.endswith('/editar/') or '/update/' in path_lower or '/alterar/' in path_lower or '/modificar/' in path_lower or '/editar/' in path_lower:
                logical_method = 'PUT'

        # Capturar dados antes da alteração (para PUT, PATCH, DELETE)
        dados_antes = None
        modelo = None
        objeto_id = None
        
        if logical_method in ['PUT', 'PATCH', 'DELETE']:
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
        if logical_method in ['POST', 'PUT', 'PATCH']:
            try:
                if isinstance(request, Request):
                    # Capturar dados antes da view processar
                    data = getattr(request, '_cached_data', None)
                    if data is None:
                        data = request.data
                        request._cached_data = data
                else:
                    # Tenta capturar dados de formulário POST padrão Django
                    if hasattr(request, 'POST') and request.POST:
                        data = request.POST.dict()
                    else:
                        data = request.body.decode('utf-8') if request.body else None

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        pass # Mantém como string se não for JSON válido
            except Exception as e:
                logger.warning(f'Erro ao processar dados da requisição: {str(e)}')
                # Não sobrescreve data com None se apenas o json.loads falhou (já tratado acima)
                if 'data' not in locals():
                    data = None

        # Processar a resposta
        response = self.get_response(request)

        try:
            # Capturar informações após o processamento da ação
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            method = logical_method
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
            
            if logical_method in ['POST', 'PUT', 'PATCH']:
                dados_depois = self.processar_dados_resposta(response)
                
                # Para atualizações, comparar dados antes e depois
                if logical_method in ['PUT', 'PATCH'] and dados_antes and dados_depois:
                    campos_alterados = self.comparar_dados(dados_antes, dados_depois)
                    pass
            
            # Para DELETE, usar dados_antes como dados_depois (o que foi excluído)
            elif logical_method == 'DELETE' and dados_antes:
                dados_depois = dados_antes

            # Extrair informações do modelo se ainda não foram obtidas
            if not modelo or not objeto_id:
                modelo, objeto_id = self.extrair_modelo_e_id_da_url(request.path)
            
            # Extrair o nome da empresa da URL (licença)
            path_parts = request.path.strip('/').split('/')
            empresa = path_parts[1] if len(path_parts) > 1 else None  # /api/<slug>/...
            if len(path_parts) > 2 and path_parts[0] == 'api' and path_parts[1] in ('emitir', 'imprimir', 'calcular'):
                empresa = path_parts[2]

            # Debug dos dados que serão salvos
            pass
            
            # Converter dados para tipos serializáveis em JSON
            # Serializar objetos Python diretamente (sem json.dumps) para JSONField
            banco = get_licenca_db_config(request)
            
            dados_json = None
            dados_antes_json = None
            dados_depois_json = None
            campos_alterados_json = None

            try:
                data_serializavel = converter_para_json_serializavel(data) if data else None
                dados_json = json.dumps(data_serializavel, ensure_ascii=False) if data_serializavel is not None else None
            except Exception as e:
                logger.error(f"Erro ao serializar dados (input): {e}")

            try:
                dados_antes_serializavel = converter_para_json_serializavel(dados_antes) if dados_antes else None
                dados_antes_json = json.dumps(dados_antes_serializavel, ensure_ascii=False) if dados_antes_serializavel is not None else None
            except Exception as e:
                logger.error(f"Erro ao serializar dados_antes: {e}")

            try:
                dados_depois_serializavel = converter_para_json_serializavel(dados_depois) if dados_depois else None
                dados_depois_json = json.dumps(dados_depois_serializavel, ensure_ascii=False) if dados_depois_serializavel is not None else None
            except Exception as e:
                logger.error(f"Erro ao serializar dados_depois: {e}")

            try:
                campos_alterados_serializavel = converter_para_json_serializavel(campos_alterados) if campos_alterados else None
                campos_alterados_json = json.dumps(campos_alterados_serializavel, ensure_ascii=False) if campos_alterados_serializavel is not None else None
            except Exception as e:
                logger.error(f"Erro ao serializar campos_alterados: {e}")
            
            # Tratamento especial para Notas Fiscais (logging detalhado)
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
                            logger.info(f"Nota Fiscal Payload: {json.dumps(printable, ensure_ascii=False)}")
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
                                logger.info(fmt_nota(printable))
                            except Exception:
                                pass
                if '/notasfiscais/notas-fiscais/emitir/' in url and isinstance(dados_depois_serializavel, dict):
                    xml_str = dados_depois_serializavel.get('xml')
                    if xml_str:
                        try:
                            from xml.dom import minidom
                            parsed = minidom.parseString(xml_str)
                            logger.info(f"XML NFe: {parsed.toprettyxml(indent='  ')}")
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Erro no logging detalhado de NFe: {e}")
            
            # Criar o log no banco da licença
            try:
                usuario_no_banco = resolver_usuario_no_banco(user, banco)
                log = LogAcao.objects.using(banco).create(
                    usuario=usuario_no_banco,
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
            except Exception as e:
                logger.error(f"FATAL: Erro ao criar registro LogAcao: {e}")

        except Exception as e:
            logger.error(f"Erro não tratado no AuditoriaMiddleware: {e}", exc_info=True)
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
