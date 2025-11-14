from django.db import connections
from O_S.models import ServicosOs, Os, PecasOs


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
    """
    Gera o próximo número sequencial simples (1..N) para itens da ordem.
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
        ids = sorted(int(row[0]) for row in cursor.fetchall() if row[0] is not None)

        if not ids:
            return 1

        sequ = 1
        for id_atual in ids:
            if id_atual != sequ:
                return sequ
            sequ += 1

        return sequ

def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Gera o próximo número de item (peca_item) para uma peça de OS.
    """
    return get_next_sequential_id(
        banco=banco,
        model=PecasOs, 
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
    Gera próximo número sequencial simples (1..N) para serviços da ordem.
    Retorna (novo_id, sequencia_local) para compatibilidade.
    """
    with connections[banco].cursor() as cursor:
        cursor.execute(
            """
            SELECT serv_item
            FROM servicosos 
            WHERE serv_os = %s 
              AND serv_empr = %s 
              AND serv_fili = %s 
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        ids = sorted(int(row[0]) for row in cursor.fetchall() if row[0] is not None)

    if not ids:
        return 1, 1

    sequ = 1
    for id_atual in ids:
        if id_atual != sequ:
            return sequ, sequ
        sequ += 1

    return sequ, sequ


def compactar_servicos(banco, serv_empr, serv_fili, serv_os):
    """
    Reatribui os valores de serv_item para 1..N sem buracos
    para a combinação (serv_empr, serv_fili, serv_os), de forma atômica.
    Usa ROW_NUMBER() com ctid para evitar colisões durante o UPDATE.
    """
    with connections[banco].cursor() as cursor:
        cursor.execute(
            """
            WITH ordered AS (
                SELECT ctid, ROW_NUMBER() OVER (ORDER BY serv_item) AS rn
                FROM servicosos
                WHERE serv_empr = %s AND serv_fili = %s AND serv_os = %s
                FOR UPDATE
            )
            UPDATE servicosos s
            SET serv_item = ordered.rn
            FROM ordered
            WHERE s.ctid = ordered.ctid
            """,
            [serv_empr, serv_fili, serv_os]
        )
