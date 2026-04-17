from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_licenca_db_config
from Produtos.servicos.preco_massa_service import PrecoMassaService


class PrecoMassaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _bool(v, default=False):
        if v is None:
            return default
        return str(v).strip().lower() in {"1", "true", "sim", "yes", "on"}

    def _empresa_filial(self, request):
        empresa = (
            request.headers.get("X-Empresa")
            or request.query_params.get("empresa")
            or request.data.get("empresa")
            or request.session.get("empresa_id")
        )
        filial = (
            request.headers.get("X-Filial")
            or request.query_params.get("filial")
            or request.data.get("filial")
            or request.session.get("filial_id")
        )
        return empresa, filial

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._empresa_filial(request)
        if not empresa or not filial:
            return Response({"detail": "Empresa e filial são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        payload = PrecoMassaService.listar_produtos(
            banco=banco,
            empresa=empresa,
            filial=filial,
            page=request.query_params.get("page", 1),
            page_size=request.query_params.get("page_size", 30),
            marca=request.query_params.get("marca"),
            familia=request.query_params.get("familia"),
            grupo=request.query_params.get("grupo"),
            subgrupo=request.query_params.get("subgrupo"),
            busca=request.query_params.get("busca"),
        )
        payload["filtros"] = PrecoMassaService.listar_filtros(banco)
        return Response(payload)

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._empresa_filial(request)
        if not empresa or not filial:
            return Response({"detail": "Empresa e filial são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        acao = (data.get("acao") or "").strip().lower()
        tipo = (data.get("tipo") or "percentual").strip().lower()
        percentual = data.get("percentual")
        valores = data.get("valores") or {}
        campos = data.get("campos") or []
        codigos = data.get("codigos") or []

        aplicar_normal = self._bool(data.get("aplicar_normal", True), True)
        aplicar_promocional = self._bool(data.get("aplicar_promocional", True), True)

        if not aplicar_normal and not aplicar_promocional:
            return Response(
                {"detail": "Selecione pelo menos um alvo: preços normais ou promocionais."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if acao == "preview":
                preview = PrecoMassaService.preview_reajuste(
                    banco=banco,
                    empresa=empresa,
                    filial=filial,
                    tipo=tipo,
                    percentual=percentual,
                    valores=valores,
                    campos=campos,
                    aplicar_normal=aplicar_normal,
                    aplicar_promocional=aplicar_promocional,
                    codigos=codigos,
                    page=data.get("page"),
                    page_size=data.get("page_size"),
                    limit=data.get("limit", 50),
                    marca=data.get("marca"),
                    familia=data.get("familia"),
                    grupo=data.get("grupo"),
                    subgrupo=data.get("subgrupo"),
                    busca=data.get("busca"),
                )
                return Response({"ok": True, "preview": preview})

            if acao == "export":
                formato = (data.get("formato") or "xlsx").strip().lower()
                preview = PrecoMassaService.preview_reajuste(
                    banco=banco,
                    empresa=empresa,
                    filial=filial,
                    tipo=tipo,
                    percentual=percentual,
                    valores=valores,
                    campos=campos,
                    aplicar_normal=aplicar_normal,
                    aplicar_promocional=aplicar_promocional,
                    codigos=codigos,
                    limit=data.get("limit", 5000),
                    marca=data.get("marca"),
                    familia=data.get("familia"),
                    grupo=data.get("grupo"),
                    subgrupo=data.get("subgrupo"),
                    busca=data.get("busca"),
                )
                if int(preview.get("count") or 0) > int(data.get("limit", 5000) or 5000):
                    return Response(
                        {"detail": "Exportação excede o limite. Refine os filtros ou selecione produtos."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                now = timezone.now().strftime("%Y%m%d_%H%M%S")
                nome_base = f"reajuste_precos_{now}"

                if formato == "csv":
                    import csv
                    import io

                    buff = io.StringIO()
                    writer = csv.writer(buff, delimiter=";")
                    header = ["Produto", "Descrição", "Marca", "Família", "Grupo", "Subgrupo"]
                    for campo in preview.get("campos") or []:
                        if aplicar_normal:
                            header += [f"Normal {campo} Antes", f"Normal {campo} Depois"]
                        if aplicar_promocional:
                            header += [f"Promo {campo} Antes", f"Promo {campo} Depois"]
                    writer.writerow(header)
                    for r in preview.get("results") or []:
                        row = [r.get("prod_codi"), r.get("prod_nome"), r.get("marca"), r.get("familia"), r.get("grupo"), r.get("subgrupo")]
                        for campo in preview.get("campos") or []:
                            if aplicar_normal:
                                a = ((r.get("normal") or {}).get(campo) or {}).get("antes", 0)
                                d = ((r.get("normal") or {}).get(campo) or {}).get("depois", 0)
                                row += [a, d]
                            if aplicar_promocional:
                                a = ((r.get("promocional") or {}).get(campo) or {}).get("antes", 0)
                                d = ((r.get("promocional") or {}).get(campo) or {}).get("depois", 0)
                                row += [a, d]
                        writer.writerow(row)
                    resp = HttpResponse(buff.getvalue(), content_type="text/csv; charset=utf-8")
                    resp["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
                    return resp

                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                ws.title = "Reajuste"
                header = ["Produto", "Descrição", "Marca", "Família", "Grupo", "Subgrupo"]
                for campo in preview.get("campos") or []:
                    if aplicar_normal:
                        header += [f"Normal {campo} Antes", f"Normal {campo} Depois"]
                    if aplicar_promocional:
                        header += [f"Promo {campo} Antes", f"Promo {campo} Depois"]
                ws.append(header)
                for r in preview.get("results") or []:
                    row = [r.get("prod_codi"), r.get("prod_nome"), r.get("marca"), r.get("familia"), r.get("grupo"), r.get("subgrupo")]
                    for campo in preview.get("campos") or []:
                        if aplicar_normal:
                            a = ((r.get("normal") or {}).get(campo) or {}).get("antes", 0)
                            d = ((r.get("normal") or {}).get(campo) or {}).get("depois", 0)
                            row += [a, d]
                        if aplicar_promocional:
                            a = ((r.get("promocional") or {}).get(campo) or {}).get("antes", 0)
                            d = ((r.get("promocional") or {}).get(campo) or {}).get("depois", 0)
                            row += [a, d]
                    ws.append(row)

                import io

                out = io.BytesIO()
                wb.save(out)
                out.seek(0)
                resp = HttpResponse(
                    out.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                resp["Content-Disposition"] = f'attachment; filename="{nome_base}.xlsx"'
                return resp

            with transaction.atomic(using=banco):
                resultado = PrecoMassaService.aplicar_reajuste(
                    banco=banco,
                    empresa=empresa,
                    filial=filial,
                    tipo=tipo,
                    percentual=percentual,
                    valores=valores,
                    campos=campos,
                    aplicar_normal=aplicar_normal,
                    aplicar_promocional=aplicar_promocional,
                    codigos=codigos,
                    marca=data.get("marca"),
                    familia=data.get("familia"),
                    grupo=data.get("grupo"),
                    subgrupo=data.get("subgrupo"),
                    busca=data.get("busca"),
                )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"ok": True, "resultado": resultado})
