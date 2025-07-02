from rest_framework.viewsets import ModelViewSet
from .models import ComissaoSps
from .serializers import ComissaoSpsSerializer
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin

class ComissaoSpsViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo = 'comissoes'
    queryset = ComissaoSps.objects.all()
    serializer_class = ComissaoSpsSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return ComissaoSps.objects.using(banco).all()

    def get_serializer_class(self):
        return ComissaoSpsSerializer

    def perform_create(self, serializer):
        banco = get_licenca_db_config(self.request) or 'default'
        serializer.save()

    def perform_update(self, serializer):
        banco = get_licenca_db_config(self.request) or 'default'
        serializer.save()

    def perform_destroy(self, instance):
        banco = get_licenca_db_config(self.request) or 'default'
        instance.delete(using=banco)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
