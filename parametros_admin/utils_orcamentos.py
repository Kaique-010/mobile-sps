from .models import ParametroSistema, Modulo
from core.utils import get_licenca_db_config
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def obter_parametros_orcamentos(empresa_id, filial_id, request):
    """
    Obtém todos os parâmetros de orçamentos para empresa/filial
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Buscar módulo de orçamentos
        modulo_orcamentos = Modulo.objects.using(banco).filter(
            modu_nome__icontains='orcamento'
        ).first()
        
        # Se não encontrar, buscar módulo de pedidos (orçamentos podem usar o mesmo)
        if not modulo_orcamentos:
            modulo_orcamentos = Modulo.objects.using(banco).filter(
                modu_nome__icontains='pedido'
            ).first()
        
        if not modulo_orcamentos:
            logger.warning("Módulo de orçamentos não encontrado")
            return {}
        
        parametros_nomes = [
            'baixa_estoque_orcamento',
            'usar_preco_prazo',
            'usar_ultimo_preco',
            'desconto_orcamento',
            'validade_orcamento_dias',
            'conversao_automatica_pedido'
        ]
        
        parametros = {}
        for nome_param in parametros_nomes:
            param = ParametroSistema.objects.using(banco).filter(
                para_empr=empresa_id,
                para_fili=filial_id,
                para_modu=modulo_orcamentos,
                para_nome=nome_param
            ).first()
            
            parametros[nome_param] = {
                'valor': param.para_valo if param else 'false',
                'ativo': param.para_ativ if param else False,
                'existe': param is not None
            }
        
        return parametros
        
    except Exception as e:
        logger.error(f"Erro ao obter parâmetros de orçamentos: {e}")
        return {}


def verificar_baixa_estoque_orcamento(empresa_id, filial_id, request):
    """
    Verifica se baixa de estoque em orçamento está habilitada
    """
    parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
    param = parametros.get('baixa_estoque_orcamento', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_usar_preco_prazo_orcamento(empresa_id, filial_id, request):
    """
    Verifica se deve usar preço a prazo em orçamentos
    """
    parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
    param = parametros.get('usar_preco_prazo', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_usar_ultimo_preco_orcamento(empresa_id, filial_id, request):
    """
    Verifica se deve usar último preço aplicado em orçamentos
    """
    parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
    param = parametros.get('usar_ultimo_preco', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_desconto_orcamento(empresa_id, filial_id, request):
    """
    Verifica se desconto em orçamento está habilitado
    """
    parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
    param = parametros.get('desconto_orcamento', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def verificar_conversao_automatica(empresa_id, filial_id, request):
    """
    Verifica se conversão automática para pedido está habilitada
    """
    parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
    param = parametros.get('conversao_automatica_pedido', {})
    return param.get('ativo', False) and param.get('valor', '').lower() == 'true'


def obter_validade_orcamento(empresa_id, filial_id, request):
    """
    Obtém quantidade de dias de validade do orçamento
    """
    try:
        parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
        param = parametros.get('validade_orcamento_dias', {})
        
        if param.get('ativo', False):
            try:
                return int(param.get('valor', '30'))
            except (ValueError, TypeError):
                return 30  # Padrão de 30 dias
        
        return 30  # Padrão se parâmetro não estiver ativo
        
    except Exception as e:
        logger.error(f"Erro ao obter validade do orçamento: {e}")
        return 30


def obter_preco_produto_orcamento(produto_codigo, empresa_id, filial_id, request, tipo_preco='normal'):
    """
    Obtém preço do produto para orçamento baseado nos parâmetros configurados
    """
    try:
        banco = get_licenca_db_config(request)
        
        # Verificar se deve usar preço a prazo
        if verificar_usar_preco_prazo_orcamento(empresa_id, filial_id, request) and tipo_preco == 'prazo':
            preco_prazo = obter_preco_prazo_orcamento(produto_codigo, empresa_id, filial_id, request)
            if preco_prazo:
                return preco_prazo
        
        # Verificar se deve usar último preço aplicado
        if verificar_usar_ultimo_preco_orcamento(empresa_id, filial_id, request):
            ultimo_preco = obter_ultimo_preco_orcamento(produto_codigo, empresa_id, filial_id, request)
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


def obter_preco_prazo_orcamento(produto_codigo, empresa_id, filial_id, request):
    """
    Obtém preço a prazo específico para orçamento
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
        logger.error(f"Erro ao obter preço a prazo para orçamento: {e}")
        return None


