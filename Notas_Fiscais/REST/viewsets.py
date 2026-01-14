# notas_fiscais/api/viewsets.py

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models import Nota, NotaEvento, NotaItem
from decimal import Decimal
from CFOP.models import CFOP
from .serializers import (
    NotaDetailSerializer,
    NotaCreateUpdateSerializer,
)
from ..services.evento_service import EventoService
from core.utils import get_licenca_db_config 
from ..services.nota_service import NotaService
from ..services.calculo_impostos_service import CalculoImpostosService


class NotaViewSet(viewsets.ModelViewSet):
    """
    API de Notas Fiscais (saída).
    GET    /api/notas/           -> lista
    POST   /api/notas/           -> cria
    GET    /api/notas/{id}/      -> detalhe
    PUT    /api/notas/{id}/      -> atualiza completa
    PATCH  /api/notas/{id}/      -> atualiza parcial
    POST   /api/notas/{id}/cancelar/ -> cancela nota
    """

    queryset = Nota.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["modelo", "serie", "numero", "status", "tipo_operacao", "finalidade"]
    search_fields = ["chave_acesso", "destinatario__enti_nome", "destinatario__enti_cnpj", "destinatario__enti_cpf"]
    ordering_fields = ["data_emissao", "numero", "status"]
    ordering = ["-data_emissao", "-numero"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return NotaCreateUpdateSerializer
        return NotaDetailSerializer

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = (
            self.request.query_params.get("empresa")
            or self.request.session.get("empresa_id")
            or self.request.headers.get("X-Empresa")
        )
        filial = (
            self.request.query_params.get("filial")
            or self.request.session.get("filial_id")
            or self.request.headers.get("X-Filial")
        )

        qs = (
            Nota.objects.using(banco)
            .select_related("emitente", "destinatario")
            .prefetch_related("itens__impostos", "eventos")
        )

        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)

        return qs

    def retrieve(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        pk = kwargs.get(self.lookup_field, kwargs.get("pk"))
        empresa = (
            request.query_params.get("empresa")
            or request.session.get("empresa_id")
            or request.headers.get("X-Empresa")
        )
        filial = (
            request.query_params.get("filial")
            or request.session.get("filial_id")
            or request.headers.get("X-Filial")
        )
        qs = (
            Nota.objects.using(banco)
            .select_related("emitente", "destinatario")
            .prefetch_related("itens__impostos", "eventos")
        )
        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)
        obj = qs.filter(pk=pk).first()
        if not obj:
            return Response({"detail": "Nota não encontrada"}, status=status.HTTP_404_NOT_FOUND)
        out = NotaDetailSerializer(obj, context=self.get_serializer_context())
        data_out = dict(out.data)
        itens_qs = (
            NotaItem.objects.using(banco)
            .select_related("impostos")
            .filter(nota=obj)
        )
        tot_prod = Decimal("0")
        tot_desc = Decimal("0")
        tot_icms = Decimal("0")
        tot_ipi = Decimal("0")
        tot_pis = Decimal("0")
        tot_cof = Decimal("0")
        tot_cbs = Decimal("0")
        tot_ibs = Decimal("0")
        cfop_flags = {}
        for it in itens_qs:
            tot_prod += Decimal(str(it.total or 0))
            tot_desc += Decimal(str(it.desconto or 0))
            imp = getattr(it, "impostos", None)
            if imp:
                tot_icms += Decimal(str(imp.icms_valor or 0))
                tot_ipi += Decimal(str(imp.ipi_valor or 0))
                tot_pis += Decimal(str(imp.pis_valor or 0))
                tot_cof += Decimal(str(imp.cofins_valor or 0))
                tot_cbs += Decimal(str(imp.cbs_valor or 0))
                tot_ibs += Decimal(str(imp.ibs_valor or 0))
            cf = (
                CFOP.objects.using(banco)
                .filter(cfop_empr=obj.empresa, cfop_codi=it.cfop)
                .values(
                    "cfop_exig_icms",
                    "cfop_exig_ipi",
                    "cfop_exig_pis_cofins",
                    "cfop_exig_cbs",
                    "cfop_exig_ibs",
                    "cfop_gera_st",
                )
                .first()
            )
            if cf:
                cfop_flags[str(it.id)] = cf
        tot_trib = tot_icms + tot_ipi + tot_pis + tot_cof + tot_cbs + tot_ibs
        total_nota = tot_prod + tot_trib
        data_out["totais"] = {
            "produtos": str(tot_prod.quantize(Decimal("0.01"))),
            "desconto": str(tot_desc.quantize(Decimal("0.01"))),
            "icms": str(tot_icms.quantize(Decimal("0.01"))),
            "ipi": str(tot_ipi.quantize(Decimal("0.01"))),
            "pis": str(tot_pis.quantize(Decimal("0.01"))),
            "cofins": str(tot_cof.quantize(Decimal("0.01"))),
            "cbs": str(tot_cbs.quantize(Decimal("0.01"))),
            "ibs": str(tot_ibs.quantize(Decimal("0.01"))),
            "tributos": str(tot_trib.quantize(Decimal("0.01"))),
            "total": str(total_nota.quantize(Decimal("0.01"))),
        }
        data_out["cfop_flags"] = cfop_flags
        return Response(data_out, status=status.HTTP_200_OK)

    # --------- CREATE ---------
    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id") or request.headers.get("X-Empresa")
        filial = request.session.get("filial_id") or request.headers.get("X-Filial")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        itens = data.pop("itens")
        impostos = data.pop("impostos", [])
        transporte = data.pop("transporte", None)

        impostos_map = {idx: imp for idx, imp in enumerate(impostos)} if impostos else None

        nota = NotaService.criar(
            data=data,
            itens=itens,
            impostos_map=impostos_map,
            transporte=transporte,
            empresa=empresa,
            filial=filial,
            database=banco,
        )

        debug_data = CalculoImpostosService(banco).aplicar_impostos(nota, return_debug=True)
        NotaService.gravar(nota, descricao="Rascunho criado via API")

        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        data_out = dict(out.data)
        if debug_data:
            data_out["debug_calculo"] = debug_data
        return Response(data_out, status=status.HTTP_201_CREATED)

    # --------- UPDATE ---------
    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        partial = kwargs.pop("partial", False)

        nota = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        itens = data.pop("itens")
        impostos = data.pop("impostos", [])
        transporte = data.pop("transporte", None)

        impostos_map = {idx: imp for idx, imp in enumerate(impostos)} if impostos else None

        nota = NotaService.atualizar(
            nota=nota,
            data=data,
            itens=itens,
            impostos_map=impostos_map,
            transporte=transporte,
            database=banco,
        )

        debug_data = CalculoImpostosService(banco).aplicar_impostos(nota, return_debug=True)
        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        data_out = dict(out.data)
        if debug_data:
            data_out["debug_calculo"] = debug_data
        itens_qs = (
            NotaItem.objects.using(banco)
            .select_related("impostos")
            .filter(nota=nota)
        )
        tot_prod = Decimal("0")
        tot_desc = Decimal("0")
        tot_icms = Decimal("0")
        tot_ipi = Decimal("0")
        tot_pis = Decimal("0")
        tot_cof = Decimal("0")
        tot_cbs = Decimal("0")
        tot_ibs = Decimal("0")
        cfop_flags = {}
        for it in itens_qs:
            tot_prod += Decimal(str(it.total or 0))
            tot_desc += Decimal(str(it.desconto or 0))
            imp = getattr(it, "impostos", None)
            if imp:
                tot_icms += Decimal(str(imp.icms_valor or 0))
                tot_ipi += Decimal(str(imp.ipi_valor or 0))
                tot_pis += Decimal(str(imp.pis_valor or 0))
                tot_cof += Decimal(str(imp.cofins_valor or 0))
                tot_cbs += Decimal(str(imp.cbs_valor or 0))
                tot_ibs += Decimal(str(imp.ibs_valor or 0))
            cf = (
                CFOP.objects.using(banco)
                .filter(cfop_empr=nota.empresa, cfop_codi=it.cfop)
                .values(
                    "cfop_exig_icms",
                    "cfop_exig_ipi",
                    "cfop_exig_pis_cofins",
                    "cfop_exig_cbs",
                    "cfop_exig_ibs",
                    "cfop_gera_st",
                )
                .first()
            )
            if cf:
                cfop_flags[str(it.id)] = cf
        tot_trib = tot_icms + tot_ipi + tot_pis + tot_cof + tot_cbs + tot_ibs
        total_nota = tot_prod + tot_trib
        data_out["totais"] = {
            "produtos": str(tot_prod.quantize(Decimal("0.01"))),
            "desconto": str(tot_desc.quantize(Decimal("0.01"))),
            "icms": str(tot_icms.quantize(Decimal("0.01"))),
            "ipi": str(tot_ipi.quantize(Decimal("0.01"))),
            "pis": str(tot_pis.quantize(Decimal("0.01"))),
            "cofins": str(tot_cof.quantize(Decimal("0.01"))),
            "cbs": str(tot_cbs.quantize(Decimal("0.01"))),
            "ibs": str(tot_ibs.quantize(Decimal("0.01"))),
            "tributos": str(tot_trib.quantize(Decimal("0.01"))),
            "total": str(total_nota.quantize(Decimal("0.01"))),
        }
        data_out["cfop_flags"] = cfop_flags
        return Response(data_out, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    # --------- CANCELAR ---------
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa = (
            request.session.get("empresa_id")
            or request.query_params.get("empresa")
            or request.headers.get("X-Empresa")
        )
        filial = (
            request.session.get("filial_id")
            or request.query_params.get("filial")
            or request.headers.get("X-Filial")
        )
        nota = (
            Nota.objects.using(banco)
            .filter(pk=pk, empresa=empresa, filial=filial)
            .first()
        )
        if not nota:
            return Response({"detail": "Nota não encontrada"}, status=status.HTTP_404_NOT_FOUND)

        descricao = request.data.get("descricao", "Cancelamento solicitado via API")
        xml = request.data.get("xml")
        protocolo = request.data.get("protocolo")

        NotaService.cancelar(
            nota=nota,
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def transmitir(self, request, pk=None, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa = (
            request.session.get("empresa_id")
            or request.query_params.get("empresa")
            or request.headers.get("X-Empresa")
        )
        filial = (
            request.session.get("filial_id")
            or request.query_params.get("filial")
            or request.headers.get("X-Filial")
        )
        nota = (
            Nota.objects.using(banco)
            .filter(pk=pk, empresa=empresa, filial=filial)
            .first()
        )
        if not nota:
            return Response({"detail": "Nota não encontrada"}, status=status.HTTP_404_NOT_FOUND)

        if nota.status == 100:
            return Response({"detail": "Nota já autorizada"}, status=status.HTTP_400_BAD_REQUEST)

        chave = request.data.get("chave_acesso")
        protocolo = request.data.get("protocolo")
        xml = request.data.get("xml")
        descricao = request.data.get("descricao") or "Transmitida via painel"

        NotaService.transmitir(
            nota=nota,
            descricao=descricao,
            chave=chave,
            protocolo=protocolo,
            xml=xml,
        )

        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def inutilizar(self, request, pk=None, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id") or request.query_params.get("empresa")
        filial = request.session.get("filial_id") or request.query_params.get("filial")
        nota = (
            Nota.objects.using(banco)
            .filter(pk=pk, empresa=empresa, filial=filial)
            .first()
        )
        if not nota:
            return Response({"detail": "Nota não encontrada"}, status=status.HTTP_404_NOT_FOUND)

        if nota.status == 102:
            return Response({"detail": "Nota já inutilizada"}, status=status.HTTP_400_BAD_REQUEST)

        descricao = request.data.get("descricao", "Inutilização solicitada via API")
        xml = request.data.get("xml")
        protocolo = request.data.get("protocolo")

        NotaService.inutilizar(
            nota=nota,
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def gravar(self, request, pk=None, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id") or request.query_params.get("empresa")
        filial = request.session.get("filial_id") or request.query_params.get("filial")
        nota = (
            Nota.objects.using(banco)
            .filter(pk=pk, empresa=empresa, filial=filial)
            .first()
        )
        if not nota:
            return Response({"detail": "Nota não encontrada"}, status=status.HTTP_404_NOT_FOUND)
        if nota.status == 100:
            return Response({"detail": "Nota já autorizada"}, status=status.HTTP_400_BAD_REQUEST)
        if nota.status == 102:
            return Response({"detail": "Nota já inutilizada"}, status=status.HTTP_400_BAD_REQUEST)
        if nota.status == 101:
            return Response({"detail": "Nota já cancelada"}, status=status.HTTP_400_BAD_REQUEST)
        

        debug_data = CalculoImpostosService(banco).aplicar_impostos(nota, return_debug=True)
        descricao = request.data.get("descricao", "Rascunho criado/atualizado via API")        
        NotaService.gravar(nota, descricao=descricao)
        out = NotaDetailSerializer(nota, context=self.get_serializer_context())
        data_out = dict(out.data)
        if debug_data:
            data_out["debug_calculo"] = debug_data
        return Response(data_out, status=status.HTTP_200_OK)


class NotaEventoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista eventos de notas fiscais (cancelamento, CC-e, etc).
    """

    queryset = NotaEvento.objects.all()
    serializer_class = None  # simples: podemos reutilizar um serializer direto

    def list(self, request, *args, **kwargs):
        nota_id = request.query_params.get("nota")
        qs = NotaEvento.objects.all()
        if nota_id:
            qs = qs.filter(nota_id=nota_id)

        data = [
            {
                "id": e.id,
                "nota_id": e.nota_id,
                "tipo": e.tipo,
                "descricao": e.descricao,
                "protocolo": e.protocolo,
                "criado_em": e.criado_em,
            }
            for e in qs.order_by("-criado_em")
        ]
        return Response(data)
