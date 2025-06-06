from django.db import connections
from django.db.models import Max
from O_S.models import Osservico, Os, Ospecas, 
from O_S.models import ServicosOs, Os, PecasOs


def get_next_sequential_id(banco, model, os_os, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            [os_os, empresa_id, filial_id]
        )
        ids = [row[0] for row in cursor.fetchall()]
        
        # Se não houver IDs, começa do 1
        if not ids:
            ultimo_local = 0
        else:
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs


def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):
    """
    Função específica para peças, mantida para compatibilidade
    """
    return get_next_sequential_id(
        banco=banco,
        model=Os,
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
    Função para gerar IDs sequenciais de serviços
    """
    with connections[banco].cursor() as cursor:
        # Lock the rows for this order
        cursor.execute(
            """
            SELECT serv_sequ 
            FROM servicosos 
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
from O_S.models import ServicosOs, Os, PecasOs

def get_next_sequential_id(banco, model, ordem_id, empresa_id, filial_id, id_field, ordem_field, empresa_field, filial_field):
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
            # Encontra o maior local
            ultimo_local = max(int(str(id_)[-2:]) for id_ in ids if id_ is not None)

    novo_local = ultimo_local + 1
    novo_id = int(f"{os_os}{novo_local:02d}")

    return novo_id


def get_next_item_number_sequence(banco, peca_os, peca_empr, peca_fili):