def obter_ultimo_preco_orcamento(produto_codigo, empresa_id, filial_id, request):
    """
    Obtém o último preço aplicado para um produto em orçamentos
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Orcamentos.models import ItensOrcamento
        
        ultimo_item = ItensOrcamento.objects.using(banco).filter(
            iorc_prod=produto_codigo,
            iorc_empr=empresa_id,
            iorc_fili=filial_id
        ).order_by('-iorc_codi').first()
        
        return ultimo_item.iorc_unit if ultimo_item else None
        
    except Exception as e:
        logger.error(f"Erro ao obter último preço de orçamento: {e}")
        return None


def validar_desconto_orcamento(desconto_percentual, valor_item, empresa_id, filial_id, request):
    """
    Valida se o desconto pode ser aplicado em orçamento baseado nos parâmetros
    """
    try:
        # Verificar se desconto é permitido
        if not verificar_desconto_orcamento(empresa_id, filial_id, request):
            raise ValidationError("Desconto não permitido em orçamentos para esta empresa/filial")
        
        # Validações básicas
        if desconto_percentual < 0 or desconto_percentual > 100:
            raise ValidationError("Desconto deve estar entre 0% e 100%")
        
        # Aqui você pode adicionar outras validações específicas
        # como desconto máximo permitido, autorização necessária, etc.
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar desconto em orçamento: {e}")
        raise ValidationError("Erro interno ao validar desconto")


def calcular_desconto_orcamento(valor_original, desconto_percentual):
    """
    Calcula valor do desconto e valor final para orçamento
    """
    if desconto_percentual <= 0:
        return Decimal('0.00'), valor_original
    
    valor_desconto = valor_original * (Decimal(str(desconto_percentual)) / 100)
    valor_final = valor_original - valor_desconto
    
    return valor_desconto, valor_final


def calcular_data_validade_orcamento(empresa_id, filial_id, request, data_base=None):
    """
    Calcula data de validade do orçamento baseada nos parâmetros
    """
    try:
        from datetime import datetime, timedelta
        
        if data_base is None:
            data_base = datetime.now().date()
        
        dias_validade = obter_validade_orcamento(empresa_id, filial_id, request)
        data_validade = data_base + timedelta(days=dias_validade)
        
        return data_validade
        
    except Exception as e:
        logger.error(f"Erro ao calcular data de validade: {e}")
        from datetime import datetime, timedelta
        return datetime.now().date() + timedelta(days=30)


def verificar_orcamento_vencido(orcamento_id, request):
    """
    Verifica se orçamento está vencido
    """
    try:
        banco = get_licenca_db_config(request)
        from datetime import datetime
        
        from Orcamentos.models import Orcamento
        
        orcamento = Orcamento.objects.using(banco).get(orc_codi=orcamento_id)
        
        if hasattr(orcamento, 'orc_vali') and orcamento.orc_vali:
            return datetime.now().date() > orcamento.orc_vali
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao verificar vencimento do orçamento: {e}")
        return False


def processar_item_orcamento(item_data, request):
    """
    Processa item de orçamento aplicando parâmetros de preço e desconto
    """
    try:
        empresa_id = item_data.get('iorc_empr')
        filial_id = item_data.get('iorc_fili')
        produto_codigo = item_data.get('iorc_prod')
        quantidade = item_data.get('iorc_quan', 1)
        desconto_percentual = item_data.get('iorc_desc', 0)
        tipo_preco = item_data.get('tipo_preco', 'normal')
        
        # Obter preço baseado nos parâmetros
        preco_unitario = obter_preco_produto_orcamento(
            produto_codigo, empresa_id, filial_id, request, tipo_preco
        )
        
        # Calcular valor bruto
        valor_bruto = preco_unitario * Decimal(str(quantidade))
        
        # Validar e calcular desconto se aplicável
        valor_desconto = Decimal('0.00')
        if desconto_percentual > 0:
            validar_desconto_orcamento(
                desconto_percentual, valor_bruto, empresa_id, filial_id, request
            )
            valor_desconto, valor_final = calcular_desconto_orcamento(valor_bruto, desconto_percentual)
        else:
            valor_final = valor_bruto
        
        # Verificar se deve fazer baixa de estoque
        baixa_estoque = verificar_baixa_estoque_orcamento(empresa_id, filial_id, request)
        baixa_msg = "Baixa de estoque habilitada" if baixa_estoque else "Baixa de estoque desabilitada"
        
        # Verificar parâmetros aplicados
        parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
        
        resultado = {
            'preco_unitario': preco_unitario,
            'valor_bruto': valor_bruto,
            'valor_desconto': valor_desconto,
            'valor_final': valor_final,
            'baixa_estoque': baixa_estoque,
            'baixa_msg': baixa_msg,
            'parametros_aplicados': {
                'usar_preco_prazo': parametros.get('usar_preco_prazo', {}).get('ativo', False),
                'usar_ultimo_preco': parametros.get('usar_ultimo_preco', {}).get('ativo', False),
                'desconto_permitido': parametros.get('desconto_orcamento', {}).get('ativo', False),
                'baixa_estoque': parametros.get('baixa_estoque_orcamento', {}).get('ativo', False)
            }
        }
        
        return resultado
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar item de orçamento: {e}")
        raise ValidationError("Erro interno ao processar item")


def processar_orcamento_completo(orcamento_data, itens_data, request):
    """
    Processa orçamento completo com todos os parâmetros
    """
    try:
        empresa_id = orcamento_data.get('orc_empr')
        filial_id = orcamento_data.get('orc_fili')
        
        parametros = obter_parametros_orcamentos(empresa_id, filial_id, request)
        
        # Calcular data de validade se não informada
        if not orcamento_data.get('orc_vali'):
            orcamento_data['orc_vali'] = calcular_data_validade_orcamento(
                empresa_id, filial_id, request
            )
        
        resultado = {
            'orcamento_valido': True,
            'itens_processados': [],
            'alertas': [],
            'parametros_aplicados': parametros,
            'data_validade': orcamento_data.get('orc_vali')
        }
        
        # Processar cada item
        for item_data in itens_data:
            item_data.update({
                'iorc_empr': empresa_id,
                'iorc_fili': filial_id
            })
            
            # Processar preços e descontos
            item_resultado = processar_item_orcamento(item_data, request)
            
            # Verificar baixa de estoque se aplicável
            if item_resultado['baixa_estoque']:
                # Usar função do utils_estoque para verificar disponibilidade
                from .utils_estoque import verificar_estoque_disponivel
                
                estoque_ok, estoque_atual = verificar_estoque_disponivel(
                    item_data.get('iorc_prod'),
                    item_data.get('iorc_quan', 0),
                    empresa_id,
                    filial_id,
                    request
                )
                
                if not estoque_ok:
                    resultado['alertas'].append({
                        'tipo': 'estoque_orcamento',
                        'produto': item_data.get('iorc_prod'),
                        'mensagem': f'Estoque insuficiente para baixa automática. Disponível: {estoque_atual}'
                    })
            
            resultado['itens_processados'].append(item_resultado)
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar orçamento completo: {e}")
        raise ValidationError("Erro interno ao processar orçamento")


def converter_orcamento_para_pedido(orcamento_id, request):
    """
    Converte orçamento para pedido aplicando parâmetros específicos
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Orcamentos.models import Orcamento, ItensOrcamento
        
        orcamento = Orcamento.objects.using(banco).get(orc_codi=orcamento_id)
        
        # Verificar se orçamento está vencido
        if verificar_orcamento_vencido(orcamento_id, request):
            return {
                'conversao_ok': False,
                'erro': 'Orçamento vencido, não pode ser convertido'
            }
        
        # Verificar se conversão automática está habilitada
        if not verificar_conversao_automatica(orcamento.orc_empr, orcamento.orc_fili, request):
            return {
                'conversao_ok': False,
                'erro': 'Conversão automática está desabilitada para esta empresa/filial'
            }
        
        # Buscar itens do orçamento
        itens = ItensOrcamento.objects.using(banco).filter(iorc_orc=orcamento_id)
        
        # Preparar dados do pedido
        pedido_data = {
            'pedi_empr': orcamento.orc_empr,
            'pedi_fili': orcamento.orc_fili,
            'pedi_clie': orcamento.orc_clie,
            'pedi_tota': orcamento.orc_tota,
            'pedi_stat': 'PENDENTE'
        }
        
        # Preparar itens do pedido
        itens_data = []
        for item in itens:
            itens_data.append({
                'iped_prod': item.iorc_prod,
                'iped_quan': item.iorc_quan,
                'iped_unit': item.iorc_unit,
                'iped_desc': item.iorc_desc,
                'iped_tota': item.iorc_tota
            })
        
        # Processar como pedido usando utils_pedidos
        from .utils_pedidos import processar_pedido_completo
        
        resultado_pedido = processar_pedido_completo(pedido_data, itens_data, request)
        
        if resultado_pedido['pedido_valido']:
            # Marcar orçamento como convertido
            orcamento.orc_stat = 'CONVERTIDO'
            orcamento.save()
        
        return {
            'conversao_ok': resultado_pedido['pedido_valido'],
            'orcamento_id': orcamento_id,
            'resultado_pedido': resultado_pedido,
            'parametros_orcamento': obter_parametros_orcamentos(orcamento.orc_empr, orcamento.orc_fili, request)
        }
        
    except Exception as e:
        logger.error(f"Erro ao converter orçamento {orcamento_id} para pedido: {e}")
        return {
            'conversao_ok': False,
            'erro': f'Erro interno: {str(e)}'
        }


def listar_orcamentos_vencidos(empresa_id, filial_id, request):
    """
    Lista orçamentos vencidos baseado nos parâmetros de validade
    """
    try:
        banco = get_licenca_db_config(request)
        from datetime import datetime
        
        from Orcamentos.models import Orcamento
        
        orcamentos_vencidos = Orcamento.objects.using(banco).filter(
            orc_empr=empresa_id,
            orc_fili=filial_id,
            orc_vali__lt=datetime.now().date(),
            orc_stat__in=['PENDENTE', 'APROVADO']  # Apenas orçamentos ativos
        )
        
        resultado = []
        for orcamento in orcamentos_vencidos:
            resultado.append({
                'orcamento_id': orcamento.orc_codi,
                'cliente': orcamento.orc_clie,
                'valor_total': orcamento.orc_tota,
                'data_validade': orcamento.orc_vali,
                'dias_vencido': (datetime.now().date() - orcamento.orc_vali).days
            })
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao listar orçamentos vencidos: {e}")
        return []