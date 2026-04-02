from ...models import Ordemprodfotos, Ordemproditens, Ordemprodmate, Etapa
from ..serializers import (
    OrdemprodfotosSerializer,
    OrdemproditensSerializer,
    )
from .base import BaseMultiDBModelViewSet


class OrdemprodfotosViewSet(BaseMultiDBModelViewSet):
    queryset = Ordemprodfotos.objects.all()
    serializer_class = OrdemprodfotosSerializer
    filterset_fields = ['orpr_codi', 'orpr_empr', 'orpr_fili']


class OrdemproditensViewSet(BaseMultiDBModelViewSet):
    queryset = Ordemproditens.objects.all()
    serializer_class = OrdemproditensSerializer
    filterset_fields = ['orpr_codi', 'orpr_fili', 'orpr_pedi']


