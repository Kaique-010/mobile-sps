import os
import django

# 1. Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.test import RequestFactory
from rest_framework.request import Request
from rest_framework import filters

from core.utils import get_db_from_slug
from OrdemdeServico.view_dash import OrdensEletroViewSet

def debug_dash():
    print("=== DEBUG ORDENS ELETRO VIEWSET ===")
    
    # 1. Register DB
    try:
        get_db_from_slug('eletro')
        print("✅ Banco 'eletro' registrado.")
    except Exception as e:
        print(f"❌ Erro ao registrar banco: {e}")
        return

    # 2. Setup Request
    factory = RequestFactory()
    # Trigger default ordering (-data_abertura) and target corrupt order
    request = factory.get('/api/eletro/entidades/ordens-eletro/', {
        'limit': 10,
        'ordem_de_servico': '107144'
    })
    drf_request = Request(request)

    # 3. Instantiate ViewSet
    view = OrdensEletroViewSet()
    view.request = drf_request
    view.format_kwarg = None
    view.args = ()
    view.kwargs = {'slug': 'eletro'}

    # Monkeypatch get_licenca_db_config in sys.modules['OrdemdeServico.view_dash']
    import OrdemdeServico.view_dash
    OrdemdeServico.view_dash.get_licenca_db_config = lambda r: 'eletro'
    
    # 4. Get QuerySet
    try:
        # Apply filters manually since we are not going through dispatch
        qs = view.get_queryset()
        
        # Apply filter backend
        backend = view.filter_backends[0]() # DjangoFilterBackend
        qs = backend.filter_queryset(drf_request, qs, view)
        
        print(f"QuerySet created. Query: {str(qs.query)}")
    except Exception as e:
        print(f"❌ Error creating queryset: {e}")
        return

    # 5. Iterate to trigger execution
    print("\n=== ITERATING QUERYSET ===")
    try:
        count = 0
        for item in qs[:10]:
            print(f"Item {item.pk}: DataAber={item.data_abertura}")
            count += 1
        print(f"✅ Successfully iterated {count} items.")
    except Exception as e:
        print(f"❌ CRASH during iteration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_dash()