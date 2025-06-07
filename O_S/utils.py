from django.db import connections
from O_S.models import ServicosOs, Os, PecasOs


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
    """
    Gera o próximo ID sequencial para um item com base nos campos de empresa, filial e ordem.
    """
    with connections[banco].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {id_field}
            FROM {model._meta.db_table}
            WHERE {ordem_field} = %s 
              AND {empresa_field} = %s 
              AND {filial_field} = %s
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        ids = [row[0] for row in cursor.fetchall() if row[0] is not None]

    if not ids:
        ultimo_local = 0
    else:
        # Assume que os dois últimos dígitos do ID são a sequência
        ultimo_local = max(int(str(id_)[-2:]) for id_ in ids)

    novo_local = ultimo_local + 1
    novo_id = int(f"{ordem_id}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Gera o próximo número de item (peca_item) para uma peça de OS.
    """
    return get_next_sequential_id(
        banco=banco,
        model=PecasOs,  # ✅ Corrigido: busca na tabela certa
        ordem_id=peca_os,
        empresa_id=peca_empr,
        filial_id=peca_fili,
        id_field='peca_item',
        ordem_field='peca_os',
        empresa_field='peca_empr',
        filial_field='peca_fili'
    )


def get_next_service_id(banco, ordem_id, empresa_id, filial_id):
    """
    Gera o próximo ID de serviço para uma determinada ordem.
    """
    with connections[banco].cursor() as cursor:
        cursor.execute(
            """
            SELECT serv_item 
            FROM servicosos 
            WHERE serv_orde = %s 
              AND serv_empr = %s 
              AND serv_fili = %s 
            ORDER BY serv_item DESC
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        result = cursor.fetchone()

    next_sequ = 1 if result is None else result[0] + 1
    novo_id = int(f"{ordem_id}{next_sequ:03d}")

    return novo_id, next_sequ
