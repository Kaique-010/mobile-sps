from rest_framework import viewsets
from .models import ImplantacaoTela
from .serializers import ImplantacaoTelaSerializer
from .services.implantacao_tela_service import ImplantacaoTelaService

class ImplantacaoTelaViewSet(viewsets.ModelViewSet):
    serializer_class = ImplantacaoTelaSerializer

    def get_queryset(self):
        return ImplantacaoTelaService.listar_implantacoes(self.request)

    def perform_create(self, serializer):
        ImplantacaoTelaService.criar_implantacao(serializer.validated_data, self.request)

    def perform_update(self, serializer):
        ImplantacaoTelaService.atualizar_implantacao(self.get_object(), serializer.validated_data, self.request)

    def perform_destroy(self, instance):
        ImplantacaoTelaService.deletar_implantacao(instance, self.request)