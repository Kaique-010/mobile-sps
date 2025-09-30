from .models import ParametroSistema, Modulo
from core.utils import get_licenca_db_config
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
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
            'desconto_orcamento',
            'desconto_item_orcamento',
            'desconto_total_orcamento',
            'desconto_total_pedido',
            'desconto_total_disponivel',
            'usar_preco_prazo',
            'usar_ultimo_preco',
            'desconto_pedido',
            'desconto_item_pedido',
            'desconto_maximo_item',
            'desconto_maximo_total',
            'pedido_volta_estoque',
            'validar_estoque_pedido',
            'calcular_frete_automatico', 
            'baixa_estoque_orcamento',
            'baixa_estoque_pedido',
            'pedido_volta_esatoque'
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
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


def verificar_usar_ultimo_preco(empresa_id, filial_id, request):
    """
    Verifica se deve usar último preço aplicado
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('usar_ultimo_preco', {})
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


def verificar_desconto_pedido(empresa_id, filial_id, request):
    """
    Verifica se desconto em pedido está habilitado
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('desconto_pedido', {})
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


def verificar_volta_estoque_pedido(empresa_id, filial_id, request):
    """
    Verifica se volta de estoque em pedido está habilitada
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('pedido_volta_estoque', {})
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


def verificar_validar_estoque_pedido(empresa_id, filial_id, request):
    """
    Verifica se deve validar estoque ao criar pedido
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('validar_estoque_pedido', {})
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


def verificar_baixa_estoque_pedido(empresa_id, filial_id, request):
    """
    Verifica se deve fazer baixa automática de estoque ao criar pedido
    """
    parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
    param = parametros.get('baixa_estoque_pedido', {})
    valor = param.get('valor', 'false')
    # Corrigir para tratar tanto string quanto boolean
    if isinstance(valor, bool):
        return param.get('ativo', False) and valor
    return param.get('ativo', False) and str(valor).lower() == 'true'


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
        
        
        
#Parametros para aplicar desconto no total do pedido

def arredondar(valor):
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def desconto_no_total(pedido):
    """
    Aplica desconto no total do pedido, se configurado.
    """
    total = pedido.pedi_tota or Decimal('0.00')
    desconto = pedido.pedi_desc or Decimal('0.00')

    total_liquido = max(total - desconto, Decimal('0.00'))
    pedido.pedi_tota = arredondar(total_liquido)
    # pedido.save() → deixa o save fora, quem chama é que decide


def desconto_no_item(item):
    """
    Aplica desconto no item de orçamento/pedido.
    """
    unitario = item.iped_unit or Decimal('0.00')
    quantidade = item.iped_quan or Decimal('0.00')
    desconto = item.iped_desc or Decimal('0.00')

    total = unitario * quantidade
    total_liquido = max(total - desconto, Decimal('0.00'))

    item.iped_tota = arredondar(total_liquido)
    # item.save() → mesmo esquema, deixa fora

def aplicar_descontos(pedido, itens, usar_desconto_item=False, usar_desconto_total=False, banco=None):
    """
    Aplica os descontos no pedido ou nos itens com base nos parâmetros.
    """

    if usar_desconto_item and usar_desconto_total:
        raise ValueError("Não pode aplicar desconto no item e no total ao mesmo tempo.")

    if usar_desconto_item:
        for item in itens:
            desconto_no_item(item)
            if banco:
                item.save(using=banco)
            else:
                item.save()
        pedido.pedi_tota = arredondar(sum([item.iped_tota or Decimal('0.00') for item in itens]))

    elif usar_desconto_total:
        total_bruto = arredondar(sum([
            (item.iped_quan or Decimal('0.00')) * (item.iped_unit or Decimal('0.00'))
            for item in itens
        ]))
        pedido.pedi_tota = total_bruto
        desconto_no_total(pedido)

    else:
        pedido.pedi_tota = arredondar(sum([
            (item.iped_quan or Decimal('0.00')) * (item.iped_unit or Decimal('0.00'))
            for item in itens
        ]))


