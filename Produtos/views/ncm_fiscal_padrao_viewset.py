from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from core.decorator import ModuloRequeridoMixin
from core.utils import get_licenca_db_config, get_ncm_master_db

from CFOP.models import NcmFiscalPadrao
from Produtos.models import Ncm
from CFOP.cst_utils import get_csts_por_regime
from Licencas.models import Filiais

from ..serializers.ncm_fiscal_padrao_serializer import NcmFiscalPadraoSerializer


class NcmFiscalPadraoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = "Produtos"
    serializer_class = NcmFiscalPadraoSerializer
    permission_classes = [IsAuthenticated]

    def _get_banco(self):
        return get_licenca_db_config(self.request)

    def _get_ncm_db(self):
        return get_ncm_master_db(self._get_banco())

    def get_queryset(self):
        banco = self._get_banco()
        return NcmFiscalPadrao.objects.using(banco).all().order_by("ncm_id")

    def _build_ncm_map(self, itens):
        ncm_ids = {getattr(item, "ncm_id", None) for item in itens}
        ncm_ids.discard(None)
        if not ncm_ids:
            return {}
        ncm_db = self._get_ncm_db()
        ncms = Ncm.objects.using(ncm_db).filter(pk__in=list(ncm_ids))
        return {ncm.pk: {"codigo": ncm.pk, "descricao": ncm.ncm_desc} for ncm in ncms}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["banco"] = self._get_banco()
        context["ncm_db"] = self._get_ncm_db()
        ncm_map = getattr(self, "_ncm_map", None)
        if ncm_map is not None:
            context["ncm_map"] = ncm_map
        return context

    def _normalize_payload(self, payload):
        if hasattr(payload, "copy"):
            data = payload.copy()
        else:
            data = dict(payload)
        for k, v in list(data.items()):
            if v == "":
                data[k] = None
        return data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        itens = page if page is not None else queryset
        self._ncm_map = self._build_ncm_map(itens)
        serializer = self.get_serializer(itens, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._ncm_map = self._build_ncm_map([instance])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._normalize_payload(request.data))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=self._normalize_payload(request.data), partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    
    @action(detail=False, methods=["get"], url_path="buscancm")
    def buscancm(self, request, *args, **kwargs):
        q = request.query_params.get("q") or request.query_params.get("search") or ""
        q = str(q).strip()
        if not q:
            return Response([])

        try:
            limit = int(request.query_params.get("limit") or 20)
        except Exception:
            limit = 20
        limit = max(1, min(limit, 100))

        ncm_db = self._get_ncm_db()
        filtros = Q(ncm_desc__icontains=q)
        try:
            filtros |= Q(pk__startswith=q)
        except Exception:
            try:
                filtros |= Q(pk=int(q))
            except Exception:
                pass

        qs = Ncm.objects.using(ncm_db).filter(filtros).order_by("pk")[:limit]
        return Response(
            [
                {
                    "ncm_id": str(ncm.pk),
                    "ncm": ncm.ncm_desc,
                    "codigo": ncm.pk,
                    "descricao": ncm.ncm_desc,
                }
                for ncm in qs
            ]
        )

    @action(detail=True, methods=["get"], url_path="buscancm")
    def buscancm_detail(self, request, *args, **kwargs):
        instance = self.get_object()
        ncm_db = self._get_ncm_db()
        ncm = Ncm.objects.using(ncm_db).filter(pk=instance.ncm_id).first()
        if ncm is None:
            return Response({"error": "NCM não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"codigo": ncm.pk, "descricao": ncm.ncm_desc})

    @action(detail=False, methods=["get"], url_path="buscacsts")
    def csts(self, request, *args, **kwargs):
        banco = self._get_banco()
        empresa_id = (
            request.query_params.get("empresa")
            or request.headers.get("X-Empresa")
            or request.session.get("empresa_id")
            or 1
        )
        filial_id = (
            request.query_params.get("filial")
            or request.headers.get("X-Filial")
            or request.session.get("filial_id")
            or 1
        )
        try:
            empresa_id = int(empresa_id)
        except Exception:
            empresa_id = 1
        try:
            filial_id = int(filial_id)
        except Exception:
            filial_id = 1

        try:
            filial = Filiais.objects.using(banco).filter(empr_empr=empresa_id, empr_codi=filial_id).first()
            regime = str(getattr(filial, "empr_regi_trib", None) or "1") if filial else "1"
        except Exception:
            regime = "1"

        csts = get_csts_por_regime(regime)
        formatted_csts = {k: [{"codigo": a, "descricao": b} for a, b in v] for k, v in csts.items()}

        return Response(
            {
                "metadata": {
                    "empresa": empresa_id,
                    "filial": filial_id,
                    "regime_codigo": regime,
                    "regime_descricao": (
                        "Simples Nacional"
                        if regime == "1"
                        else "Regime Normal"
                        if regime == "3"
                        else "Simples Nacional - Excesso"
                    ),
                },
                "tributos": formatted_csts,
            }
        )
