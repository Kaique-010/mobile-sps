import os
import django
from django.conf import settings
from django.test import RequestFactory
from rest_framework.request import Request
import sys

# Setup Django
sys.path.append('D:/mobile-sps')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.utils import get_db_from_slug
from OrdemdeServico.Views.ordem_viewset import OrdemViewSet
from OrdemdeServico.models import Ordemservico

def debug_viewset():
    print("=== DEBUG VIEWSET ===")
    
    # 1. Register DB
    try:
        get_db_from_slug('eletro')
        print("✅ Banco 'eletro' registrado.")
    except Exception as e:
        print(f"❌ Erro ao registrar banco: {e}")
        return

    # 2. Setup Request
    factory = RequestFactory()
    # Test specific corrupt order found: 107144
    request = factory.get('/api/eletro/entidades/ordem-servico/', {
        'ordering': '-orde_data_aber', 
        'orde_nume': '107144',
        'limit': 10
    })
    
    # Wrap in DRF Request
    drf_request = Request(request)
    
    # 3. Instantiate ViewSet
    view = OrdemViewSet()
    view.request = drf_request
    view.format_kwarg = None
    view.args = ()
    view.kwargs = {'slug': 'eletro'} # MultiDB mixin needs this or similar?
    # BaseMultiDBModelViewSet uses self.kwargs.get('slug') or logic to find DB.
    # Let's check get_banco() implementation if needed.
    # Usually it parses URL or takes from request.
    # We'll see.
    
    # Manually set the database to ensure it uses 'eletro'
    # BaseMultiDBModelViewSet might rely on 'get_banco'
    # Let's monkeypatch get_banco just in case, or trust it works with kwargs.
    def mock_get_banco():
        return 'eletro'
    view.get_banco = mock_get_banco

    # 4. Get QuerySet
    try:
        qs = view.get_queryset()
        print(f"QuerySet created. Query: {str(qs.query)}")
    except Exception as e:
        print(f"❌ Error creating queryset: {e}")
        return

    # 5. Apply Filtering & Ordering (Manually invoke backends)
    # We want to test SafeOrderingFilter specifically.
    from OrdemdeServico.Views.ordem_viewset import SafeOrderingFilter
    backend = SafeOrderingFilter()
    
    try:
        qs_ordered = backend.filter_queryset(drf_request, qs, view)
        print(f"QuerySet ordered. SQL: {str(qs_ordered.query)}")
    except Exception as e:
        print(f"❌ Error applying ordering: {e}")
        return

    # 6. Iterate to trigger execution
    print("\n=== ITERATING QUERYSET ===")
    try:
        count = 0
        for item in qs_ordered[:20]: # Fetch first 20
            # Check if field is deferred
            if count == 0:
                print(f"Deferred fields: {item.get_deferred_fields()}")
            
            # Accessing fields to ensure they are loaded
            val = item.orde_data_aber
            print(f"Item {item.pk}: DataAber={val} (Type: {type(val)})")
            
            # Check other corrupt fields
            print(f"Item {item.pk}: DataRepr={item.orde_data_repr} (Type: {type(item.orde_data_repr)})")
            print(f"Item {item.pk}: DataFech={item.orde_data_fech} (Type: {type(item.orde_data_fech)})")
            count += 1
        print(f"✅ Successfully iterated {count} items.")
    except Exception as e:
        print(f"❌ CRASH during iteration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_viewset()
