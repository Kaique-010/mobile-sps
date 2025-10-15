from django.db import connections
from O_S.models import ServicosOs, Os, PecasOs


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
    """
    Gera o próximo ID sequencial para um item com base nos campos de empresa, filial e ordem.
    O ID é composto por: <ordem_id><sequencia crescente, com padding>.
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
        ids = [row[0] for row in cursor.fetchall()]
        
        # Se não houver IDs, começa do 1
        if not ids:
            ultimo_local = 0
        else:
            # Pega o último número local (últimos 3 dígitos do maior ID)
            ultimo_local = max(int(str(id_)[-3:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{ordem_id}{novo_local:03d}")

    return novo_id

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
    Gera o próximo ID de serviço sequencial simples para uma determinada ordem.
    """
    with connections[banco].cursor() as cursor:
        # Primeiro faz lock das linhas existentes
        cursor.execute(
            """
            SELECT serv_id, serv_item
            FROM servicosos 
            WHERE serv_os = %s 
              AND serv_empr = %s 
              AND serv_fili = %s 
            ORDER BY serv_id
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        results = cursor.fetchall()
        
        # Encontra o próximo ID disponível
        if not results:
            novo_id = 1
            next_sequ = 1
        else:
            # Pega todos os IDs e itens existentes
            ids = [row[0] for row in results]
            items = [row[1] for row in results]
            
            # Encontra o próximo ID disponível
            ids_sorted = sorted(ids)
            novo_id = 1
            for id_atual in ids_sorted:
                if novo_id < id_atual:
                    break
                novo_id = id_atual + 1
            
            # Encontra o próximo item disponível
            items_sorted = sorted(items)
            next_sequ = 1
            for item_atual in items_sorted:
                if next_sequ < item_atual:
                    break
                next_sequ = item_atual + 1

    return novo_id, next_sequ
