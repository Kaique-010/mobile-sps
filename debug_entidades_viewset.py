import os
import django
from django.conf import settings

# 1. Configurar Settings Mínimos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from core.utils import get_db_from_slug
from Entidades.Views.relatorios import OrdemServicoViewSet
from OrdemdeServico.serializers import OrdemServicoSerializer

def debug_entidades():
    print("=== DEBUG ENTIDADES ORDEM SERVICO VIEWSET ===")
    
    # 1. Register DB
    try:
        get_db_from_slug('eletro')
        print("✅ Banco 'eletro' registrado.")
    except Exception as e:
        print(f"❌ Erro ao registrar banco: {e}")
        return

    # 2. Setup Request
    factory = APIRequestFactory()
    request = factory.get('/api/eletro/entidades/ordem-servico/', {'ordering': '-orde_data_aber'})
    request.session = {}
    request.cliente_id = 148  # ID do cliente para teste
    request.banco = 'eletro'
    request.query_params = request.GET
    
    # 3. Setup View
    view = OrdemServicoViewSet()
    view.request = request
    view.format_kwarg = None
    view.args = ()
    view.kwargs = {'slug': 'eletro'} 
    
    # 4. Get QuerySet
    try:
        qs = view.get_queryset()
        # Filtra pela ordem problemática para teste focado
        # Mas mantendo o filtro de cliente aplicado pelo get_queryset original
        qs = qs.filter(orde_nume=107144)
        
        print(f"QuerySet created. Query: {qs.query}")
    except Exception as e:
        print(f"❌ CRASH getting queryset: {e}")
        return

    # 5. Serialize
    print("\n=== SERIALIZING QUERYSET ===")
    try:
        serializer = OrdemServicoSerializer(qs, many=True, context={'request': request, 'banco': 'eletro'})
        data = serializer.data
        print(f"✅ Successfully serialized {len(data)} items.")
        if len(data) > 0:
            item = data[0]
            print(f"Item 107144 Data Aber: {item.get('orde_data_aber')}")
            print(f"Item 107144 Data Fech: {item.get('orde_data_fech')}")
    except Exception as e:
        print(f"❌ CRASH during serialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_entidades()
