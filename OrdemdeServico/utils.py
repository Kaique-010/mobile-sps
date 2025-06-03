from django.db import connections

def get_next_item_number_sequence(banco, peca_orde, peca_empr, peca_fili):
    try:
        with connections[banco].cursor() as cursor:
           
            cursor.execute("""
                SELECT COALESCE(MAX(peca_id), 0) + 1 
                FROM ordemservicopecas 
                WHERE peca_empr = %s AND peca_fili = %s AND peca_orde = %s
            """, [peca_empr, peca_fili, peca_orde])
            next_id = cursor.fetchone()[0]
            
            if next_id == 1:  
                return 1
            return next_id
    except Exception as e:
       
        with connections[banco].cursor() as cursor:
            cursor.execute("SELECT nextval('ordemservicopecas_peca_id_seq')")
            return cursor.fetchone()[0]