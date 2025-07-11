from .models import ParametroSistema, Modulo
from core.utils import get_licenca_db_config
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def obter_parametros_estoque(empresa_id, filial_id, request):
    """
    Obtém todos os parâmetros de estoque para empresa/filial
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Buscar módulo de estoque
        modulo_estoque = Modulo.objects.using(banco).filter(
            modu_nome__icontains='estoque'
        ).first()
        
        if not modulo_estoque:
            logger.warning("Módulo de estoque não encontrado")
            return {}
        
        parametros_nomes = [
            'entrada_automatica_estoque',
            'saida_automatica_estoque', 
            'pedido_volta_estoque',
            'alerta_estoque_minimo',
            'permitir_estoque_negativo',
            'calculo_automatico_custo'
        ]
        
        parametros = {}
        for nome_param in parametros_nomes:
            param = ParametroSistema.objects.using(banco).filter(
                para_empr=empresa_id,
                para_fili=filial_id,
                para_modu=modulo_estoque,
                para_nome=nome_param
            ).first()
            
            parametros[nome_param] = {
                'valor': param.para_valo if param else 'false',
                'ativo': param.para_ativ if param else False,
                'existe': param is not None
            }
        
        return parametros
        
    except Exception as e:
        logger.error(f"Erro ao obter parâmetros de estoque: {e}")
        return {}


def verificar_entrada_automatica(empresa_id, filial_id, request):
    """
    Verifica se entrada automática está habilitada
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('entrada_automatica_estoque', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_saida_automatica(empresa_id, filial_id, request):
    """
    Verifica se saída automática está habilitada
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('saida_automatica_estoque', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_volta_estoque(empresa_id, filial_id, request):
    """
    Verifica se volta de estoque está habilitada
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('pedido_volta_estoque', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_alerta_estoque_minimo(empresa_id, filial_id, request):
    """
    Verifica se alerta de estoque mínimo está habilitado
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('alerta_estoque_minimo', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_estoque_negativo(empresa_id, filial_id, request):
    """
    Verifica se estoque negativo é permitido
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('permitir_estoque_negativo', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_calculo_automatico_custo(empresa_id, filial_id, request):
    """
    Verifica se cálculo automático de custo está habilitado
    """
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    param = parametros.get('calculo_automatico_custo', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def calcular_estoque_atual(produto_codigo, empresa_id, filial_id, request):
    """
    Calcula estoque atual de um produto
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Importar modelo de estoque
        from Produtos.models import Estoque
        
        estoque = Estoque.objects.using(banco).filter(
            esto_prod=produto_codigo,
            esto_empr=empresa_id,
            esto_fili=filial_id
        ).first()
        
        return estoque.esto_quan if estoque else Decimal('0.00')
        
    except Exception as e:
        logger.error(f"Erro ao calcular estoque atual: {e}")
        return Decimal('0.00')


def verificar_estoque_disponivel(produto_codigo, quantidade_solicitada, empresa_id, filial_id, request):
    """
    Verifica se há estoque disponível para a quantidade solicitada
    """
    try:
        estoque_atual = calcular_estoque_atual(produto_codigo, empresa_id, filial_id, request)
        
        # Verificar se estoque negativo é permitido
        permite_negativo = verificar_estoque_negativo(empresa_id, filial_id, request)
        
        if permite_negativo:
            return True, estoque_atual
        
        disponivel = estoque_atual >= Decimal(str(quantidade_solicitada))
        return disponivel, estoque_atual
        
    except Exception as e:
        logger.error(f"Erro ao verificar estoque disponível: {e}")
        return False, Decimal('0.00')


def processar_entrada_estoque(entrada_data, request):
    """
    Processa entrada de estoque baseada nos parâmetros
    """
    try:
        empresa_id = entrada_data.get('entr_empr')
        filial_id = entrada_data.get('entr_fili')
        produto_codigo = entrada_data.get('entr_prod')
        quantidade = entrada_data.get('entr_quan', 0)
        
        # Verificar se entrada automática está habilitada
        if not verificar_entrada_automatica(empresa_id, filial_id, request):
            return {
                'entrada_valida': False,
                'alertas': [{
                    'tipo': 'parametro_desabilitado',
                    'mensagem': 'Entrada automática de estoque está desabilitada'
                }]
            }
        
        # Verificar se deve calcular custo automaticamente
        calcular_custo = verificar_calculo_automatico_custo(empresa_id, filial_id, request)
        
        if calcular_custo and not entrada_data.get('entr_unit'):
            # Calcular custo médio ou último custo
            entrada_data['entr_unit'] = calcular_custo_automatico(
                produto_codigo, empresa_id, filial_id, request
            )
        
        # Verificar alerta de estoque mínimo após entrada
        alertas = []
        if verificar_alerta_estoque_minimo(empresa_id, filial_id, request):
            estoque_apos_entrada = calcular_estoque_atual(produto_codigo, empresa_id, filial_id, request) + Decimal(str(quantidade))
            alerta_minimo = verificar_estoque_minimo_produto(produto_codigo, estoque_apos_entrada, empresa_id, filial_id, request)
            if alerta_minimo:
                alertas.append(alerta_minimo)
        
        parametros_aplicados = obter_parametros_estoque(empresa_id, filial_id, request)
        
        return {
            'entrada_valida': True,
            'dados_processados': entrada_data,
            'parametros_aplicados': parametros_aplicados,
            'alertas': alertas
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar entrada de estoque: {e}")
        return {
            'entrada_valida': False,
            'alertas': [{
                'tipo': 'erro_interno',
                'mensagem': 'Erro interno ao processar entrada'
            }]
        }


def processar_saida_estoque(saida_data, request):
    """
    Processa saída de estoque baseada nos parâmetros
    """
    try:
        empresa_id = saida_data.get('said_empr')
        filial_id = saida_data.get('said_fili')
        produto_codigo = saida_data.get('said_prod')
        quantidade = saida_data.get('said_quan', 0)
        
        # Verificar se saída automática está habilitada
        if not verificar_saida_automatica(empresa_id, filial_id, request):
            return {
                'saida_valida': False,
                'alertas': [{
                    'tipo': 'parametro_desabilitado',
                    'mensagem': 'Saída automática de estoque está desabilitada'
                }]
            }
        
        # Verificar estoque disponível
        estoque_ok, estoque_atual = verificar_estoque_disponivel(
            produto_codigo, quantidade, empresa_id, filial_id, request
        )
        
        alertas = []
        if not estoque_ok:
            permite_negativo = verificar_estoque_negativo(empresa_id, filial_id, request)
            if not permite_negativo:
                return {
                    'saida_valida': False,
                    'alertas': [{
                        'tipo': 'estoque_insuficiente',
                        'mensagem': f'Estoque insuficiente. Disponível: {estoque_atual}, Solicitado: {quantidade}'
                    }]
                }
            else:
                alertas.append({
                    'tipo': 'estoque_negativo',
                    'mensagem': f'Saída resultará em estoque negativo. Atual: {estoque_atual}, Saída: {quantidade}'
                })
        
        # Verificar alerta de estoque mínimo após saída
        if verificar_alerta_estoque_minimo(empresa_id, filial_id, request):
            estoque_apos_saida = estoque_atual - Decimal(str(quantidade))
            alerta_minimo = verificar_estoque_minimo_produto(produto_codigo, estoque_apos_saida, empresa_id, filial_id, request)
            if alerta_minimo:
                alertas.append(alerta_minimo)
        
        parametros_aplicados = obter_parametros_estoque(empresa_id, filial_id, request)
        
        return {
            'saida_valida': True,
            'dados_processados': saida_data,
            'parametros_aplicados': parametros_aplicados,
            'alertas': alertas
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar saída de estoque: {e}")
        return {
            'saida_valida': False,
            'alertas': [{
                'tipo': 'erro_interno',
                'mensagem': 'Erro interno ao processar saída'
            }]
        }


def calcular_custo_automatico(produto_codigo, empresa_id, filial_id, request):
    """
    Calcula custo automático baseado no histórico
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Buscar último custo de entrada
        from Entradas_Estoque.models import ItensEntradaEstoque
        
        ultimo_item = ItensEntradaEstoque.objects.using(banco).filter(
            ient_prod=produto_codigo,
            ient_empr=empresa_id,
            ient_fili=filial_id
        ).order_by('-ient_codi').first()
        
        if ultimo_item:
            return ultimo_item.ient_unit
        
        # Se não encontrar, buscar na tabela de preços
        from Produtos.models import Tabelaprecos
        
        preco = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=produto_codigo,
            tabe_empr=empresa_id,
            tabe_fili=filial_id
        ).first()
        
        return preco.tabe_prco if preco else Decimal('0.00')
        
    except Exception as e:
        logger.error(f"Erro ao calcular custo automático: {e}")
        return Decimal('0.00')


def verificar_estoque_minimo_produto(produto_codigo, estoque_atual, empresa_id, filial_id, request):
    """
    Verifica se produto está abaixo do estoque mínimo
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Produtos.models import Produtos
        
        produto = Produtos.objects.using(banco).filter(
            prod_codi=produto_codigo,
            prod_empr=empresa_id,
            prod_fili=filial_id
        ).first()
        
        if produto and hasattr(produto, 'prod_mini'):
            estoque_minimo = produto.prod_mini or Decimal('0.00')
            
            if estoque_atual <= estoque_minimo:
                return {
                    'tipo': 'estoque_minimo',
                    'produto': produto_codigo,
                    'estoque_atual': estoque_atual,
                    'estoque_minimo': estoque_minimo,
                    'mensagem': f'Produto {produto_codigo} abaixo do estoque mínimo'
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao verificar estoque mínimo: {e}")
        return None


def reverter_saida_estoque(saida_id, request):
    """
    Reverte uma saída de estoque (volta estoque)
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Saidas_Estoque.models import SaidaEstoque, ItensSaidaEstoque
        
        saida = SaidaEstoque.objects.using(banco).get(said_codi=saida_id)
        
        # Verificar se volta de estoque está habilitada
        if not verificar_volta_estoque(saida.said_empr, saida.said_fili, request):
            return {
                'reversao_ok': False,
                'erro': 'Volta de estoque está desabilitada para esta empresa/filial'
            }
        
        # Buscar itens da saída
        itens = ItensSaidaEstoque.objects.using(banco).filter(isai_said=saida_id)
        
        estoque_restaurado = []
        for item in itens:
            # Restaurar estoque
            from Produtos.models import Estoque
            
            estoque, created = Estoque.objects.using(banco).get_or_create(
                esto_prod=item.isai_prod,
                esto_empr=saida.said_empr,
                esto_fili=saida.said_fili,
                defaults={'esto_quan': Decimal('0.00')}
            )
            
            estoque.esto_quan += item.isai_quan
            estoque.save()
            
            estoque_restaurado.append({
                'produto': item.isai_prod,
                'quantidade_restaurada': item.isai_quan,
                'estoque_atual': estoque.esto_quan
            })
        
        # Marcar saída como revertida
        saida.said_stat = 'REVERTIDA'
        saida.save()
        
        return {
            'reversao_ok': True,
            'estoque_restaurado': estoque_restaurado
        }
        
    except Exception as e:
        logger.error(f"Erro ao reverter saída de estoque: {e}")
        return {
            'reversao_ok': False,
            'erro': f'Erro interno: {str(e)}'
        }