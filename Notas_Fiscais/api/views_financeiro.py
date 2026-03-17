from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction, connections

from ..models import Nota, NotaItem
from contas_a_receber.models import FORMA_RECEBIMENTO, Titulosreceber, Baretitulos
from core.registry import get_licenca_db_config


def _parse_decimal(value, default="0"):
    try:
        if value is None or value == "":
            return Decimal(str(default))
        return Decimal(str(value))
    except Exception:
        return Decimal(str(default))


def _parse_date(value):
    if not value:
        return datetime.now().date()
    if hasattr(value, "year"):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date()


def _calcular_total_nota(nota):
    itens = list(getattr(nota, "itens", []).all())
    total_produtos = sum(((it.total or Decimal("0"))) for it in itens)
    total_tributos = Decimal("0")
    for it in itens:
        imp = getattr(it, "impostos", None)
        if not imp:
            continue
        total_tributos += (
            (imp.icms_valor or Decimal("0"))
            + (imp.icms_st_valor or Decimal("0"))
            + (imp.ipi_valor or Decimal("0"))
            + (imp.pis_valor or Decimal("0"))
            + (imp.cofins_valor or Decimal("0"))
            + (imp.cbs_valor or Decimal("0"))
            + (imp.ibs_valor or Decimal("0"))
            + (imp.fcp_valor or Decimal("0"))
        )
    return (total_produtos + total_tributos).quantize(Decimal("0.01"))


def _parcelas_existem(banco, empresa, filial, nota_numero):
    with connections[banco].cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM parcelasnotafiscal WHERE parc_empr = %s AND parc_fili = %s AND parc_nota = %s LIMIT 1",
            [int(empresa), int(filial), int(nota_numero)],
        )
        return cursor.fetchone() is not None


def _insert_parcelas_notafiscal(banco, rows):
    if not rows:
        return
    with connections[banco].cursor() as cursor:
        desc = connections[banco].introspection.get_table_description(cursor, "parcelasnotafiscal")
        cols = {c.name for c in desc}
        ordered = [
            "parc_empr",
            "parc_fili",
            "parc_nota",
            "parc_parc",
            "parc_clie",
            "parc_forn",
            "parc_emis",
            "parc_venc",
            "parc_valo",
            "parc_port",
            "parc_situ",
            "parc_form",
            "parc_avis",
            "parc_vend",
            "parc_cecu",
        ]
        insert_cols = [c for c in ordered if c in cols]
        if not insert_cols:
            raise ValueError("Tabela parcelasnotafiscal não possui colunas esperadas para inserção.")
        placeholders = ", ".join(["%s"] * len(insert_cols))
        sql = f"INSERT INTO parcelasnotafiscal ({', '.join(insert_cols)}) VALUES ({placeholders})"
        params = []
        for r in rows:
            params.append([r.get(c) for c in insert_cols])
        cursor.executemany(sql, params)


