# financeiro/api/views/orcamento_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Financeiro.Rest.serializers import (
    OrcamentoResumoFiltroSerializer,
    OrcamentoSalvarSerializer,
    BaixaEmMassaTitulosFiltroSerializer,
    BaixaEmMassaExecutarSerializer,
)
from Financeiro.services import OrcamentoService
from Financeiro.baixas_em_massa_service import BaixasEmMassaService
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Entidades.models import Entidades


class OrcamentoViewSet(viewsets.ViewSet):
    def _service(self, request):
        db_alias = get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id") or request.headers.get("X-Empresa")
        filial_id = request.session.get("filial_id") or request.headers.get("X-Filial")

        if not empresa_id:
            raise ValueError("Empresa não informada.")

        return OrcamentoService(
            db_alias=db_alias,
            empresa_id=int(empresa_id),
            filial_id=int(filial_id) if filial_id else None,
        )

    @action(detail=False, methods=["get"], url_path="resumo")
    def resumo(self, request):
        serializer = OrcamentoResumoFiltroSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service = self._service(request)
        data = service.resumo_raiz(
            orcamento_id=serializer.validated_data["orcamento_id"],
            ano=serializer.validated_data["ano"],
            mes=serializer.validated_data["mes"],
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="salvar-previsto")
    def salvar_previsto(self, request):
        serializer = OrcamentoSalvarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self._service(request)
        item = service.salvar_previsto(
            orcamento_id=serializer.validated_data["orcamento_id"],
            centro_custo_id=serializer.validated_data["centro_custo_id"],
            ano=serializer.validated_data["ano"],
            mes=serializer.validated_data["mes"],
            valor=serializer.validated_data["valor"],
        )

        return Response(
            {
                "id": item.orci_id,
                "mensagem": "Previsto salvo com sucesso.",
            },
            status=status.HTTP_200_OK,
        )


