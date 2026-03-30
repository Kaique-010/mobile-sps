from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction

from core.utils import get_licenca_db_config
from GestaoObras.models import (
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


class BaseMultiDBModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_banco(self):
        return get_licenca_db_config(self.request)

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["banco"] = self.get_banco()
        return ctx

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data
        if isinstance(data, dict):
            data.setdefault(self.empr_field, request.headers.get("X-Empresa") or request.query_params.get("empr"))
            data.setdefault(self.fili_field, request.headers.get("X-Filial") or request.query_params.get("fili"))
        serializer = self.get_serializer(data=data, many=isinstance(data, list))
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ObraViewSet(BaseMultiDBModelViewSet):
    serializer_class = ObraSerializer
    empr_field = "obra_empr"
    fili_field = "obra_fili"

    def get_queryset(self):
        banco = self.get_banco()
        empresa = (
            self.request.query_params.get("obra_empr")
            or self.request.query_params.get("empresa_id")
            or self.request.query_params.get("empr")
        )
        filial = (
            self.request.query_params.get("obra_fili")
            or self.request.query_params.get("filial_id")
            or self.request.query_params.get("fili")
        )
        qs = Obra.objects.using(banco)
        if empresa and filial:
            qs = qs.filter(obra_empr=empresa, obra_fili=filial)
        return qs.order_by("-obra_codi")


class ObraEtapaViewSet(BaseMultiDBModelViewSet):
    serializer_class = ObraEtapaSerializer
    empr_field = "etap_empr"
    fili_field = "etap_fili"

    def get_queryset(self):
        banco = self.get_banco()
        empresa = self.request.query_params.get("etap_empr") or self.request.query_params.get("empr")
        filial = self.request.query_params.get("etap_fili") or self.request.query_params.get("fili")
        obra_id = self.request.query_params.get("etap_obra") or self.request.query_params.get("obra_id")
        qs = ObraEtapa.objects.using(banco)
        if empresa and filial:
            qs = qs.filter(etap_empr=empresa, etap_fili=filial)
        if obra_id:
            qs = qs.filter(etap_obra_id=obra_id)
        return qs.order_by("etap_orde", "id")


class ObraMaterialMovimentoViewSet(BaseMultiDBModelViewSet):
    serializer_class = ObraMaterialMovimentoSerializer
    empr_field = "movm_empr"
    fili_field = "movm_fili"

    def get_queryset(self):
        banco = self.get_banco()
        empresa = self.request.query_params.get("movm_empr") or self.request.query_params.get("empr")
        filial = self.request.query_params.get("movm_fili") or self.request.query_params.get("fili")
        obra_id = self.request.query_params.get("movm_obra") or self.request.query_params.get("obra_id")
        etapa_id = self.request.query_params.get("movm_etap") or self.request.query_params.get("etapa_id")
        qs = ObraMaterialMovimento.objects.using(banco)
        if empresa and filial:
            qs = qs.filter(movm_empr=empresa, movm_fili=filial)
        if obra_id:
            qs = qs.filter(movm_obra_id=obra_id)
        if etapa_id:
            qs = qs.filter(movm_etap_id=etapa_id)
        return qs.order_by("-movm_data", "-movm_codi")


class ObraLancamentoFinanceiroViewSet(BaseMultiDBModelViewSet):
    serializer_class = ObraLancamentoFinanceiroSerializer
    empr_field = "lfin_empr"
    fili_field = "lfin_fili"

    def get_queryset(self):
        banco = self.get_banco()
        empresa = self.request.query_params.get("lfin_empr") or self.request.query_params.get("empr")
        filial = self.request.query_params.get("lfin_fili") or self.request.query_params.get("fili")
        obra_id = self.request.query_params.get("lfin_obra") or self.request.query_params.get("obra_id")
        etapa_id = self.request.query_params.get("lfin_etap") or self.request.query_params.get("etapa_id")
        tipo = self.request.query_params.get("lfin_tipo")
        qs = ObraLancamentoFinanceiro.objects.using(banco)
        if empresa and filial:
            qs = qs.filter(lfin_empr=empresa, lfin_fili=filial)
        if obra_id:
            qs = qs.filter(lfin_obra_id=obra_id)
        if etapa_id:
            qs = qs.filter(lfin_etap_id=etapa_id)
        if tipo:
            qs = qs.filter(lfin_tipo=tipo)
        return qs.order_by("-lfin_dcom", "-lfin_codi")


class ObraProcessoViewSet(BaseMultiDBModelViewSet):
    serializer_class = ObraProcessoSerializer
    empr_field = "proc_empr"
    fili_field = "proc_fili"

    def get_queryset(self):
        banco = self.get_banco()
        empresa = self.request.query_params.get("proc_empr") or self.request.query_params.get("empr")
        filial = self.request.query_params.get("proc_fili") or self.request.query_params.get("fili")
        obra_id = self.request.query_params.get("proc_obra") or self.request.query_params.get("obra_id")
        etapa_id = self.request.query_params.get("proc_etap") or self.request.query_params.get("etapa_id")
        qs = ObraProcesso.objects.using(banco)
        if empresa and filial:
            qs = qs.filter(proc_empr=empresa, proc_fili=filial)
        if obra_id:
            qs = qs.filter(proc_obra_id=obra_id)
        if etapa_id:
            qs = qs.filter(proc_etap_id=etapa_id)
        return qs.order_by("-proc_codi")
