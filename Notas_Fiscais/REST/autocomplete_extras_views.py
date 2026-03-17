import logging

from django.db.models import Q
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from core.utils import get_licenca_db_config
from Entidades.models import Entidades
from Produtos.models import Produtos, Tabelaprecos
from CFOP.models import CFOP
from CFOP.services.services import MotorFiscal, get_empresa_uf_origem
from CFOP.auxiliares.fiscal_padrao_resolver import FiscalPadraoResolver


logger = logging.getLogger(__name__)


def _get_empresa_filial(request):
    empresa = request.session.get("empresa_id") or request.headers.get("X-Empresa") or request.query_params.get("empresa")
    filial = request.session.get("filial_id") or request.headers.get("X-Filial") or request.query_params.get("filial")
    return empresa, filial


class ProdutoDetalheNotaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, codigo, slug=None):
        banco = get_licenca_db_config(request) or "default"
        empresa, filial = _get_empresa_filial(request)
        if not empresa:
            return Response({"detail": "Empresa é obrigatória"}, status=status.HTTP_400_BAD_REQUEST)

        p = (
            Produtos.objects.using(banco)
            .filter(prod_empr=empresa, prod_codi=codigo)
            .select_related("prod_unme")
            .first()
        )
        if not p:
            return Response({"detail": "Produto não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        destinatario_id = (request.query_params.get("destinatario") or "").strip()
        destinatario = None
        if destinatario_id:
            destinatario = (
                Entidades.objects.using(banco)
                .filter(enti_empr=empresa, enti_clie=destinatario_id)
                .first()
            )

        motor = MotorFiscal(banco=banco)
        ncm_obj = motor.obter_ncm(p)

        uf_origem = (get_empresa_uf_origem(empresa_id=empresa, filial_id=filial, banco=banco) or "").strip().upper()
        uf_destino = (getattr(destinatario, "enti_esta", None) or "").strip().upper() if destinatario else ""
        if not uf_destino:
            uf_destino = uf_origem

        tipo_entidade = (getattr(destinatario, "enti_tipo_enti", None) or "").strip().upper() if destinatario else ""

        fiscal_padrao, fonte_tributacao = FiscalPadraoResolver(banco=banco).resolver(
            produto=p,
            ncm=ncm_obj,
            cfop=None,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            tipo_entidade=tipo_entidade,
        )

        cfop_sugerido = None
        if ncm_obj:
            from CFOP.models import NcmFiscalPadrao as NcmFiscalPadraoModel

            fiscals_ncm = NcmFiscalPadraoModel.objects.using(banco).filter(ncm_id=ncm_obj.pk)
            best = None
            best_score = -1

            for fiscal in fiscals_ncm:
                fiscal_uf_origem = (getattr(fiscal, "uf_origem", None) or "").strip().upper()
                fiscal_uf_destino = (getattr(fiscal, "uf_destino", None) or "").strip().upper()
                fiscal_tipo_entidade = (getattr(fiscal, "tipo_entidade", None) or "").strip().upper()

                if fiscal_uf_origem and fiscal_uf_origem != uf_origem:
                    continue
                if fiscal_uf_destino and fiscal_uf_destino != uf_destino:
                    continue
                if fiscal_tipo_entidade:
                    if not tipo_entidade:
                        continue
                    if tipo_entidade == "AM":
                        pass
                    elif fiscal_tipo_entidade == "AM":
                        pass
                    elif fiscal_tipo_entidade != tipo_entidade:
                        continue

                cfop_raw = str(getattr(fiscal, "cfop", "") or "").strip()
                if not cfop_raw:
                    continue

                score = 0
                if fiscal_uf_origem:
                    score += 1
                if fiscal_uf_destino:
                    score += 1
                if fiscal_tipo_entidade:
                    score += 1
                if score > best_score:
                    best = fiscal
                    best_score = score

            if best and getattr(best, "cfop", None):
                cfop_code = str(getattr(best, "cfop") or "").split(" - ")[0].strip()
                cfop_code = "".join(ch for ch in cfop_code if ch.isdigit())[:4]
                if len(cfop_code) == 4:
                    exists = CFOP.objects.using(banco).filter(cfop_empr=empresa, cfop_codi=cfop_code).exists()
                    if not exists:
                        exists = CFOP.objects.using(banco).filter(cfop_codi=cfop_code).exists()
                    if exists:
                        cfop_sugerido = cfop_code

        data = {
            "prod_codi": p.prod_codi,
            "prod_nome": p.prod_nome,
            "prod_unid": getattr(getattr(p, "prod_unme", None), "unid_codi", "UN"),
            "prod_ncm": getattr(p, "prod_ncm", ""),
            "cfop_sugerido": cfop_sugerido,
            "cst_icms_sugerido": getattr(fiscal_padrao, "cst_icms", None) if fiscal_padrao else None,
            "cst_pis_sugerido": getattr(fiscal_padrao, "cst_pis", None) if fiscal_padrao else None,
            "cst_cofins_sugerido": getattr(fiscal_padrao, "cst_cofins", None) if fiscal_padrao else None,
            "cst_cbs_sugerido": getattr(fiscal_padrao, "cst_cbs", None) if fiscal_padrao else None,
            "cst_ibs_sugerido": getattr(fiscal_padrao, "cst_ibs", None) if fiscal_padrao else None,
            "fonte_tributacao": fonte_tributacao,
        }

        preco = (
            Tabelaprecos.objects.using(banco)
            .filter(tabe_empr=empresa, tabe_prod=p.prod_codi)
            .values_list("tabe_avis", flat=True)
            .first()
        )
        if preco:
            data["prod_preco_vista"] = float(preco)

        return Response(data)


class CfopAutocompleteNotaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(request) or "default"
        empresa, _filial = _get_empresa_filial(request)
        if not empresa:
            return Response({"detail": "Empresa é obrigatória"}, status=status.HTTP_400_BAD_REQUEST)

        q = (request.query_params.get("q") or "").strip()

        qs = CFOP.objects.using(banco).filter(cfop_empr=empresa)
        if q:
            qs = qs.filter(Q(cfop_codi__icontains=q) | Q(cfop_desc__iregex=q))

        qs = qs.only(
            "cfop_codi",
            "cfop_desc",
            "cfop_exig_icms",
            "cfop_exig_ipi",
            "cfop_exig_pis_cofins",
            "cfop_exig_cbs",
            "cfop_exig_ibs",
            "cfop_gera_st",
            "cfop_gera_difal",
        ).order_by("cfop_codi")[:20]

        data = [
            {
                "value": str(x.cfop_codi),
                "label": f"{x.cfop_codi} • {x.cfop_desc}",
                "cst_icms": ("000" if getattr(x, "cfop_exig_icms", False) else None),
                "cst_pis": ("01" if getattr(x, "cfop_exig_pis_cofins", False) else None),
                "cst_cofins": ("01" if getattr(x, "cfop_exig_pis_cofins", False) else None),
                "flags": {
                    "exig_icms": getattr(x, "cfop_exig_icms", False),
                    "exig_ipi": getattr(x, "cfop_exig_ipi", False),
                    "exig_pis_cofins": getattr(x, "cfop_exig_pis_cofins", False),
                    "exig_cbs": getattr(x, "cfop_exig_cbs", False),
                    "exig_ibs": getattr(x, "cfop_exig_ibs", False),
                    "gera_st": getattr(x, "cfop_gera_st", False),
                    "gera_difal": getattr(x, "cfop_gera_difal", False),
                },
            }
            for x in qs
        ]

        return Response(data)


class TransportadorasAutocompleteNotaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(request) or "default"
        empresa, _filial = _get_empresa_filial(request)
        if not empresa:
            return Response({"detail": "Empresa é obrigatória"}, status=status.HTTP_400_BAD_REQUEST)

        q = (request.query_params.get("q") or "").strip()

        qs = Entidades.objects.using(banco).filter(enti_empr=empresa)
        if q:
            qs = qs.filter(Q(enti_nome__iregex=q) | Q(enti_cnpj__icontains=q) | Q(enti_cpf__icontains=q))

        qs = qs.only("enti_clie", "enti_nome", "enti_cnpj", "enti_cpf").order_by("enti_nome")[:20]
        data = [
            {
                "value": e.enti_clie,
                "label": f"{e.enti_nome} • {(e.enti_cnpj or e.enti_cpf or '')}",
                "enti_clie": e.enti_clie,
                "enti_nome": e.enti_nome,
                "enti_cnpj": e.enti_cnpj,
                "enti_cpf": e.enti_cpf,
            }
            for e in qs
        ]

        return Response(data)

