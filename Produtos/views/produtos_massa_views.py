from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_licenca_db_config
from Produtos.servicos.produtos_em_massa import ProdutosEmMassaService
from Produtos.models import Produtos


class ProdutosMassaAPIView(APIView):
    permission_classes = [IsAuthenticated]

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

    @staticmethod
    def _fmt_fk(v):
        if v is None:
            return ""
        if isinstance(v, dict):
            codigo = v.get("codigo")
            nome = v.get("nome") or v.get("descricao")
            if codigo and nome:
                return f"{codigo} - {nome}"
            return str(codigo or nome or "")
        return str(v)

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._empresa_filial(request)
        if not empresa:
            return Response({"detail": "Empresa é obrigatória."}, status=status.HTTP_400_BAD_REQUEST)

        payload = ProdutosEmMassaService.listar_produtos(
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
        payload["filtros"] = ProdutosEmMassaService.listar_filtros(banco)
        return Response(payload)

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"detail": "Banco de dados não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa, filial = self._empresa_filial(request)
        if not empresa:
            return Response({"detail": "Empresa é obrigatória."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        acao = (data.get("acao") or "").strip().lower()
        valores = data.get("valores") or {}
        campos = data.get("campos") or []
        codigos = data.get("codigos") or []
        updates = data.get("updates") or []

        try:
            if acao == "preview":
                preview = ProdutosEmMassaService.preview_atualizacao(
                    banco=banco,
                    empresa=empresa,
                    valores=valores,
                    campos=campos,
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
                if updates:
                    label = {
                        "prod_nome": "Nome",
                        "prod_unme": "Unidade",
                        "prod_ncm": "NCM",
                        "prod_gtin": "GTIN",
                        "prod_loca": "Local",
                        "prod_orig_merc": "Origem",
                        "prod_marc": "Marca",
                        "prod_fami": "Família",
                        "prod_grup": "Grupo",
                        "prod_sugr": "Subgrupo",
                        "prod_codi_nume": "Código Nume",
                    }

                    codigos = [str(u.get("prod_codi")) for u in updates if isinstance(u, dict) and u.get("prod_codi")]
                    produtos = list(
                        Produtos.objects.using(banco)
                        .select_related("prod_unme", "prod_marc", "prod_fami", "prod_grup", "prod_sugr")
                        .filter(prod_empr=str(empresa), prod_codi__in=codigos)
                    )
                    prod_map = {p.prod_codi: p for p in produtos}

                    linhas = []
                    for upd in updates:
                        if not isinstance(upd, dict):
                            continue
                        prod_codi = str(upd.get("prod_codi") or "")
                        valores_item = upd.get("valores") or {}
                        if not prod_codi or not isinstance(valores_item, dict):
                            continue
                        prod = prod_map.get(prod_codi)
                        for campo, novo in valores_item.items():
                            if campo not in ProdutosEmMassaService.CAMPOS_SUPORTADOS:
                                continue
                            antes = ProdutosEmMassaService._display_field(prod, campo) if prod else None
                            depois = novo
                            if campo in ProdutosEmMassaService.CAMPOS_FK:
                                if novo in (None, ""):
                                    depois = None
                                else:
                                    model_fk = ProdutosEmMassaService.CAMPOS_FK[campo]
                                    fk_obj = model_fk.objects.using(banco).filter(pk=novo).first()
                                    if fk_obj:
                                        if campo == "prod_unme":
                                            depois = {"codigo": getattr(fk_obj, "unid_codi", None), "descricao": getattr(fk_obj, "unid_desc", None)}
                                        elif campo == "prod_marc":
                                            depois = {"codigo": getattr(fk_obj, "codigo", None), "nome": getattr(fk_obj, "nome", None)}
                                        else:
                                            depois = {"codigo": getattr(fk_obj, "codigo", None), "descricao": getattr(fk_obj, "descricao", None)}
                                    else:
                                        depois = novo
                            linhas.append(
                                {
                                    "prod_codi": prod_codi,
                                    "campo": label.get(campo, campo),
                                    "antes": self._fmt_fk(antes),
                                    "depois": self._fmt_fk(depois),
                                }
                            )

                    now = timezone.now().strftime("%Y%m%d_%H%M%S")
                    nome_base = f"atualizacao_produtos_{now}"

                    if formato == "csv":
                        import csv
                        import io

                        buff = io.StringIO()
                        writer = csv.writer(buff, delimiter=";")
                        writer.writerow(["Produto", "Campo", "Antes", "Depois"])
                        for l in linhas:
                            writer.writerow([l["prod_codi"], l["campo"], l["antes"], l["depois"]])
                        resp = HttpResponse(buff.getvalue(), content_type="text/csv; charset=utf-8")
                        resp["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
                        return resp

                    from openpyxl import Workbook

                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Atualização"
                    ws.append(["Produto", "Campo", "Antes", "Depois"])
                    for l in linhas:
                        ws.append([l["prod_codi"], l["campo"], l["antes"], l["depois"]])

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

                preview = ProdutosEmMassaService.preview_atualizacao(
                    banco=banco,
                    empresa=empresa,
                    valores=valores,
                    campos=campos,
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
                nome_base = f"atualizacao_produtos_{now}"
                campos_export = preview.get("campos") or []

                if formato == "csv":
                    import csv
                    import io

                    buff = io.StringIO()
                    writer = csv.writer(buff, delimiter=";")
                    header = ["Produto", "Nome", "Marca", "Família", "Grupo", "Subgrupo"]
                    for campo in campos_export:
                        header += [f"{campo} Antes", f"{campo} Depois"]
                    writer.writerow(header)

                    for r in preview.get("results") or []:
                        row = [r.get("prod_codi"), r.get("prod_nome"), r.get("marca"), r.get("familia"), r.get("grupo"), r.get("subgrupo")]
                        for campo in campos_export:
                            a = ((r.get("campos") or {}).get(campo) or {}).get("antes")
                            d = ((r.get("campos") or {}).get(campo) or {}).get("depois")
                            row += [self._fmt_fk(a), self._fmt_fk(d)]
                        writer.writerow(row)
                    resp = HttpResponse(buff.getvalue(), content_type="text/csv; charset=utf-8")
                    resp["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
                    return resp

                from openpyxl import Workbook

                wb = Workbook()
                ws = wb.active
                ws.title = "Atualização"
                header = ["Produto", "Nome", "Marca", "Família", "Grupo", "Subgrupo"]
                for campo in campos_export:
                    header += [f"{campo} Antes", f"{campo} Depois"]
                ws.append(header)

                for r in preview.get("results") or []:
                    row = [r.get("prod_codi"), r.get("prod_nome"), r.get("marca"), r.get("familia"), r.get("grupo"), r.get("subgrupo")]
                    for campo in campos_export:
                        a = ((r.get("campos") or {}).get(campo) or {}).get("antes")
                        d = ((r.get("campos") or {}).get(campo) or {}).get("depois")
                        row += [self._fmt_fk(a), self._fmt_fk(d)]
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

            if updates:
                with transaction.atomic(using=banco):
                    resultado = ProdutosEmMassaService.aplicar_atualizacao_linhas(
                        banco=banco,
                        empresa=empresa,
                        updates=updates,
                    )
                return Response({"ok": True, "resultado": resultado})

            with transaction.atomic(using=banco):
                resultado = ProdutosEmMassaService.aplicar_atualizacao(
                    banco=banco,
                    empresa=empresa,
                    valores=valores,
                    campos=campos,
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
