from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction

from ..models import PedidoVenda
from contas_a_receber.models import Titulosreceber
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config


class GerarTitulosPedidoView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        data = request.data
        pedi_nume = data.get("pedi_nume")
        pedi_forn = data.get("pedi_forn")
        pedi_tota = Decimal(data.get("pedi_tota", 0))
        entrada = Decimal(str(data.get("entrada", 0) or 0))
        forma_pagamento = data.get("pedi_form_rece")
        parcelas = int(data.get("parcelas", 1))
        data_base = data.get("data_base", datetime.now().date().isoformat())

        if isinstance(data_base, str):
            data_base = datetime.strptime(data_base, "%Y-%m-%d").date()

        if not pedi_nume or not pedi_forn or not pedi_tota:
            return Response({"detail": "pedi_nume, pedi_forn e pedi_tota são obrigatórios."}, status=400)

        if entrada < 0:
            return Response({"detail": "entrada não pode ser negativa."}, status=400)
        if entrada > pedi_tota:
            return Response({"detail": "entrada não pode ser maior que o total."}, status=400)

        try:
            pedido = PedidoVenda.objects.using(banco).get(pedi_nume=pedi_nume)
            pedi_empr = pedido.pedi_empr
            pedi_fili = pedido.pedi_fili
        except PedidoVenda.DoesNotExist:
            return Response({"detail": "Pedido de venda não encontrado."}, status=404)

        total_restante = (pedi_tota - entrada).quantize(Decimal("0.01"))
        valor_parcela = (total_restante / (parcelas if parcelas > 0 else 1)).quantize(Decimal("0.01"))
        diferenca = total_restante - (valor_parcela * (parcelas if parcelas > 0 else 1))

        titulos = []
        titulos = []

        # Entrada como primeira parcela (se houver)
        offset = 1
        if entrada > 0:
            titulos.append(Titulosreceber(
                titu_empr=pedi_empr,
                titu_fili=pedi_fili,
                titu_seri="PEV",
                titu_titu=str(pedi_nume),
                titu_clie=pedi_forn,
                titu_parc=1,
                titu_valo=entrada,
                titu_venc=data_base,
                titu_form_reci=forma_pagamento or "",
                titu_emis=datetime.now().date(),
                titu_hist=f"Entrada do Pedido {pedi_nume}, pelo SPS Web/Mobile",
                titu_cecu="0",
                titu_port="0",
                titu_even="0",
                titu_prov=True,
                titu_tipo="Receber"
            ))
            offset = 2

        # Demais parcelas
        for i in range(parcelas):
            vencimento = data_base + timedelta(days=30 * i)
            valor_atual = valor_parcela
            if i == 0:
                valor_atual += diferenca

            titulos.append(Titulosreceber(
                titu_empr=pedi_empr,
                titu_fili=pedi_fili,
                titu_seri="PEV",
                titu_titu=str(pedi_nume),
                titu_clie=pedi_forn,
                titu_parc=i + offset,
                titu_valo=valor_atual,
                titu_venc=vencimento,
                titu_form_reci=forma_pagamento or "",
                titu_emis=datetime.now().date(),
                titu_hist=f"Título gerado do Pedido {pedi_nume}, pelo SPS Web/Mobile",
                titu_cecu="0",
                titu_port="0",
                titu_even="0",
                titu_prov=True,
                titu_tipo="Receber"
            ))

        with transaction.atomic(using=banco):
            Titulosreceber.objects.using(banco).bulk_create(titulos)

        return Response({
            "detail": f"{len(titulos)} títulos gerados com sucesso.",
            "total_pedido": float(pedi_tota),
            "entrada": float(entrada),
            "total_parcelado": float(total_restante),
            "valor_parcelas": [float(t.titu_valo) for t in titulos],
            "vencimentos": [t.titu_venc.isoformat() for t in titulos]
        }, status=201)


