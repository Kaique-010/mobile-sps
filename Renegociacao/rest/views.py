from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
from ..models import Renegociado
from ..services.renegociacao_service import RenegociacaoService
from .serializers import RenegociadoSerializer
from contas_a_receber.models import Titulosreceber
from Entidades.models import Entidades


class RenegociadoViewSet(viewsets.ViewSet):
    """
    Endpoints REST para renegociações.
    """
    def list(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        empresa_id = int(request.query_params.get("empresa_id", 0) or 0)
        filial_id = int(request.query_params.get("filial_id", 0) or 0)
        qs = Renegociado.objects.using(banco).all()
        if empresa_id:
            qs = qs.filter(rene_empr=empresa_id)
        if filial_id:
            qs = qs.filter(rene_fili=filial_id)
        data = RenegociadoSerializer(qs, many=True).data
        return Response(data)

    def retrieve(self, request, pk=None, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        obj = Renegociado.objects.using(banco).filter(pk=pk).first()
        if not obj:
            return Response({"detail": "Não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(RenegociadoSerializer(obj).data)

    def create(self, request, slug=None):
        data = request.data or {}
        empresa_id = int(data.get("empresa_id"))
        filial_id = int(data.get("filial_id"))
        titulos_ids = data.get("titulos_ids") or []
        juros = data.get("juros", 0)
        multa = data.get("multa", 0)
        desconto = data.get("desconto", 0)
        parcelas = int(data.get("parcelas", 1))
        usuario_id = int(data.get("usuario_id", 0))
        vencimento_base = data.get("vencimento_base")
        regra_parc = data.get("regra_parc")
        try:
            reneg = RenegociacaoService.criar_renegociacao(
                slug=slug or get_licenca_slug(),
                empresa_id=empresa_id,
                filial_id=filial_id,
                titulos_ids=titulos_ids,
                juros=juros,
                multa=multa,
                desconto=desconto,
                parcelas=parcelas,
                usuario_id=usuario_id,
                vencimento_base=vencimento_base,
                regra_parc=regra_parc,
            )
            return Response(RenegociadoSerializer(reneg).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def quebrar(self, request, pk=None, slug=None):
        observacoes = request.data.get("observacoes", "")
        usuario_id = 0
        user = getattr(request, "user", None)
        if user and getattr(user, "id", None):
            try:
                usuario_id = int(user.id)
            except (TypeError, ValueError):
                usuario_id = 0
        try:
            RenegociacaoService.quebrar_acordo(
                slug=slug or get_licenca_slug(),
                renegociacao_id=int(pk),
                observacoes=observacoes,
                usuario_id=usuario_id,
            )
            return Response({"detail": "Acordo quebrado com sucesso."})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def titulos(self, request, pk=None, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        titulos = (Titulosreceber.objects
                   .using(banco)
                   .filter(titu_ctrl=int(pk))
                   .values("titu_titu", "titu_seri", "titu_parc", "titu_valo", "titu_venc", "titu_aber"))
        return Response(list(titulos))

    @action(detail=False, methods=["get"], url_path="titulos-por-cliente")
    def titulos_por_cliente(self, request, slug=None):
        empresa_id = int(request.query_params.get("empresa_id", 0) or 0)
        filial_id = int(request.query_params.get("filial_id", 0) or 0)
        cliente_id = int(request.query_params.get("cliente_id", 0) or 0)
        if not (empresa_id and filial_id and cliente_id):
            return Response({"detail": "Parâmetros empresa_id, filial_id e cliente_id são obrigatórios."}, status=400)
        qs = RenegociacaoService.listar_titulos_por_cliente(
            slug=slug or get_licenca_slug(),
            empresa_id=empresa_id,
            filial_id=filial_id,
            cliente_id=cliente_id,
        )
        data = [
            {
                "titu_titu": t.titu_titu,
                "titu_seri": t.titu_seri,
                "titu_parc": t.titu_parc,
                "titu_venc": t.titu_venc,
                "titu_valo": t.titu_valo,
                "titu_aber": t.titu_aber,
            }
            for t in qs
        ]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="autocomplete-clientes")
    def autocomplete_clientes(self, request, slug=None):
        banco = get_db_from_slug(slug or get_licenca_slug())
        q = (request.query_params.get("q") or "").strip()
        empresa_id = request.query_params.get("empresa_id")
        try:
            qs = Entidades.objects.using(banco)
            if empresa_id:
                qs = qs.filter(enti_empr=int(empresa_id))
            if q:
                if q.isdigit():
                    qs = qs.filter(enti_clie=int(q))
                else:
                    qs = qs.filter(enti_nome__icontains=q)
            qs = qs.values("enti_clie", "enti_nome").order_by("enti_nome")[:20]
            data = [{"id": r["enti_clie"], "label": f'{r["enti_nome"]} ({r["enti_clie"]})'} for r in qs]
            return Response(data)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
