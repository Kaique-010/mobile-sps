from rest_framework import viewsets
from .models import LicencaGlobal
from .serializers import LicencaGlobalSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class LicencaGlobalViewSet(viewsets.ModelViewSet):
    queryset = LicencaGlobal.objects.all()
    serializer_class = LicencaGlobalSerializer
    
    
    def get_queryset(self):
        return LicencaGlobal.objects.using('global').all()

    def perform_create(self, serializer):
        serializer.save(using='global')

    def perform_update(self, serializer):
        serializer.save(using='global')

    def perform_destroy(self, instance):
        instance.delete(using='global')

    @action(detail=False, methods=['get'], url_path='modulos')
    def modulos_ativos(self, request, slug=None):
        try:
            licenca = LicencaGlobal.objects.get(lice_slug=slug, lice_stat=True)
        except LicencaGlobal.DoesNotExist:
            return Response({'erro': 'Licença não encontrada ou inativa'}, status=404)

        modulos = {
            key: value
            for key, value in LicencaGlobalSerializer(licenca).data.items()
            if key.startswith('modulo_') and value is True
        }
        return Response({'slug': slug, 'modulos_ativos': modulos})