class RemoverTitulosPedidoView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        pedi_nume = request.data.get("pedi_nume")
        if not pedi_nume:
            return Response({"detail": "pedi_nume é obrigatório."}, status=400)

        try:
            pedido = PedidoVenda.objects.using(banco).get(pedi_nume=pedi_nume)
        except PedidoVenda.DoesNotExist:
            return Response({"detail": "Pedido de venda não encontrado."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=pedido.pedi_empr,
            titu_fili=pedido.pedi_fili,
            titu_seri="PEV",
            titu_titu=str(pedi_nume)
        )

        if not titulos.exists():
            return Response({"detail": "Nenhum título encontrado para esse pedido."}, status=404)

        count = titulos.count()
        titulos.delete()

        return Response({"detail": f"{count} títulos removidos com sucesso."}, status=200)


class ConsultarTitulosPedidoView(APIView):
    def get(self, request, pedi_nume, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        try:
            pedido = PedidoVenda.objects.using(banco).get(pedi_nume=pedi_nume)
        except PedidoVenda.DoesNotExist:
            return Response({"detail": "Pedido de venda não encontrado."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=pedido.pedi_empr,
            titu_fili=pedido.pedi_fili,
            titu_seri="PEV",
            titu_titu=str(pedi_nume)
        ).order_by('titu_parc')

        if not titulos.exists():
            return Response({"detail": "Nenhum título encontrado para esse pedido."}, status=200)

        total = titulos.aggregate(
            total=Sum('titu_valo'),
            quantidade=Count('*')
        )

        dados_titulos = [{
            "parcela": titulo.titu_parc,
            "valor": float(titulo.titu_valo),
            "vencimento": titulo.titu_venc,
            "forma_pagamento": titulo.titu_form_reci,
            "status": titulo.titu_situ,
            "empresa": titulo.titu_empr,
            "filial": titulo.titu_fili
        } for titulo in titulos]

        return Response({
            "titulos": dados_titulos,
            "total": float(total['total']),
            "quantidade_parcelas": total['quantidade']
        })


class AtualizarTituloPedidoView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        data = request.data
        pedi_nume = data.get("pedi_nume")
        parcela = data.get("parcela")
        valor = data.get("valor")
        vencimento = data.get("vencimento")

        if not all([pedi_nume, parcela, valor, vencimento]):
            return Response({"detail": "pedi_nume, parcela, valor e vencimento são obrigatórios."}, status=400)

        try:
            pedido = PedidoVenda.objects.using(banco).get(pedi_nume=pedi_nume)
        except PedidoVenda.DoesNotExist:
            return Response({"detail": "Pedido de venda não encontrado."}, status=404)

        try:
            titulo = Titulosreceber.objects.using(banco).get(
                titu_empr=pedido.pedi_empr,
                titu_fili=pedido.pedi_fili,
                titu_seri="PEV",
                titu_titu=str(pedi_nume),
                titu_parc=parcela
            )
        except Titulosreceber.DoesNotExist:
            return Response({"detail": "Título não encontrado."}, status=404)

        if isinstance(vencimento, str):
            vencimento = datetime.strptime(vencimento, "%Y-%m-%d").date()

        with transaction.atomic(using=banco):
            titulo.titu_valo = Decimal(str(valor))
            titulo.titu_venc = vencimento
            titulo.save(using=banco)

        return Response({
            "detail": "Título atualizado com sucesso.",
            "titulo": {
                "parcela": titulo.titu_parc,
                "valor": float(titulo.titu_valo),
                "vencimento": titulo.titu_venc.isoformat(),
                "forma_pagamento": titulo.titu_form_reci,
                "status": titulo.titu_situ
            }
        }, status=200)


class RelatorioFinanceiroPedidoView(APIView):
    def get(self, request):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        data_inicial = request.query_params.get('data_inicial')
        data_final = request.query_params.get('data_final')
        cliente = request.query_params.get('cliente')
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')

        titulos = Titulosreceber.objects.using(banco).filter(titu_seri="PEV")

        if empresa:
            titulos = titulos.filter(titu_empr=empresa)
        if filial:
            titulos = titulos.filter(titu_fili=filial)
        if data_inicial:
            titulos = titulos.filter(titu_emis__gte=data_inicial)
        if data_final:
            titulos = titulos.filter(titu_emis__lte=data_final)
        if cliente:
            titulos = titulos.filter(titu_clie=cliente)

        resumo = titulos.aggregate(
            total_geral=Sum('titu_valo'),
            quantidade_titulos=Count('*')
        )

        formas_pagamento = titulos.values('titu_form_reci').annotate(
            total=Sum('titu_valo'),
            quantidade=Count('*')
        )

        return Response({
            "total_geral": float(resumo['total_geral'] or 0),
            "quantidade_titulos": resumo['quantidade_titulos'],
            "periodo": {
                "inicio": data_inicial,
                "fim": data_final
            },
            "formas_pagamento": [
                {
                    "forma": item['titu_form_reci'],
                    "total": float(item['total']),
                    "quantidade": item['quantidade']
                } for item in formas_pagamento
            ]
        })