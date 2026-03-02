
import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from core.utils import get_db_from_slug
from Notas_Fiscais.models import Nota, NotaEvento

try:
    # O banco no log é 'saveweb001'
    slug = 'saveweb001'
    # Configura a conexão com o banco dinâmico
    db_name = get_db_from_slug(slug)
    
    nota = Nota.objects.using(db_name).get(id=3)
    
    print(f"--- NOTA {nota.id} ---")
    print(f"Status: {nota.status}")
    print(f"Chave Acesso Atual: '{nota.chave_acesso}'")
    print(f"Motivo Status: '{nota.motivo_status}'")
    print(f"Protocolo: '{nota.protocolo_autorizacao}'")
    
    print("\n--- EVENTOS ---")
    eventos = NotaEvento.objects.using(db_name).filter(nota=nota).order_by('id')
    for ev in eventos:
        print(f"[{ev.id}] Tipo: {ev.tipo} | Desc: {ev.descricao[:100]}...")

except Exception as e:
    print(f"Erro ao inspecionar: {e}")
