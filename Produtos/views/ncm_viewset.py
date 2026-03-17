from django.db.models import Q
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.utils import get_ncm_master_db

from ..models import Ncm
from ..serializers.ncm_serializer import NcmSerializer


class NcmViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = "Produtos"
    serializer_class = NcmSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["ncm_codi", "ncm_desc"]
    lookup_field = "ncm_codi"
    lookup_value_regex = r"[^/]+"

    def _get_ncm_db(self):
        banco = get_licenca_db_config(self.request)
        return get_ncm_master_db(banco)

    def get_queryset(self):
        ncm_db = self._get_ncm_db()
        qs = Ncm.objects.using(ncm_db).all()
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(ncm_codi__icontains=q) | Q(ncm_desc__icontains=q))
        return qs.order_by("ncm_codi")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        banco = get_licenca_db_config(self.request)
        context["banco"] = banco
        context["ncm_db"] = get_ncm_master_db(banco)
        return context
