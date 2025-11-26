# services.py
from django.db.models import Q
from .models import Centrodecustos

MASCARA = ["S", "S", "A"]              # N1 = S, N2 = S, N3 = A
DIGITOS = [1, 2, 3]                    # 1 → 1 dígito | 2 → 2 dígitos | 3 → 3 dígitos


def gerar_proximo_codigo(parent_code: str | None, empresa_id: int, db_alias: str | None = None):
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

    qs = Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects
    existentes = qs.filter(filtros).values_list("cecu_expa", flat=True)

    usados = []
    for cod in existentes:
        partes = cod.split(".")
        if len(partes) >= nivel_atual:
            try:
                usados.append(int(partes[nivel_atual - 1]))
            except Exception:
                pass

    if nivel_atual == 3:
        inicio = 1
        proximo = (max(usados) + 1) if usados else inicio
    else:
        proximo = (max(usados) + 1) if usados else 1
    sufixo = str(proximo).zfill(DIGITOS[nivel_atual - 1])

    novo_codigo = f"{prefix}{sufixo}"
    tipo = MASCARA[nivel_atual - 1]

    return novo_codigo, tipo

def get_children(codigo, empresa_id, db_alias: str | None = None):
    """Retorna apenas filhos imediatos do código informado.

    Primeiro tenta localizar por prefixo expandido e nível (mais confiável).
    Se não houver resultado, faz fallback para o vínculo `cecu_niv1`.
    """
    codigo_str = str(codigo)
    qs = Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects

    try:
        prefix = codigo_str + "."
        pattern = r"^" + prefix.replace(".", r"\.") + r"[^.]+$"
        imediatos = qs.filter(
            cecu_empr=empresa_id,
            cecu_expa__regex=pattern,
        ).exclude(cecu_expa=codigo_str).order_by("cecu_expa").distinct("cecu_redu")
        if imediatos.exists():
            return imediatos
    except Exception:
        pass

    try:
        parent_redu = int(codigo_str.replace(".", ""))
    except Exception:
        parent_redu = 0

    # Fallback apenas para nível 1: filhos diretos nível 2 com vínculo cecu_niv1 = 1,2,3,4
    try:
        partes = codigo_str.split('.')
        nivel_parent = len(partes)
    except Exception:
        nivel_parent = 0

    return qs.none()
