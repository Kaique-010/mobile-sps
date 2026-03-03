
import os
import django
from django.db.models import Q, Case, When, Value, DateField

# Set correct settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from OrdemdeServico.models import Ordemservico
from core.registry import get_licenca_db_config as get_db_from_slug
from OrdemdeServico.serializers import OrdemServicoSerializer

def verify_fix():
    # Identificar o banco correto
    slug = 'eletro'
    try:
        banco = get_db_from_slug(slug)
        print(f"Usando banco: {banco} para slug: {slug}")
    except Exception as e:
        # Se falhar o registro por algum motivo, tenta pegar da config se ja tiver
        print(f"Erro ao registrar: {e}")
        banco = 'eletro'

    if not banco:
        print("Banco não encontrado!")
        return

    # Listar campos do modelo para verificar se esquecemos algum DateField
    print("\nVerificando campos do modelo Ordemservico:")
    from django.db import models
    date_fields = []
    for field in Ordemservico._meta.get_fields():
        if isinstance(field, (models.DateField, models.DateTimeField)):
            print(f"  - {field.name} ({type(field).__name__})")
            date_fields.append(field.name)
        
    print(f"Total de campos de data: {len(date_fields)}")
    
    # Campos que estamos deferindo atualmente
    deferred_fields = [
        'orde_data_aber', 'orde_hora_aber', 'orde_data_repr', 
        'orde_data_fech', 'orde_hora_fech', 'orde_nf_data', 'orde_ulti_alte'
    ]
    
    missing_defer = [f for f in date_fields if f not in deferred_fields]
    print(f"Campos de data NÃO deferidos: {missing_defer}")

    try:
        # Simular o queryset do OrdemViewSet

        qs = Ordemservico.objects.using(banco).defer(
            'orde_data_aber', 'orde_hora_aber', 'orde_data_repr', 
            'orde_data_fech', 'orde_hora_fech', 'orde_nf_data', 'orde_ulti_alte'
        ).all()

        # Filtros básicos - COMENTADO PARA ACHAR OS 10597
        # qs = qs.filter(orde_seto__isnull=False).exclude(orde_seto=0)
        # qs = qs.filter(orde_stat_orde__in=[0, 1, 2, 3, 5, 21, 22])

        # Filtros de data - COMENTADO PARA TESTAR SE TRAZ REGISTRO RUIM SEM EXPLODIR
        # qs = qs.filter(orde_data_aber__year__gte=1900, orde_data_aber__year__lte=2100)
        # qs = qs.filter(
        #    Q(orde_data_fech__isnull=True) | (Q(orde_data_fech__year__gte=1900) & Q(orde_data_fech__year__lte=2100))
        # )
        # qs = qs.filter(
        #    Q(orde_nf_data__isnull=True) | (Q(orde_nf_data__year__gte=1900) & Q(orde_nf_data__year__lte=2100))
        # )
        # qs = qs.filter(
        #    Q(orde_data_repr__isnull=True) | (Q(orde_data_repr__year__gte=1900) & Q(orde_data_repr__year__lte=2100))
        # )
        # qs = qs.filter(
        #    Q(orde_ulti_alte__isnull=True) | (Q(orde_ulti_alte__year__gte=1900) & Q(orde_ulti_alte__year__lte=2100))
        # )
        
        # Tentar pegar especificamente a OS do cliente 148
        print("Tentando buscar OS do cliente 148...")
        qs_148 = qs.filter(orde_enti=148)
        
        # Anotação segura (A correção aplicada)
        qs_148 = qs_148.annotate(
            safe_data_aber=Case(
                When(orde_data_aber__year__gte=1900, orde_data_aber__year__lte=2100, then='orde_data_aber'),
                default=Value(None),
                output_field=DateField()
            )
        )
        
        # Ordenar por safe_data_aber
        qs_148 = qs_148.order_by('-safe_data_aber')

        print(f"Contando registros para cliente 148...")
        count = qs_148.count()
        print(f"Encontrados {count} registros para cliente 148")

        if count > 0:
            print("Tentando listar registros do cliente 148...")
            results = list(qs_148[:10])
            for item in results:
                print(f"Item: {item.orde_nume}")
                print(f"Safe Data Aber: {getattr(item, 'safe_data_aber', 'N/A')}")
                # Tentar acessar o campo bruto (deve ser deferido, mas vamos ver se o driver reclama ao acessar)
                # print(f"Data Aber Bruta: {item.orde_data_aber}") # CUIDADO: Isso pode quebrar o script

                # Testar Serialização
                print(f"Serializando item {item.orde_nume}...")
                
                # Contexto necessário para o serializer (banco)
                class MockRequest:
                    def __init__(self):
                        self.user = None
                        self.query_params = {}
                
                context = {
                    'banco': banco,
                    'request': MockRequest()
                }
                
                try:
                    serializer = OrdemServicoSerializer(item, context=context)
                    data = serializer.data
                    print(f"  Data Aber (serializada): {data.get('orde_data_aber')}")
                except Exception as e:
                    print(f"  ERRO ao serializar item {item.orde_nume}: {e}")

        print("SUCESSO: Teste cliente 148 concluído!")
        return # Encerrar por aqui para este teste


        # Ordenação segura
        qs = qs.order_by('-safe_data_aber', '-orde_nume')

        print("Queryset construído. Tentando buscar o primeiro registro...")
        first_item = qs.first()
        print(f"Primeiro item: {first_item.orde_nume if first_item else 'Nenhum'}")
        
        print("Tentando iterar sobre os primeiros 10 registros...")
        results = list(qs[:10])
        for i, item in enumerate(results):
            print(f"Item {i}: {item.orde_nume} - Data Aber (safe): {getattr(item, 'safe_data_aber', 'N/A')}")
            
        print("SUCESSO: A listagem e ordenação funcionaram sem erro de data!")

        # Testar Serialização
        print("\nTestando serialização com OrdemServicoSerializer...")
        
        # Contexto necessário para o serializer (banco)
        class MockRequest:
            def __init__(self):
                self.user = None
                self.query_params = {}
        
        context = {
            'banco': banco,
            'request': MockRequest()
        }
        
        for i, item in enumerate(results[:5]):
            print(f"Serializando item {item.orde_nume}...")
            try:
                serializer = OrdemServicoSerializer(item, context=context)
                data = serializer.data
                print(f"  Data Aber (serializada): {data.get('orde_data_aber')}")
            except Exception as e:
                print(f"  ERRO ao serializar item {item.orde_nume}: {e}")

        print("SUCESSO: Serialização concluída!")

    except Exception as e:
        print(f"ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_fix()