class GerarTitulosNotaView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request) or "default"
        data = request.data or {}
        nota_numero = data.get("nota_numero")
        entrada = _parse_decimal(data.get("entrada", 0), default="0")
        forma_pagamento = (data.get("forma_pagamento") or "").strip()
        parcelas = int(data.get("parcelas") or 1)
        data_base = _parse_date(data.get("data_base"))

        if not nota_numero:
            return Response({"detail": "nota_numero é obrigatório."}, status=400)
        if parcelas < 1:
            return Response({"detail": "parcelas deve ser >= 1."}, status=400)
        if forma_pagamento and forma_pagamento not in dict(FORMA_RECEBIMENTO).keys():
            return Response({"detail": "Forma de recebimento inválida."}, status=400)

        try:
            nota = (
                Nota.objects.using(banco)
                .prefetch_related("itens__impostos")
                .get(pk=int(nota_numero))
            )
        except Nota.DoesNotExist:
            return Response({"detail": "Nota não encontrada."}, status=404)

        total_nota = _calcular_total_nota(nota)
        if entrada < 0:
            return Response({"detail": "entrada não pode ser negativa."}, status=400)
        if entrada > total_nota:
            return Response({"detail": "entrada não pode ser maior que o total."}, status=400)

        cliente_id = int(getattr(nota, "destinatario_id", 0) or 0)
        if cliente_id <= 0:
            return Response({"detail": "Destinatário inválido."}, status=409)

        titulos_existem = Titulosreceber.objects.using(banco).filter(
            titu_empr=int(nota.empresa),
            titu_fili=int(nota.filial),
            titu_seri="NFE",
            titu_titu=str(nota.numero),
            titu_clie=cliente_id,
        ).exists()
        if titulos_existem or _parcelas_existem(banco, nota.empresa, nota.filial, nota.numero):
            return Response(
                {"detail": "Já existe título/parcela para esta nota. Use Consultar ou Remover."},
                status=409,
            )

        total_restante = (total_nota - entrada).quantize(Decimal("0.01"))
        valor_parcela = (total_restante / Decimal(str(parcelas))).quantize(Decimal("0.01"))
        diferenca = total_restante - (valor_parcela * Decimal(str(parcelas)))

        rows = []
        parc_num = 1
        if entrada > 0:
            rows.append(
                {
                    "parc_empr": int(nota.empresa),
                    "parc_fili": int(nota.filial),
                    "parc_nota": int(nota.numero),
                    "parc_parc": int(parc_num),
                    "parc_clie": cliente_id,
                    "parc_forn": cliente_id,
                    "parc_emis": datetime.now().date(),
                    "parc_venc": data_base,
                    "parc_valo": entrada,
                    "parc_port": 0,
                    "parc_situ": 0,
                    "parc_form": forma_pagamento or "",
                    "parc_avis": False,
                    "parc_vend": 0,
                    "parc_cecu": 0,
                }
            )
            parc_num += 1

        for i in range(parcelas):
            vencimento = data_base + timedelta(days=30 * (i if entrada == 0 else i + 1))
            valor_atual = valor_parcela
            if i == 0:
                valor_atual += diferenca
            rows.append(
                {
                    "parc_empr": int(nota.empresa),
                    "parc_fili": int(nota.filial),
                    "parc_nota": int(nota.numero),
                    "parc_parc": int(parc_num),
                    "parc_clie": cliente_id,
                    "parc_forn": cliente_id,
                    "parc_emis": datetime.now().date(),
                    "parc_venc": vencimento,
                    "parc_valo": valor_atual,
                    "parc_port": 0,
                    "parc_situ": 0,
                    "parc_form": forma_pagamento or "",
                    "parc_avis": False,
                    "parc_vend": 0,
                    "parc_cecu": 0,
                }
            )
            parc_num += 1

        try:
            with transaction.atomic(using=banco):
                _insert_parcelas_notafiscal(banco, rows)
        except Exception as e:
            return Response({"detail": f"Erro ao gerar parcelas: {e}"}, status=409)

        return Response(
            {
                "detail": f"{len(rows)} parcela(s) gerada(s) com sucesso.",
                "total_nota": float(total_nota),
                "total_parcelado": float(total_restante),
            },
            status=201,
        )


class RemoverTitulosNotaView(APIView):
    def post(self, request, nota_numero, slug=None):
        banco = get_licenca_db_config(self.request) or "default"
        if not nota_numero:
            return Response({"detail": "nota_numero é obrigatório."}, status=400)

        try:
            nota = Nota.objects.using(banco).get(pk=int(nota_numero))
        except Nota.DoesNotExist:
            return Response({"detail": "Nota não encontrada."}, status=404)

        cliente_id = int(getattr(nota, "destinatario_id", 0) or 0)
        nota_numero = int(nota.numero)

        try:
            with transaction.atomic(using=banco):
                Baretitulos.objects.using(banco).filter(
                    bare_empr=int(nota.empresa),
                    bare_fili=int(nota.filial),
                    bare_clie=cliente_id,
                    bare_titu=str(nota_numero),
                    bare_seri="NFE",
                ).delete()

                titulos_count = Titulosreceber.objects.using(banco).filter(
                    titu_empr=int(nota.empresa),
                    titu_fili=int(nota.filial),
                    titu_seri="NFE",
                    titu_titu=str(nota_numero),
                    titu_clie=cliente_id,
                ).delete()[0]

                with connections[banco].cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM parcelasnotafiscal WHERE parc_empr = %s AND parc_fili = %s AND parc_nota = %s",
                        [int(nota.empresa), int(nota.filial), int(nota_numero)],
                    )
        except Exception as e:
            return Response({"detail": f"Erro ao remover financeiro: {e}"}, status=409)

        return Response({"detail": f"{titulos_count} título(s) removido(s) com sucesso."}, status=200)


