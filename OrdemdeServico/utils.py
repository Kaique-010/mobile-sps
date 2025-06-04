from django.db import connections
from django.db.models import Max
from OrdemdeServico.models import Ordemservicopecas, Ordemservicoservicos, Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
    """
    Função genérica para gerar IDs sequenciais
    """
    with connections[banco].cursor() as cursor:
        # Primeiro obtém todos os IDs em lock
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


def get_next_item_number_sequence(banco, peca_orde, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Ordemservicopecas,
        ordem_id=peca_orde,
        empresa_id=peca_empr,
        filial_id=peca_fili,
        id_field='peca_id',
        ordem_field='peca_orde',
        empresa_field='peca_empr',
        filial_field='peca_fili'
    )


def get_next_service_id(banco, ordem_id, empresa_id, filial_id):
    """
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM ordemservicoservicos 
            WHERE serv_orde = %s 
            AND serv_empr = %s 
            AND serv_fili = %s 
            ORDER BY serv_sequ DESC
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        result = cursor.fetchone()
        next_sequ = 1 if result is None else result[0] + 1
        
        # Gera o ID combinando ordem e sequência
        novo_id = int(f"{ordem_id}{next_sequ:03d}")
        
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