class BaixasEmMassaViewSet(viewsets.ViewSet):
    def _contexto(self, request, slug=None):
        db_alias = get_licenca_db_config(request)
        slug = slug or get_licenca_slug() or request.session.get("slug")
        empresa_id = request.session.get("empresa_id") or request.headers.get("X-Empresa")
        filial_id = request.session.get("filial_id") or request.headers.get("X-Filial")
        usuario_id = request.session.get("usua_codi")
        if not usuario_id:
            try:
                usuario_id = getattr(getattr(request, "user", None), "usua_codi", None)
            except Exception:
                usuario_id = None

        if not empresa_id:
            raise ValueError("Empresa não informada.")

        return {
            "db_alias": db_alias,
            "slug": slug,
            "empresa_id": int(empresa_id),
            "filial_id": int(filial_id) if filial_id else None,
            "usuario_id": int(usuario_id) if usuario_id else None,
        }

    @action(detail=False, methods=["get"], url_path="titulos")
    def titulos(self, request, slug=None):
        filtro = BaixaEmMassaTitulosFiltroSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)

        ctx = self._contexto(request, slug)
        db_alias = ctx["db_alias"]
        empresa_id = ctx["empresa_id"]
        filial_id = ctx["filial_id"]

        tipo = filtro.validated_data["tipo"]
        data_ini = filtro.validated_data.get("data_ini")
        data_fim = filtro.validated_data.get("data_fim")
        termo = (filtro.validated_data.get("q") or "").strip()

        if tipo == "pagar":
            qs = Titulospagar.objects.using(db_alias).filter(
                titu_empr=empresa_id,
                titu_aber__in=["A", "P"],
            )
            if filial_id:
                qs = qs.filter(titu_fili=filial_id)
            if data_ini:
                qs = qs.filter(titu_venc__gte=data_ini)
            if data_fim:
                qs = qs.filter(titu_venc__lte=data_fim)
            if termo:
                qs = qs.filter(Q(titu_titu__icontains=termo) | Q(titu_nomi__icontains=termo))
            rows = list(
                qs.order_by("titu_venc", "titu_titu")
                .values(
                    "titu_titu",
                    "titu_seri",
                    "titu_parc",
                    "titu_emis",
                    "titu_venc",
                    "titu_valo",
                    "titu_aber",
                    "titu_forn",
                    "titu_form_reci",
                    "titu_cecu",
                )[:1000]
            )
            ent_ids = {r.get("titu_forn") for r in rows if r.get("titu_forn") is not None}
            ent_qs = Entidades.objects.using(db_alias).filter(enti_clie__in=ent_ids, enti_empr=empresa_id)
            nomes = {e["enti_clie"]: e["enti_nome"] for e in ent_qs.values("enti_clie", "enti_nome")}
            out = [
                {
                    "id": r["titu_titu"],
                    "titulo": r["titu_titu"],
                    "serie": r.get("titu_seri"),
                    "parcela": r.get("titu_parc"),
                    "emissao": r.get("titu_emis"),
                    "vencimento": r.get("titu_venc"),
                    "valor": float(r.get("titu_valo") or 0),
                    "status": r.get("titu_aber"),
                    "entidade_id": r.get("titu_forn"),
                    "entidade_nome": nomes.get(r.get("titu_forn"), ""),
                    "forma": r.get("titu_form_reci"),
                    "centro_custo": r.get("titu_cecu"),
                }
                for r in rows
            ]
            return Response({"results": out}, status=status.HTTP_200_OK)

        qs = Titulosreceber.objects.using(db_alias).filter(
            titu_empr=empresa_id,
            titu_aber__in=["A", "P"],
        )
        if filial_id:
            qs = qs.filter(titu_fili=filial_id)
        if data_ini:
            qs = qs.filter(titu_venc__gte=data_ini)
        if data_fim:
            qs = qs.filter(titu_venc__lte=data_fim)
        if termo:
            qs = qs.filter(Q(titu_titu__icontains=termo))

        rows = list(
            qs.order_by("titu_venc", "titu_titu")
            .values(
                "titu_titu",
                "titu_seri",
                "titu_parc",
                "titu_emis",
                "titu_venc",
                "titu_valo",
                "titu_aber",
                "titu_clie",
                "titu_form_reci",
                "titu_cecu",
            )[:1000]
        )
        ent_ids = {r.get("titu_clie") for r in rows if r.get("titu_clie") is not None}
        ent_qs = Entidades.objects.using(db_alias).filter(enti_clie__in=ent_ids, enti_empr=empresa_id)
        nomes = {e["enti_clie"]: e["enti_nome"] for e in ent_qs.values("enti_clie", "enti_nome")}
        out = [
            {
                "id": r["titu_titu"],
                "titulo": r["titu_titu"],
                "serie": r.get("titu_seri"),
                "parcela": r.get("titu_parc"),
                "emissao": r.get("titu_emis"),
                "vencimento": r.get("titu_venc"),
                "valor": float(r.get("titu_valo") or 0),
                "status": r.get("titu_aber"),
                "entidade_id": r.get("titu_clie"),
                "entidade_nome": nomes.get(r.get("titu_clie"), ""),
                "forma": r.get("titu_form_reci"),
                "centro_custo": r.get("titu_cecu"),
            }
            for r in rows
        ]
        return Response({"results": out}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="executar")
    def executar(self, request, slug=None):
        serializer = BaixaEmMassaExecutarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ctx = self._contexto(request, slug)
        tipo = serializer.validated_data["tipo"]
        ids = serializer.validated_data["ids"]

        usuario_id = serializer.validated_data.get("usuario_id") or ctx.get("usuario_id")

        service = BaixasEmMassaService()
        payload = {
            "slug": ctx.get("slug"),
            "data_baixa": serializer.validated_data["data_baixa"],
            "banco_id": serializer.validated_data["banco_id"],
            "centro_custo": serializer.validated_data.get("centro_custo"),
            "forma_pagamento": serializer.validated_data.get("forma_pagamento") or "B",
            "usuario_id": usuario_id,
            "valor_juros": serializer.validated_data.get("valor_juros") or 0,
            "valor_multa": serializer.validated_data.get("valor_multa") or 0,
            "valor_desconto": serializer.validated_data.get("valor_desconto") or 0,
            "historico": serializer.validated_data.get("historico"),
            "cheque": serializer.validated_data.get("cheque"),
        }
        try:
            if tipo == "receber":
                resultado = service.executar(ids_receber=ids, ids_pagar=[], **payload)
            else:
                resultado = service.executar(ids_pagar=ids, ids_receber=[], **payload)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(resultado, status=status.HTTP_200_OK)
