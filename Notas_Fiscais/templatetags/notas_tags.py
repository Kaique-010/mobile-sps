
from django import template
from ..utils.sefaz_messages import get_sefaz_message, SEFAZ_MESSAGES

register = template.Library()

@register.filter
def sefaz_status_label(status):
    """
    Converte o código de status da SEFAZ em uma mensagem amigável para exibição.
    Substitui o get_status_display para cobrir também os códigos de erro da SEFAZ.
    """
    try:
        status_int = int(status)
    except (ValueError, TypeError):
        return status

    # Status do Sistema (Choices do Model)
    system_labels = {
        0: "Rascunho",
        100: "Autorizada",
        101: "Cancelada",
        102: "Inutilizada",
        301: "Denegada (Emitente)",
        302: "Denegada (Destinatário)",
    }
    
    if status_int in system_labels:
        return system_labels[status_int]
    
    # Status da SEFAZ (Erros/Rejeições)
    msg = SEFAZ_MESSAGES.get(status_int)
    if msg:
        return f"{msg} ({status_int})"
            
    # Fallback
    return status

@register.filter
def sefaz_status_short(status):
    """
    Retorna uma versão curta do status para exibição em tabelas.
    Status de sistema retornam o nome (ex: Autorizada).
    Erros retornam 'Erro (Código)'.
    """
    try:
        status_int = int(status)
    except (ValueError, TypeError):
        return status

    system_labels = {
        0: "Rascunho",
        100: "Autorizada",
        101: "Cancelada",
        102: "Inutilizada",
        301: "Denegada (Emitente)",
        302: "Denegada (Destinatário)",
    }
    
    if status_int in system_labels:
        return system_labels[status_int]
        
    return f"Erro ({status_int})"