class ConsultarTitulosNotaView(APIView):
    def get(self, request, nota_numero, slug=None):
        banco = get_licenca_db_config(self.request) or "default"
        if not nota_numero:
            return Response({"detail": "nota_numero é obrigatório."}, status=400)

        try:
            nota = Nota.objects.using(banco).get(pk=int(nota_numero))
        except Nota.DoesNotExist:
            return Response({"detail": "Nota não encontrada."}, status=404)

        cliente_id = int(getattr(nota, "destinatario_id", 0) or 0)
        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=int(nota.empresa),
            titu_fili=int(nota.filial),
            titu_seri="NFE",
            titu_titu=str(nota.numero),
            titu_clie=cliente_id,
        ).order_by("titu_parc")

        total = titulos.aggregate(total=Sum("titu_valo"), quantidade=Count("*"))
        dados = [
            {
                "parcela": t.titu_parc,
                "valor": float(t.titu_valo or 0),
                "vencimento": (t.titu_venc.isoformat() if t.titu_venc else ""),
                "forma_pagamento": t.titu_form_reci,
                "status": t.titu_situ,
                "aberto": t.titu_aber,
            }
            for t in titulos
        ]
        return Response(
            {
                "titulos": dados,
                "total": float(total["total"] or 0),
                "quantidade_parcelas": int(total["quantidade"] or 0),
            }
        )


class AtualizarTituloNotaView(APIView):
    def post(self, request, nota_numero, slug=None):
        banco = get_licenca_db_config(self.request) or "default"
        if not nota_numero:
            return Response({"detail": "nota_numero é obrigatório."}, status=400)

        data = request.data or {}
        parcela = data.get("parcela")
        valor = data.get("valor")
        vencimento = data.get("vencimento")
        forma_pagamento = (data.get("forma_pagamento") or "").strip()

        if not parcela:
            return Response({"detail": "parcela é obrigatória."}, status=400)
        if valor is None or valor == "":
            return Response({"detail": "valor é obrigatório."}, status=400)
        if not vencimento:
            return Response({"detail": "vencimento é obrigatório."}, status=400)
        if not forma_pagamento:
            return Response({"detail": "forma_pagamento é obrigatória."}, status=400)
        if forma_pagamento not in dict(FORMA_RECEBIMENTO).keys():
            return Response({"detail": "Forma de recebimento inválida."}, status=400)

        try:
            nota = (
                Nota.objects.using(banco)
                .prefetch_related("itens__impostos")
                .get(pk=int(nota_numero))
            )
        except Nota.DoesNotExist:
            return Response({"detail": "Nota não encontrada."}, status=404)

        cliente_id = int(getattr(nota, "destinatario_id", 0) or 0)
        try:
            titulo = Titulosreceber.objects.using(banco).get(
                titu_empr=int(nota.empresa),
                titu_fili=int(nota.filial),
                titu_seri="NFE",
                titu_titu=str(nota.numero),
                titu_clie=cliente_id,
                titu_parc=str(parcela),
            )
        except Titulosreceber.DoesNotExist:
            return Response({"detail": "Título não encontrado."}, status=404)

        if titulo.titu_aber and str(titulo.titu_aber).upper() != "A":
            return Response({"detail": "Título não pode ser editado pois não está aberto."}, status=409)

        novo_valor = _parse_decimal(valor, default="0")
        if novo_valor < 0:
            return Response({"detail": "Valor da parcela não pode ser negativo."}, status=400)

        tota_limite = _calcular_total_nota(nota)
        soma_atual = (
            Titulosreceber.objects.using(banco)
            .filter(
                titu_empr=int(nota.empresa),
                titu_fili=int(nota.filial),
                titu_seri="NFE",
                titu_titu=str(nota.numero),
                titu_clie=cliente_id,
            )
            .aggregate(total=Sum("titu_valo"))["total"]
            or Decimal("0")
        )
        soma_sem_parcela = Decimal(str(soma_atual)) - Decimal(str(titulo.titu_valo or 0))
        if (soma_sem_parcela + novo_valor) > tota_limite:
            return Response({"detail": "Soma dos títulos excede o total da nota fiscal."}, status=409)

        venc = _parse_date(vencimento)
        with transaction.atomic(using=banco):
            Titulosreceber.objects.using(banco).filter(
                titu_empr=int(nota.empresa),
                titu_fili=int(nota.filial),
                titu_seri="NFE",
                titu_titu=str(nota.numero),
                titu_clie=cliente_id,
                titu_parc=str(parcela),
            ).update(
                titu_valo=novo_valor,
                titu_venc=venc,
                titu_form_reci=forma_pagamento,
            )
            titulo = Titulosreceber.objects.using(banco).get(
                titu_empr=int(nota.empresa),
                titu_fili=int(nota.filial),
                titu_seri="NFE",
                titu_titu=str(nota.numero),
                titu_clie=cliente_id,
                titu_parc=str(parcela),
            )

        return Response(
            {
                "detail": "Título atualizado com sucesso.",
                "titulo": {
                    "parcela": titulo.titu_parc,
                    "valor": float(titulo.titu_valo or 0),
                    "vencimento": (titulo.titu_venc.isoformat() if titulo.titu_venc else ""),
                    "forma_pagamento": titulo.titu_form_reci,
                    "status": titulo.titu_situ,
                },
            },
            status=200,
        )
