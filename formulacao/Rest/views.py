from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
from Produtos.models import Lote, Produtos, Tabelaprecos

from ..models import FormulaProduto, FormulaItem, FormulaSaida, OrdemProducao
from ..services.formulacao_service import ProducaoService
from .serializers import (
    FormulaProdutoSerializer,
    FormulaItemSerializer,
    FormulaSaidaSerializer,
    OrdemProducaoSerializer,
)


class FormulaViewSet(viewsets.ViewSet):
    def list(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        empresa_id = request.query_params.get("empresa_id")
        filial_id = request.query_params.get("filial_id")
        prod = (request.query_params.get("produto") or "").strip()
        vers = request.query_params.get("versao")
        ativo = request.query_params.get("ativo")

        qs = FormulaProduto.objects.using(banco).select_related("form_prod")
        if empresa_id:
            qs = qs.filter(form_empr=int(empresa_id))
        if filial_id:
            qs = qs.filter(form_fili=int(filial_id))
        if prod:
            qs = qs.filter(form_prod__prod_codi=str(prod))
        if vers:
            qs = qs.filter(form_vers=int(vers))
        if ativo is not None and str(ativo).strip() != "":
            qs = qs.filter(form_ativ=str(ativo).lower() in ("1", "true", "t", "sim", "s"))

        data = FormulaProdutoSerializer(qs.order_by("-form_vers"), many=True).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="itens")
    def itens(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        empresa_id = request.query_params.get("empresa_id")
        filial_id = request.query_params.get("filial_id")
        prod = (request.query_params.get("produto") or "").strip()
        vers = request.query_params.get("versao")

        if not (empresa_id and filial_id and prod and vers):
            return Response(
                {"detail": "empresa_id, filial_id, produto e versao são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        formula = FormulaProduto.objects.using(banco).get(
            form_empr=int(empresa_id),
            form_fili=int(filial_id),
            form_prod__prod_codi=str(prod),
            form_vers=int(vers),
            form_ativ=True,
        )
        qs = (
            FormulaItem.objects.using(banco)
            .filter(form_form=formula)
            .select_related("form_insu")
            .order_by("form_item")
        )
        return Response(FormulaItemSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="saidas")
    def saidas(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        empresa_id = request.query_params.get("empresa_id")
        filial_id = request.query_params.get("filial_id")
        prod = (request.query_params.get("produto") or "").strip()
        vers = request.query_params.get("versao")

        if not (empresa_id and filial_id and prod and vers):
            return Response(
                {"detail": "empresa_id, filial_id, produto e versao são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        formula = FormulaProduto.objects.using(banco).get(
            form_empr=int(empresa_id),
            form_fili=int(filial_id),
            form_prod__prod_codi=str(prod),
            form_vers=int(vers),
            form_ativ=True,
        )
        qs = (
            FormulaSaida.objects.using(banco)
            .filter(said_form=formula)
            .select_related("said_prod")
            .order_by("-said_principal", "said_prod__prod_nome")
        )
        return Response(FormulaSaidaSerializer(qs, many=True).data)


class OrdemProducaoViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        empresa_id = request.query_params.get("empresa_id")
        filial_id = request.query_params.get("filial_id")
        status_op = request.query_params.get("status")

        qs = OrdemProducao.objects.using(banco).select_related("op_prod")
        if empresa_id:
            qs = qs.filter(op_empr=int(empresa_id))
        if filial_id:
            qs = qs.filter(op_fili=int(filial_id))
        if status_op:
            qs = qs.filter(op_status=str(status_op).strip().upper()[:1])

        data = OrdemProducaoSerializer(qs.order_by("-op_nume"), many=True).data
        return Response(data)

    def create(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        payload = request.data or {}

        empresa_id = int(payload.get("empresa_id") or 0)
        filial_id = int(payload.get("filial_id") or 0)
        prod_codi = str(payload.get("produto") or "").strip()
        vers = int(payload.get("versao") or 0)
        quan = Decimal(str(payload.get("quantidade") or "0"))
        lote = (payload.get("lote") or "").strip() or None
        data_str = (payload.get("data") or "").strip()

        if not (empresa_id and filial_id and prod_codi and vers and quan):
            return Response(
                {"detail": "empresa_id, filial_id, produto, versao e quantidade são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_op = date.fromisoformat(data_str) if data_str else timezone.now().date()
        except Exception:
            data_op = timezone.now().date()

        prod = (
            Produtos.objects.using(banco)
            .filter(prod_empr=str(empresa_id), prod_codi=str(prod_codi))
            .first()
        )
        if not prod:
            prod = Produtos.objects.using(banco).filter(prod_codi=str(prod_codi)).first()
        if not prod:
            return Response({"detail": "Produto não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic(using=banco):
            max_nume = (
                OrdemProducao.objects.using(banco)
                .filter(op_empr=empresa_id, op_fili=filial_id)
                .aggregate(m=Max("op_nume"))
                .get("m")
                or 0
            )
            op_nume = int(max_nume) + 1
            op = OrdemProducao.objects.using(banco).create(
                op_empr=empresa_id,
                op_fili=filial_id,
                op_nume=op_nume,
                op_data=data_op,
                op_prod=prod,
                op_vers=vers,
                op_quan=quan,
                op_status="A",
                op_lote=lote,
            )

        return Response(OrdemProducaoSerializer(op).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="executar")
    def executar(self, request, slug=None):
        banco_slug = slug or get_licenca_slug()
        banco = get_db_from_slug(banco_slug)
        payload = request.data or {}

        empresa_id = int(payload.get("empresa_id") or 0)
        filial_id = int(payload.get("filial_id") or 0)
        op_nume = int(payload.get("op_nume") or 0)
        usuario_id = int(payload.get("usuario_id") or getattr(getattr(request, "user", None), "id", 1) or 1)

        if not (empresa_id and filial_id and op_nume):
            return Response(
                {"detail": "empresa_id, filial_id e op_nume são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        op = (
            OrdemProducao.objects.using(banco)
            .select_related("op_prod")
            .filter(op_empr=empresa_id, op_fili=filial_id, op_nume=op_nume)
            .first()
        )
        if not op:
            return Response({"detail": "Ordem não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            def parse_date(value):
                if not value:
                    return None
                if hasattr(value, "year"):
                    return value
                try:
                    return date.fromisoformat(str(value))
                except Exception:
                    return None

            preco_vista = request.data.get("preco_vista")
            preco_prazo = request.data.get("preco_prazo")
            if preco_vista is not None or preco_prazo is not None:
                chave = {
                    "tabe_empr": empresa_id,
                    "tabe_fili": filial_id,
                    "tabe_prod": str(op.op_prod.prod_codi),
                }
                update_fields = {}
                if preco_vista is not None and str(preco_vista).strip() != "":
                    update_fields["tabe_avis"] = str(preco_vista)
                if preco_prazo is not None and str(preco_prazo).strip() != "":
                    update_fields["tabe_apra"] = str(preco_prazo)
                if update_fields:
                    qs = Tabelaprecos.objects.using(banco).filter(**chave)
                    if qs.exists():
                        qs.update(**update_fields)
                    else:
                        Tabelaprecos.objects.using(banco).create(**{**chave, **update_fields})

            lote_data_fabr = parse_date(payload.get("lote_data_fabr") or payload.get("data_fabricacao"))
            lote_data_vali = parse_date(payload.get("lote_data_venc") or payload.get("lote_data_vali") or payload.get("data_validade"))

            produto_codigo = str(op.op_prod.prod_codi)
            raw_lote = (op.op_lote or "").strip()
            parts = [p.strip() for p in raw_lote.replace("_", "-").split("-") if p.strip()]
            candidato = next((p for p in reversed([raw_lote] + parts) if p.isdigit()), None)
            lote_numero = int(candidato) if candidato else None
            should_sync_op_lote = (not raw_lote) or raw_lote.isdigit() or (
                "-" in raw_lote and raw_lote.replace("_", "-").split("-")[-1].isdigit()
            )

            if lote_numero is None:
                max_lote = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=empresa_id, lote_prod=produto_codigo)
                    .aggregate(m=Max("lote_lote"))
                    .get("m")
                    or 0
                )
                lote_numero = int(max_lote) + 1

            existe_lote = Lote.objects.using(banco).filter(
                lote_empr=empresa_id,
                lote_prod=produto_codigo,
                lote_lote=lote_numero,
            )
            if not existe_lote.exists():
                max_lote = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=empresa_id, lote_prod=produto_codigo)
                    .aggregate(m=Max("lote_lote"))
                    .get("m")
                    or 0
                )
                if int(lote_numero) <= int(max_lote):
                    lote_numero = int(max_lote) + 1

                novo_op_lote = str(int(lote_numero))
                if should_sync_op_lote and raw_lote != novo_op_lote:
                    OrdemProducao.objects.using(banco).filter(
                        op_empr=empresa_id, op_fili=filial_id, op_nume=op.op_nume
                    ).update(op_lote=novo_op_lote)
                    op.op_lote = novo_op_lote

                lote = Lote(
                    lote_empr=empresa_id,
                    lote_prod=produto_codigo,
                    lote_lote=int(lote_numero),
                    lote_unit=Decimal("0.00"),
                    lote_sald=Decimal(str(op.op_quan or 0)).quantize(Decimal("0.01")),
                    lote_data_fabr=lote_data_fabr,
                    lote_data_vali=lote_data_vali,
                    lote_ativ=True,
                )
                lote.save(using=banco)
            else:
                novo_op_lote = str(int(lote_numero))
                if should_sync_op_lote and raw_lote != novo_op_lote:
                    OrdemProducao.objects.using(banco).filter(
                        op_empr=empresa_id, op_fili=filial_id, op_nume=op.op_nume
                    ).update(op_lote=novo_op_lote)
                    op.op_lote = novo_op_lote

                update = {
                    "lote_ativ": True,
                    "lote_sald": Decimal(str(op.op_quan or 0)).quantize(Decimal("0.01")),
                }
                if lote_data_fabr:
                    update["lote_data_fabr"] = lote_data_fabr
                if lote_data_vali:
                    update["lote_data_vali"] = lote_data_vali
                if update:
                    existe_lote.update(**update)

            ProducaoService.executar(op, db_slug=banco_slug, usuario_id=usuario_id)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        op_refresh = (
            OrdemProducao.objects.using(banco)
            .select_related("op_prod")
            .filter(op_empr=empresa_id, op_fili=filial_id, op_nume=op_nume)
            .first()
        )
        return Response(OrdemProducaoSerializer(op_refresh).data, status=status.HTTP_200_OK)
