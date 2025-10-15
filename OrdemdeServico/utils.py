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
    Função para gerar IDs sequenciais simples de serviços
    """
    with connections[banco].cursor() as cursor:
        # Primeiro faz lock das linhas existentes
        cursor.execute(
            """
            SELECT serv_id, serv_sequ
            FROM ordemservicoservicos 
            WHERE serv_orde = %s 
            AND serv_empr = %s 
            AND serv_fili = %s 
            ORDER BY serv_id
            FOR UPDATE
            """,
            [ordem_id, empresa_id, filial_id]
        )
        results = cursor.fetchall()
        
        # Encontra o próximo serv_id disponível
        if not results:
            novo_id = 1
            next_sequ = 1
        else:
            # Pega todos os IDs e sequências existentes
            ids = [row[0] for row in results]
            sequs = [row[1] for row in results]
            
            # Encontra o próximo ID disponível
            ids_sorted = sorted(ids)
            novo_id = 1
            for id_atual in ids_sorted:
                if novo_id < id_atual:
                    break
                novo_id = id_atual + 1
            
            # Encontra a próxima sequência disponível
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
