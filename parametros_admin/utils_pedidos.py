from .models import ParametroSistema, Modulo
from core.utils import get_licenca_db_config
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def obter_parametros_pedidos(empresa_id, filial_id, request):
    """
    Obtém todos os parâmetros de pedidos para empresa/filial
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Buscar módulo de pedidos
        modulo_pedidos = Modulo.objects.using(banco).filter(
            modu_nome__icontains='pedido'
        ).first()
        
        if not modulo_pedidos:
            logger.warning("Módulo de pedidos não encontrado")
            return {}
        
        parametros_nomes = [
            'usar_preco_prazo',
            'usar_ultimo_preco',
            'desconto_pedido',
            'pedido_volta_estoque',
            'validar_estoque_pedido',
            'calcular_frete_automatico'
        ]
        
        parametros = {}
        for nome_param in parametros_nomes:
            param = ParametroSistema.objects.using(banco).filter(
                para_empr=empresa_id,
                para_fili=filial_id,
                para_modu=modulo_pedidos,
                para_nome=nome_param
            ).first()
            
            parametros[nome_param] = {
                'valor': param.para_valo if param else 'false',
                'ativo': param.para_ativ if param else False,
                'existe': param is not None
            }
        
        return parametros
        
    except Exception as e:
        logger.error(f"Erro ao obter parâmetros de pedidos: {e}")
        return {}


def verificar_usar_preco_prazo(empresa_id, filial_id, request):
    """
    Verifica se deve usar preço a prazo
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('usar_preco_prazo', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_usar_ultimo_preco(empresa_id, filial_id, request):
    """
    Verifica se deve usar último preço aplicado
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('usar_ultimo_preco', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_desconto_pedido(empresa_id, filial_id, request):
    """
    Verifica se desconto em pedido está habilitado
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('desconto_pedido', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_volta_estoque_pedido(empresa_id, filial_id, request):
    """
    Verifica se volta de estoque em pedido está habilitada
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('pedido_volta_estoque', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_validar_estoque_pedido(empresa_id, filial_id, request):
    """
    Verifica se deve validar estoque ao criar pedido
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('validar_estoque_pedido', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def obter_preco_produto(produto_codigo, empresa_id, filial_id, request, tipo_preco='normal'):
    """
    Obtém preço do produto baseado nos parâmetros configurados
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Verificar se deve usar preço a prazo
        if verificar_usar_preco_prazo(empresa_id, filial_id, request) and tipo_preco == 'prazo':
            preco_prazo = obter_preco_prazo(produto_codigo, empresa_id, filial_id, request)
            if preco_prazo:
                return preco_prazo
        
        # Verificar se deve usar último preço aplicado
        if verificar_usar_ultimo_preco(empresa_id, filial_id, request):
            ultimo_preco = obter_ultimo_preco_aplicado(produto_codigo, empresa_id, filial_id, request)
            if ultimo_preco:
                return ultimo_preco
        
        # Usar preço padrão da tabela
        from Produtos.models import Tabelaprecos
        
        preco_padrao = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=produto_codigo,
            tabe_empr=empresa_id,
            tabe_fili=filial_id
        ).first()
        
        return preco_padrao.tabe_prco if preco_padrao else Decimal('0.00')
        
    except Exception as e:
        logger.error(f"Erro ao obter preço do produto {produto_codigo}: {e}")
        return Decimal('0.00')


def obter_preco_prazo(produto_codigo, empresa_id, filial_id, request):
    """
    Obtém preço a prazo específico
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Produtos.models import Tabelaprecos
        
        # Buscar preço a prazo (assumindo que existe um campo tipo ou tabela específica)
        preco_prazo = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=produto_codigo,
            tabe_empr=empresa_id,
            tabe_fili=filial_id,
            # Adicionar filtro para preço a prazo quando campo existir
        ).first()
        
        return preco_prazo.tabe_prco if preco_prazo else None
        
    except Exception as e:
        logger.error(f"Erro ao obter preço a prazo: {e}")
        return None


def obter_ultimo_preco_aplicado(produto_codigo, empresa_id, filial_id, request):
    """
    Obtém o último preço aplicado para um produto em pedidos
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Pedidos.models import ItensPedido
        
        ultimo_item = ItensPedido.objects.using(banco).filter(
            iped_prod=produto_codigo,
            iped_empr=empresa_id,
            iped_fili=filial_id
        ).order_by('-iped_codi').first()
        
        return ultimo_item.iped_unit if ultimo_item else None
        
    except Exception as e:
        logger.error(f"Erro ao obter último preço aplicado: {e}")
        return None


def validar_desconto_pedido(desconto_percentual, valor_item, empresa_id, filial_id, request):
    """
    Valida se o desconto pode ser aplicado baseado nos parâmetros
    """
    try:
        # Verificar se desconto é permitido
        if not verificar_desconto_pedido(empresa_id, filial_id, request):
            raise ValidationError("Desconto não permitido em pedidos para esta empresa/filial")
        
        # Validações básicas
        if desconto_percentual < 0 or desconto_percentual > 100:
            raise ValidationError("Desconto deve estar entre 0% e 100%")
        
        # Aqui você pode adicionar outras validações específicas
        # como desconto máximo permitido, autorização necessária, etc.
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar desconto em pedido: {e}")
        raise ValidationError("Erro interno ao validar desconto")


def calcular_desconto(valor_original, desconto_percentual):
    """
    Calcula valor do desconto e valor final
    """
    if desconto_percentual <= 0:
        return Decimal('0.00'), valor_original
    
    valor_desconto = valor_original * (Decimal(str(desconto_percentual)) / 100)
    valor_final = valor_original - valor_desconto
    
    return valor_desconto, valor_final


def verificar_estoque_para_pedido(produto_codigo, quantidade, empresa_id, filial_id, request):
    """
    Verifica estoque disponível para pedido
    """
    try:
        # Verificar se validação de estoque está habilitada
        if not verificar_validar_estoque_pedido(empresa_id, filial_id, request):
            return True, "Validação de estoque desabilitada"
        
        # Usar função do utils_estoque
        from .utils_estoque import verificar_estoque_disponivel
        
        disponivel, estoque_atual = verificar_estoque_disponivel(
            produto_codigo, quantidade, empresa_id, filial_id, request
        )
        
        if not disponivel:
            return False, f"Estoque insuficiente. Disponível: {estoque_atual}, Solicitado: {quantidade}"
        
        return True, f"Estoque disponível: {estoque_atual}"
        
    except Exception as e:
        logger.error(f"Erro ao verificar estoque para pedido: {e}")
        return False, "Erro ao verificar estoque"


def processar_item_pedido(item_data, request):
    """
    Processa item de pedido aplicando parâmetros de preço e desconto
    """
    try:
        empresa_id = item_data.get('iped_empr')
        filial_id = item_data.get('iped_fili')
        produto_codigo = item_data.get('iped_prod')
        quantidade = item_data.get('iped_quan', 1)
        desconto_percentual = item_data.get('iped_desc', 0)
        tipo_preco = item_data.get('tipo_preco', 'normal')
        
        # Obter preço baseado nos parâmetros
        preco_unitario = obter_preco_produto(
            produto_codigo, empresa_id, filial_id, request, tipo_preco
        )
        
        # Calcular valor bruto
        valor_bruto = preco_unitario * Decimal(str(quantidade))
        
        # Validar e calcular desconto se aplicável
        valor_desconto = Decimal('0.00')
        if desconto_percentual > 0:
            validar_desconto_pedido(
                desconto_percentual, valor_bruto, empresa_id, filial_id, request
            )
            valor_desconto, valor_final = calcular_desconto(valor_bruto, desconto_percentual)
        else:
            valor_final = valor_bruto
        
        # Verificar estoque se necessário
        estoque_ok, estoque_msg = verificar_estoque_para_pedido(
            produto_codigo, quantidade, empresa_id, filial_id, request
        )
        
        # Verificar parâmetros aplicados
        parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
        
        resultado = {
            'preco_unitario': preco_unitario,
            'valor_bruto': valor_bruto,
            'valor_desconto': valor_desconto,
            'valor_final': valor_final,
            'estoque_ok': estoque_ok,
            'estoque_msg': estoque_msg,
            'parametros_aplicados': {
                'usar_preco_prazo': parametros.get('usar_preco_prazo', {}).get('ativo', False),
                'usar_ultimo_preco': parametros.get('usar_ultimo_preco', {}).get('ativo', False),
                'desconto_permitido': parametros.get('desconto_pedido', {}).get('ativo', False),
                'validar_estoque': parametros.get('validar_estoque_pedido', {}).get('ativo', False)
            }
        }
        
        return resultado
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar item de pedido: {e}")
        raise ValidationError("Erro interno ao processar item")


def processar_pedido_completo(pedido_data, itens_data, request):
    """
    Processa pedido completo com todos os parâmetros
    """
    try:
        empresa_id = pedido_data.get('pedi_empr')
        filial_id = pedido_data.get('pedi_fili')
        
        parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
        
        resultado = {
            'pedido_valido': True,
            'itens_processados': [],
            'alertas': [],
            'parametros_aplicados': parametros
        }
        
        # Processar cada item
        for item_data in itens_data:
            item_data.update({
                'iped_empr': empresa_id,
                'iped_fili': filial_id
            })
            
            # Processar preços e descontos
            item_resultado = processar_item_pedido(item_data, request)
            
            # Verificar alertas de estoque
            if not item_resultado['estoque_ok']:
                resultado['alertas'].append({
                    'tipo': 'estoque_insuficiente',
                    'produto': item_data.get('iped_prod'),
                    'mensagem': item_resultado['estoque_msg']
                })
            
            resultado['itens_processados'].append(item_resultado)
        
        # Verificar se há alertas críticos
        alertas_criticos = [a for a in resultado['alertas'] if a.get('tipo') == 'estoque_insuficiente']
        
        if alertas_criticos and parametros.get('validar_estoque_pedido', {}).get('ativo', False):
            resultado['pedido_valido'] = False
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar pedido completo: {e}")
        raise ValidationError("Erro interno ao processar pedido")


def calcular_frete_automatico(pedido_data, request):
    """
    Calcula frete automático baseado nos parâmetros
    """
    try:
        empresa_id = pedido_data.get('pedi_empr')
        filial_id = pedido_data.get('pedi_fili')
        
        parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
        
        # Verificar se cálculo automático de frete está habilitado
        if not parametros.get('calcular_frete_automatico', {}).get('ativo', False):
            return Decimal('0.00')
        
        # Implementar lógica de cálculo de frete
        # Por exemplo, baseado no peso, distância, valor do pedido, etc.
        
        valor_total = pedido_data.get('pedi_tota', Decimal('0.00'))
        
        # Exemplo simples: frete grátis acima de R$ 100
        if valor_total >= Decimal('100.00'):
            return Decimal('0.00')
        
        # Frete fixo de R$ 10
        return Decimal('10.00')
        
    except Exception as e:
        logger.error(f"Erro ao calcular frete automático: {e}")
        return Decimal('0.00')


def cancelar_pedido_com_volta_estoque(pedido_id, request):
    """
    Cancela pedido e volta estoque se configurado
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Pedidos.models import Pedido, ItensPedido
        
        pedido = Pedido.objects.using(banco).get(pedi_codi=pedido_id)
        
        # Verificar se volta de estoque está habilitada
        if not verificar_volta_estoque_pedido(pedido.pedi_empr, pedido.pedi_fili, request):
            return {
                'cancelamento_ok': True,
                'estoque_restaurado': False,
                'mensagem': 'Pedido cancelado sem volta de estoque (parâmetro desabilitado)'
            }
        
        # Buscar itens do pedido
        itens = ItensPedido.objects.using(banco).filter(iped_pedi=pedido_id)
        
        estoque_restaurado = []
        for item in itens:
            # Restaurar estoque usando função do utils_estoque
            from .utils_estoque import calcular_estoque_atual
            from Produtos.models import Estoque
            
            estoque, created = Estoque.objects.using(banco).get_or_create(
                esto_prod=item.iped_prod,
                esto_empr=pedido.pedi_empr,
                esto_fili=pedido.pedi_fili,
                defaults={'esto_quan': Decimal('0.00')}
            )
            
            estoque.esto_quan += item.iped_quan
            estoque.save()
            
            estoque_restaurado.append({
                'produto': item.iped_prod,
                'quantidade_restaurada': item.iped_quan,
                'estoque_atual': estoque.esto_quan
            })
        
        # Marcar pedido como cancelado
        pedido.pedi_stat = 'CANCELADO'
        pedido.save()
        
        return {
            'cancelamento_ok': True,
            'estoque_restaurado': True,
            'itens_restaurados': estoque_restaurado
        }
        
    except Exception as e:
        logger.error(f"Erro ao cancelar pedido {pedido_id}: {e}")
        return {
            'cancelamento_ok': False,
            'erro': f'Erro interno: {str(e)}'
        }