from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from core.utils import get_licenca_db_config
from comissoes.models import RegraComissao, LancamentoComissao, PagamentoComissao
from comissoes.services import CadastroComissaoService, GeracaoComissaoService, PagamentoComissaoService
from .serializers import (
    RegraComissaoSerializer,
    LancamentoComissaoSerializer,
    PagamentoComissaoSerializer,
)


class _BaseMixin:
    lookup_value_regex = r"\d+"

    def get_banco(self):
        return get_licenca_db_config(self.request) or "default"

    def get_empresa_id(self):
        return self.request.session.get("empresa_id")

    def get_filial_id(self):
        return self.request.session.get("filial_id")


class RegraComissaoViewSet(_BaseMixin, viewsets.ModelViewSet):
    serializer_class = RegraComissaoSerializer

    def get_queryset(self):
        banco = self.get_banco()
        qs = RegraComissao.objects.using(banco).all()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        bene = self.request.query_params.get("beneficiario")
        ativo = self.request.query_params.get("ativo")

        if empresa_id:
            qs = qs.filter(regc_empr=int(empresa_id))
        if filial_id:
            qs = qs.filter(regc_fili=int(filial_id))
        if bene:
            qs = qs.filter(regc_bene=int(bene))
        if ativo in ("0", "1", "true", "false", "True", "False"):
            qs = qs.filter(regc_ativ=str(ativo).lower() in ("1", "true"))
        return qs.order_by("regc_id")

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        if not empresa_id or not filial_id:
            return Response({"detail": "Selecione empresa e filial para continuar."}, status=status.HTTP_400_BAD_REQUEST)
        service = CadastroComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))
        regra = service.salvar_regra(
            beneficiario_id=data["regc_bene"],
            percentual=data["regc_perc"],
            ativo=data.get("regc_ativ", True),
            data_ini=data.get("regc_data_ini"),
            data_fim=data.get("regc_data_fim"),
        )
        return Response(self.get_serializer(regra).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # atualiza via service garantindo consistência
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        banco = self.get_banco()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        if not empresa_id or not filial_id:
            return Response({"detail": "Selecione empresa e filial para continuar."}, status=status.HTTP_400_BAD_REQUEST)
        service = CadastroComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))
        regra = service.atualizar_regra(
            regra_id=instance.regc_id,
            beneficiario_id=data.get("regc_bene", instance.regc_bene),
            percentual=data.get("regc_perc", instance.regc_perc),
            ativo=data.get("regc_ativ", instance.regc_ativ),
            data_ini=data.get("regc_data_ini", instance.regc_data_ini),
            data_fim=data.get("regc_data_fim", instance.regc_data_fim),
        )
        return Response(self.get_serializer(regra).data)


class LancamentoComissaoViewSet(_BaseMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = LancamentoComissaoSerializer

    def get_queryset(self):
        banco = self.get_banco()
        qs = LancamentoComissao.objects.using(banco).all()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        bene = self.request.query_params.get("beneficiario")
        status_param = self.request.query_params.get("status")
        tipo_origem = self.request.query_params.get("tipo_origem")
        doc = self.request.query_params.get("documento")

        if empresa_id:
            qs = qs.filter(lcom_empr=int(empresa_id))
        if filial_id:
            qs = qs.filter(lcom_fili=int(filial_id))
        if bene:
            qs = qs.filter(lcom_bene=int(bene))
        if status_param:
            try:
                qs = qs.filter(lcom_stat=int(status_param))
            except Exception:
                pass
        if tipo_origem:
            qs = qs.filter(lcom_tipo_origem=tipo_origem)
        if doc:
            qs = qs.filter(lcom_docu=doc)
        return qs.order_by("lcom_data", "lcom_id")

    @action(detail=False, methods=["post"])
    def gerar(self, request):
        banco = self.get_banco()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        if not empresa_id or not filial_id:
            return Response({"detail": "Selecione empresa e filial para continuar."}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data or {}
        tipo = str(payload.get("tipo_origem") or "").strip()
        doc = str(payload.get("documento") or "").strip()
        data_doc = payload.get("data") or payload.get("lcom_data")
        base = payload.get("base") or payload.get("lcom_base")

        service = GeracaoComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))
        lancs = service.gerar_para_documento(tipo_origem=tipo, documento=doc, data_doc=data_doc, base=base)
        return Response(self.get_serializer(lancs, many=True).data, status=status.HTTP_201_CREATED)


class PagamentoComissaoViewSet(_BaseMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PagamentoComissaoSerializer

    def get_queryset(self):
        banco = self.get_banco()
        qs = PagamentoComissao.objects.using(banco).all()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        bene = self.request.query_params.get("beneficiario")
        if empresa_id:
            qs = qs.filter(pagc_empr=int(empresa_id))
        if filial_id:
            qs = qs.filter(pagc_fili=int(filial_id))
        if bene:
            qs = qs.filter(pagc_bene=int(bene))
        return qs.order_by("-pagc_data", "-pagc_id")

    @action(detail=False, methods=["post"])
    def gerar(self, request):
        banco = self.get_banco()
        empresa_id = self.get_empresa_id()
        filial_id = self.get_filial_id()
        if not empresa_id or not filial_id:
            return Response({"detail": "Selecione empresa e filial para continuar."}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data or {}
        beneficiario_id = int(payload.get("beneficiario_id") or payload.get("beneficiario") or 0)
        data_pagamento = payload.get("data") or payload.get("pagc_data")
        itens = payload.get("itens") or []
        observacao = payload.get("observacao")

        service = PagamentoComissaoService(db_alias=banco, empresa_id=int(empresa_id), filial_id=int(filial_id))
        pagamento = service.gerar_pagamento(
            beneficiario_id=beneficiario_id,
            data_pagamento=data_pagamento,
            itens=itens,
            observacao=observacao,
        )
        return Response(self.get_serializer(pagamento).data, status=status.HTTP_201_CREATED)
