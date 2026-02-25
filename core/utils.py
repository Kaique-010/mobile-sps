# utils.py
from decouple import config
from django.db import connections
from core import settings
from core.licenca_context import get_licencas_map
from decimal import Decimal, ROUND_HALF_UP


def get_db_from_slug(slug):
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    if not slug:
        return "default"

    licenca = next((lic for lic in get_licencas_map() if lic["slug"] == slug), None)
    if not licenca:
        raise Exception(f"Licença com slug '{slug}' não encontrada.")

    if slug in settings.DATABASES:
        return slug
    
    prefixo = slug.upper()
    db_user = licenca.get("db_user") or config(f"{prefixo}_DB_USER", default=None)
    db_password = licenca.get("db_password") or config(f"{prefixo}_DB_PASSWORD", default=None)
    if not db_user or not db_password:
        raise Exception(f"Credenciais não encontradas para {slug}")

    settings.DATABASES[slug] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': licenca["db_name"],
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': licenca["db_host"],
        'PORT': licenca["db_port"],
        'OPTIONS': {
            'options': '-c timezone=America/Araguaina',
            'connect_timeout': 30,
            'application_name': 'mobile_sps',
        },
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
        'TEST': {
            'MIRROR': 'default',
            'DEPENDENCIES': [],
        },
    }

    connections.ensure_defaults(slug)
    connections.prepare_test_settings(slug)
    
    total_time = (time.time() - start_time) * 1000
    logger.warning(f"⏱️  Conexão {slug} criada em {total_time:.2f}ms")

    return slug

def get_licenca_db_config(request):
    try:
        parts = request.path.strip('/').split('/')
        slug = None
        if parts and parts[0] == 'api':
            slug = parts[1] if len(parts) > 1 else None
        elif parts and parts[0] == 'web':
            if len(parts) > 2:
                slug_candidate = parts[1]
                try:
                    from core.licenca_context import get_licencas_map
                    if any(l.get('slug') == slug_candidate for l in get_licencas_map()):
                        slug = slug_candidate
                except Exception:
                    pass
        if not slug:
            try:
                from core.middleware import get_licenca_slug
                slug = get_licenca_slug() or request.session.get('slug')
            except Exception:
                slug = request.session.get('slug')
        if not slug:
            return 'default'
        try:
            return get_db_from_slug(slug)
        except Exception:
            return 'default'
    except Exception:
        return 'default'




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
    
    # Garantir que o resultado não exceda os limites do campo (max_digits=15, decimal_places=5 para iped_suto)
    # Máximo: 9999999999.99999 (10 dígitos inteiros + 5 decimais = 15 total)
    resultado = Decimal(str(round(subtotal_bruto, 5)))
    
    # Validar se não excede o limite do campo iped_suto
    if resultado >= Decimal('10000000000.00000'):  # 10^10
        raise ValueError(f"Subtotal calculado ({resultado}) excede o limite máximo do campo (9999999999.99999)")
    
    return resultado

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
    
    print(f"🔍 [DEBUG] Calculando total: quantidade={quantidade}, valor_unitario={valor_unitario}, desconto={desconto_item}")
    
    subtotal_bruto = quantidade * valor_unitario
    total_item = subtotal_bruto - desconto_item
    
    print(f"🔍 [DEBUG] Subtotal bruto: {subtotal_bruto}, Total antes round: {total_item}")
    
    # Garantir que o resultado não exceda os limites do campo (max_digits=15, decimal_places=2)
    # Máximo: 9999999999999.99 (13 dígitos inteiros + 2 decimais = 15 total)
    resultado = Decimal(str(round(max(total_item, Decimal('0.00')), 2)))

    
    # Validar se não excede o limite do campo
    if resultado >= Decimal('10000000000000.00'):  # 10^13
        raise ValueError(f"Total do item calculado ({resultado}) excede o limite máximo do campo (9999999999999.99)")
    
    return resultado


import logging
import sys

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"

COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}

def color_text(text, color=None, bold=False):
    c = COLORS.get(color, "")
    b = BOLD if bold else ""
    return f"{b}{c}{text}{RESET}"

class ColorFormatter(logging.Formatter):
    """Custom formatter to colorize log messages based on log level and content."""

    def format(self, record):
        level_color = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "magenta",
        }.get(record.levelname, "white")

        msg = super().format(record)
        msg = msg.replace("[TOOL_CALL]", color_text("[TOOL_CALL]", "yellow", True))
        msg = msg.replace("[TOOL_OUTPUT]", color_text("[TOOL_OUTPUT]", "green", True))
        msg = msg.replace("[PROMPT_PREVIEW]", color_text("[PROMPT_PREVIEW]", "magenta", True))
        msg = msg.replace("[FAISS]", color_text("[FAISS]", "cyan", True))
        msg = msg.replace("[EXECUTAR_INTENCAO]", color_text("[EXECUTAR_INTENCAO]", "blue", True))

        return color_text(msg, level_color)
    

def configurar_logger_colorido():
    """Aplica o formato colorido globalmente."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = ColorFormatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG)
