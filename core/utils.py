# utils.py
from decouple import config
from django.db import connections
from core import settings
from core.licenca_context import LICENCAS_MAP
from decimal import Decimal, ROUND_HALF_UP


def get_db_from_slug(slug):
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    if not slug:
        return "default"

    licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    if slug in settings.DATABASES:
        logger.info(f"🔄 Conexão {slug} já existe (reutilizada)")
        return slug

    # Log de diagnóstico de rede
    logger.warning(f"🌐 Criando nova conexão para {slug} -> {licenca['db_host']}:{licenca['db_port']}")
    
    prefixo = slug.upper()
    db_user = config(f"{prefixo}_DB_USER")
    db_password = config(f"{prefixo}_DB_PASSWORD")

    settings.DATABASES[slug] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': licenca["db_name"],
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': licenca["db_host"],
        'PORT': licenca["db_port"],
        'OPTIONS': {
            'options': '-c timezone=America/Araguaina',
            'connect_timeout': 30,  # Aumentado de 10 para 30
            'application_name': 'mobile_sps',
        },
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
    }

    connections.ensure_defaults(slug)
    connections.prepare_test_settings(slug)
    
    total_time = (time.time() - start_time) * 1000
    logger.warning(f"⏱️  Conexão {slug} criada em {total_time:.2f}ms")

    return slug

def get_licenca_db_config(request):
    path_parts = request.path.strip('/').split('/')
    slug = path_parts[1] if len(path_parts) > 1 else None
    return get_db_from_slug(slug)


from decimal import Decimal, ROUND_HALF_UP

def calcular_valores_pedido(itens_data, desconto_total=None, desconto_percentual=None):
    """
    Calcula subtotal, desconto e total do pedido/orçamento
    
    Args:
        itens_data: Lista de itens com quantidade e valor unitário
        desconto_total: Valor fixo de desconto em reais
        desconto_percentual: Percentual de desconto (0-100)
    
    Returns:
        dict: {'subtotal': Decimal, 'desconto': Decimal, 'total': Decimal}
    """
    subtotal = Decimal('0.00')
    
    # Calcular subtotal somando todos os itens
    for item in itens_data:
        quantidade = Decimal(str(item.get('iped_quan', 0) or 0))
        valor_unitario = Decimal(str(item.get('iped_unit', 0) or 0))
        subtotal_item = quantidade * valor_unitario
        subtotal += subtotal_item
    
    # Calcular desconto
    desconto = Decimal('0.00')
    
    if desconto_total is not None:
        # Desconto em valor fixo
        desconto = Decimal(str(desconto_total))
    elif desconto_percentual is not None:
        # Desconto percentual
        percentual = Decimal(str(desconto_percentual))
        desconto = (subtotal * percentual / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    # Calcular total
    total = subtotal - desconto
    
    # Garantir que o total não seja negativo
    if total < 0:
        total = Decimal('0.00')
    
    return {
        'subtotal': subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'desconto': desconto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'total': total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    }

def calcular_subtotal_item(quantidade, valor_unitario, desconto_item=None):
    """
    Calcula o subtotal de um item específico
    
    Args:
        quantidade: Quantidade do item
        valor_unitario: Valor unitário do item
        desconto_item: Desconto específico do item
    
    Returns:
        Decimal: Subtotal do item
    """
    quantidade = Decimal(str(quantidade or 0))
    valor_unitario = Decimal(str(valor_unitario or 0))
    desconto_item = Decimal(str(desconto_item or 0))
    
    subtotal = quantidade * valor_unitario
    total_item = subtotal - desconto_item
    
    return max(total_item, Decimal('0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_subtotal_item_bruto(quantidade, valor_unitario):
    """
    Calcula o subtotal bruto de um item (quantidade × valor unitário)
    Este é o valor antes de aplicar descontos
    
    Args:
        quantidade: Quantidade do item
        valor_unitario: Valor unitário do item
    
    Returns:
        Decimal: Subtotal bruto do item
    """
    quantidade = Decimal(str(quantidade or 0))
    valor_unitario = Decimal(str(valor_unitario or 0))
    
    subtotal_bruto = quantidade * valor_unitario
    
    return subtotal_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_total_item_com_desconto(quantidade, valor_unitario, desconto_item=None):
    """
    Calcula o total de um item específico aplicando desconto
    
    Args:
        quantidade: Quantidade do item
        valor_unitario: Valor unitário do item
        desconto_item: Desconto específico do item
    
    Returns:
        Decimal: Total do item com desconto aplicado
    """
    quantidade = Decimal(str(quantidade or 0))
    valor_unitario = Decimal(str(valor_unitario or 0))
    desconto_item = Decimal(str(desconto_item or 0))
    
    subtotal_bruto = quantidade * valor_unitario
    total_item = subtotal_bruto - desconto_item
    
    return max(total_item, Decimal('0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
