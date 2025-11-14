from django.db import connections
from django.db.models import Max
from OrdemdeServico.models import Ordemservicopecas, Ordemservicoservicos, Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
    """
    Função genérica para gerar IDs sequenciais simples (1, 2, 3, 4, 5...)
    """
    with connections[banco].cursor() as cursor:
        # Primeiro faz lock das linhas existentes
        cursor.execute(
            f"""
            SELECT {id_field}
            FROM {model._meta.db_table}
            WHERE {ordem_field} = %s 
            AND {empresa_field} = %s 
            AND {filial_field} = %s
            ORDER BY {id_field}
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        ids = [row[0] for row in cursor.fetchall()]
        
        # Encontra o próximo ID disponível
        if not ids:
            novo_id = 1
        else:
            # Procura por gaps na sequência ou usa o próximo após o maior
            ids_sorted = sorted(ids)
            novo_id = 1
            for id_atual in ids_sorted:
                if novo_id < id_atual:
                    break
                novo_id = id_atual + 1
        
    return novo_id


def get_next_item_number_sequence(banco, peca_orde, peca_empr, peca_fili):
    """
    Gera próximo `peca_id` globalmente único para ordem de serviço.
    """
    with connections[banco].cursor() as cursor:
        cursor.execute(
            f"""
            SELECT peca_id
            FROM {Ordemservicopecas._meta.db_table}
            ORDER BY peca_id
            FOR UPDATE
            """
        )
        ids = [row[0] for row in cursor.fetchall()]

        if not ids:
            novo_id = 1
        else:
            ids_sorted = sorted(ids)
            novo_id = 1
            for id_atual in ids_sorted:
                if novo_id < id_atual:
                    break
                novo_id = id_atual + 1

    return novo_id


def get_next_service_id(banco, ordem_id, empresa_id, filial_id):
    """
    Gera próximo `serv_id` globalmente único e `serv_sequ` sequencial por ordem.
    - `serv_id`: não pode colidir entre ordens (PK global).
    - `serv_sequ`: sequência local por (serv_empr, serv_fili, serv_orde).
    """
    with connections[banco].cursor() as cursor:
        # Calcula próximo serv_id GLOBAL (sem filtro por ordem)
        cursor.execute(
            """
            SELECT serv_id
            FROM ordemservicoservicos
            ORDER BY serv_id
            FOR UPDATE
            """
        )
        ids = [row[0] for row in cursor.fetchall()]

        if not ids:
            novo_id = 1
        else:
            ids_sorted = sorted(ids)
            novo_id = 1
            for id_atual in ids_sorted:
                if novo_id < id_atual:
                    break
                novo_id = id_atual + 1

        # Calcula próximo serv_sequ LOCAL (filtrado por ordem)
        cursor.execute(
            """
            SELECT serv_sequ
            FROM ordemservicoservicos 
            WHERE serv_orde = %s 
              AND serv_empr = %s 
              AND serv_fili = %s 
            ORDER BY serv_sequ
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        sequs = [row[0] for row in cursor.fetchall()]

        if not sequs:
            next_sequ = 1
        else:
            sequs_sorted = sorted(sequs)
            next_sequ = 1
            for sequ_atual in sequs_sorted:
                if next_sequ < sequ_atual:
                    break
                next_sequ = sequ_atual + 1

    return novo_id, next_sequ


def get_next_image_id(banco, ordem_id, empresa_id, filial_id, tipo_imagem):
    """
    Função para gerar IDs sequenciais de imagens
    """
    model_map = {
        'antes': (Ordemservicoimgantes, 'iman_id', 'iman_orde', 'iman_empr', 'iman_fili'),
        'durante': (Ordemservicoimgdurante, 'imdu_id', 'imdu_orde', 'imdu_empr', 'imdu_fili'),
        'depois': (Ordemservicoimgdepois, 'imde_id', 'imde_orde', 'imde_empr', 'imde_fili')
    }
    
    model, id_field, ordem_field, empresa_field, filial_field = model_map[tipo_imagem]
    
    return get_next_sequential_id(
        banco=banco,
        model=model,
        ordem_id=ordem_id,
        empresa_id=empresa_id,
        filial_id=filial_id,
        id_field=id_field,
        ordem_field=ordem_field,
        empresa_field=empresa_field,
        filial_field=filial_field
    )
