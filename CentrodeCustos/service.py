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
    codigo_str = str(codigo or "").strip()
    if not codigo_str:
        return Centrodecustos.objects.none()

    qs = Centrodecustos.objects.using(db_alias) if db_alias else Centrodecustos.objects

    partes = codigo_str.split(".")
    nivel_parent = len(partes)
    prefixo = codigo_str + "."

    filtros = {
        "cecu_empr": empresa_id,
        "cecu_expa__startswith": prefixo,
    }

    if nivel_parent >= 1:
        filtros["cecu_nive"] = nivel_parent + 1

    filhos = qs.filter(**filtros).order_by("cecu_expa")
    return filhos
