# services.py
from django.db.models import Q
from .models import Centrodecustos

MASCARA = ["S", "S", "A"]              # N1 = S, N2 = S, N3 = A
DIGITOS = [1, 2, 3]                    # 1 → 1 dígito | 2 → 2 dígitos | 3 → 3 dígitos


def gerar_proximo_codigo(parent_code: str | None, empresa_id: int):
    """
    Retorna:
    - novo código expandido (ex: 1.01.004)
    - tipo (S/A)
    """
    if parent_code:
        nivel_atual = len(parent_code.split(".")) + 1
        prefix = parent_code + "."
    else:
        nivel_atual = 1
        prefix = ""

    if nivel_atual > len(MASCARA):
        raise Exception("Profundidade maior que a máscara definida.")

    # BUSCAR EXISTENTES NESSE NÍVEL
    filtros = Q(cecu_empr=empresa_id)

    if parent_code:
        filtros &= Q(cecu_expa__startswith=prefix)
    else:
        filtros &= Q(cecu_nive=1)

    existentes = Centrodecustos.objects.filter(filtros).values_list("cecu_expa", flat=True)

    usados = []
    for cod in existentes:
        partes = cod.split(".")
        if len(partes) >= nivel_atual:
            usados.append(int(partes[nivel_atual - 1]))

    proximo = (max(usados) + 1) if usados else 1
    sufixo = str(proximo).zfill(DIGITOS[nivel_atual - 1])

    novo_codigo = f"{prefix}{sufixo}"
    tipo = MASCARA[nivel_atual - 1]

    return novo_codigo, tipo

def get_children(codigo, empresa_id):
    """Retorna filhos diretos pelo vínculo cecu_niv1 (mesmo nível ou próximo)."""
    try:
        parent_redu = int(str(codigo).replace(".", ""))
    except Exception:
        parent_redu = 0
    return Centrodecustos.objects.filter(
        cecu_empr=empresa_id,
        cecu_niv1=parent_redu
    ).exclude(cecu_redu=parent_redu).order_by("cecu_expa")
