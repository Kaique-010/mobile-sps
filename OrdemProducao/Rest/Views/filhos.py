from ...models import Ordemprodfotos, Ordemproditens, Ordemprodmate, Ordemprodetapa
from ..serializers import (
    OrdemprodfotosSerializer,
    OrdemproditensSerializer,
    OrdemprodmateSerializer,
    OrdemprodetapaSerializer,
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


class OrdemprodmateViewSet(BaseMultiDBModelViewSet):
    queryset = Ordemprodmate.objects.all()
    serializer_class = OrdemprodmateSerializer
    filterset_fields = ['orpm_orpr', 'orpm_prod']


class OrdemprodetapaViewSet(BaseMultiDBModelViewSet):
    queryset = Ordemprodetapa.objects.all()
    serializer_class = OrdemprodetapaSerializer
    filterset_fields = ['opet_orpr', 'opet_func', 'opet_etap']
