from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import (
    Obra,
    ObraEtapa,
    ObraLancamentoFinanceiro,
    ObraMaterialMovimento,
    ObraProcesso,
)
from .serializers import (
    ObraEtapaSerializer,
    ObraLancamentoFinanceiroSerializer,
    ObraMaterialMovimentoSerializer,
    ObraProcessoSerializer,
    ObraSerializer,
)


class ObraViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Obra.objects.all()
    serializer_class = ObraSerializer


class ObraEtapaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ObraEtapa.objects.all()
    serializer_class = ObraEtapaSerializer


class ObraMaterialMovimentoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ObraMaterialMovimento.objects.all()
    serializer_class = ObraMaterialMovimentoSerializer


class ObraLancamentoFinanceiroViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ObraLancamentoFinanceiro.objects.all()
    serializer_class = ObraLancamentoFinanceiroSerializer


class ObraProcessoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ObraProcesso.objects.all()
    serializer_class = ObraProcessoSerializer