def atualizar_parametros_pedidos(empresa_id, filial_id, dados_parametros, modulos_busca=None):
    """
    Atualiza parâmetros específicos de pedidos
    
    Args:
        empresa_id: ID da empresa
        filial_id: ID da filial
        dados_parametros: Dicionário com os parâmetros a serem atualizados
        modulos_busca: Lista de nomes de módulos para buscar (opcional)
                      Default: ['pedido', 'orcamento']
    """
    try:
        from core.utils import get_licenca_db_config
        from django.http import HttpRequest
        
        # Criar request mock se necessário
        request = HttpRequest()
        banco = get_licenca_db_config(request)
        
        if not banco:
            logger.error("Banco de dados não encontrado")
            return False
        
        # Buscar módulo de pedidos
        from django.db.models import Q
        
        # Usar lista padrão se não foi fornecida
        if modulos_busca is None:
            modulos_busca = ['pedido', 'orcamento']
        
        # Construir query dinâmica com base na lista de módulos
        query = Q()
        for modulo_nome in modulos_busca:
            query |= Q(modu_nome__icontains=modulo_nome)
        
        modulo_pedidos = Modulo.objects.using(banco).filter(query).first()
        
        if not modulo_pedidos:
            logger.error("Módulo de pedidos não encontrado")
            return False
        
        # Parâmetros que podem ser atualizados
        parametros_permitidos = [
            'desconto_item_disponivel',
            'desconto_total_disponivel', 
            'desconto_maximo_item',
            'desconto_maximo_total',
            'usar_preco_prazo',
            'usar_ultimo_preco',
            'desconto_total_pedido',
            'desconto_total_orcamento',
            'desconto_item_pedido',
            'desconto_item_orcamento',
            'pedido_volta_estoque',
            'validar_estoque_pedido',
            'calcular_frete_automatico'
        ]
        
        # Atualizar cada parâmetro
        for nome_param, valor in dados_parametros.items():
            logger.info(f"Processando parâmetro: {nome_param} = {valor} (tipo: {type(valor)})")
            
            if nome_param not in parametros_permitidos:
                logger.warning(f"Parâmetro {nome_param} não está na lista de permitidos")
                continue
                
            try:
                # Converter valor para boolean
                if isinstance(valor, str):
                    valor_bool = valor.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(valor, (int, float)):
                    valor_bool = bool(valor)
                elif isinstance(valor, bool):
                    valor_bool = valor
                else:
                    valor_bool = False
                
                logger.info(f"Valor convertido para boolean: {valor_bool}")
                
                # Buscar ou criar parâmetro
                parametro, created = ParametroSistema.objects.using(banco).get_or_create(
                    para_empr=empresa_id,
                    para_fili=filial_id,
                    para_modu=modulo_pedidos,
                    para_nome=nome_param,
                    defaults={
                        'para_desc': f'Parâmetro {nome_param} para pedidos',
                        'para_valo': valor_bool,
                        'para_ativ': True,
                        'para_usua_alte': 1  # Usuário sistema
                    }
                )
                
                if created:
                    logger.info(f"Parâmetro {nome_param} criado com valor: {valor_bool}")
                else:
                    # Atualizar parâmetro existente
                    valor_anterior = parametro.para_valo
                    parametro.para_valo = valor_bool
                    parametro.para_usua_alte = 1
                    parametro.save(using=banco)
                    logger.info(f"Parâmetro {nome_param} atualizado de {valor_anterior} para {valor_bool}")
                
            except Exception as e:
                logger.error(f"Erro ao atualizar parâmetro {nome_param}: {e}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao atualizar parâmetros de pedidos: {e}")
        return False


def validar_desconto_item_pedido(desconto_percentual, empresa_id, filial_id, request):
    """
    Valida desconto específico por item em pedidos
    """
    try:
        # Verificar se desconto por item é permitido
        parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
        
        # Verificar se desconto por item está habilitado
        desconto_item_param = parametros.get('desconto_item_pedido', {})
        if not desconto_item_param.get('ativo', False) or not desconto_item_param.get('valor', False):
            raise ValidationError("Desconto por item não permitido para esta empresa/filial")
        
        # Validações básicas
        if desconto_percentual < 0 or desconto_percentual > 100:
            raise ValidationError("Desconto deve estar entre 0% e 100%")
        
        # Verificar limite máximo se configurado
        limite_param = parametros.get('desconto_maximo_item', {})
        if limite_param.get('ativo', False):
            # Para limites numéricos, seria necessário um campo adicional no modelo
            # Por enquanto, usar validação padrão de 50%
            limite_maximo = 50.0
            if desconto_percentual > limite_maximo:
                raise ValidationError(f"Desconto por item não pode exceder {limite_maximo}%")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar desconto por item: {e}")
        raise ValidationError("Erro interno ao validar desconto por item")


def validar_desconto_total_pedido(desconto_percentual, empresa_id, filial_id, request):
    """
    Valida desconto específico no total do pedido
    """
    try:
        # Verificar se desconto no total é permitido
        parametros = obter_parametros_pedidos(empresa_id, filial_id, request)
        
        # Verificar se desconto no total está habilitado
        desconto_total_param = parametros.get('desconto_total_pedido', {})
        if not desconto_total_param.get('ativo', False) or not desconto_total_param.get('valor', False):
            raise ValidationError("Desconto no total não permitido para esta empresa/filial")
        
        # Validações básicas
        if desconto_percentual < 0 or desconto_percentual > 100:
            raise ValidationError("Desconto deve estar entre 0% e 100%")
        
        # Verificar limite máximo se configurado
        limite_param = parametros.get('desconto_maximo_total', {})
        if limite_param.get('ativo', False):
            # Para limites numéricos, seria necessário um campo adicional no modelo
            # Por enquanto, usar validação padrão de 30%
            limite_maximo = 30.0
            if desconto_percentual > limite_maximo:
                raise ValidationError(f"Desconto no total não pode exceder {limite_maximo}%")
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Erro ao validar desconto no total: {e}")
        raise ValidationError("Erro interno ao validar desconto no total")
