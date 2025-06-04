from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction

from .models import Ordemservico
from contas_a_receber.models import Titulosreceber
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config


class GerarTitulosOSView(APIView):
    def post(self, request, slug=None):
         
        banco = get_licenca_db_config(self.request)
        data = request.data
        orde_nume = data.get("orde_nume")
        orde_clie = data.get("orde_clie")
        orde_tota = Decimal(data.get("orde_tota", 0))
        forma_pagamento = data.get("forma_pagamento")
        parcelas = int(data.get("parcelas", 1))
        data_base = data.get("data_base", datetime.now().date().isoformat())
        
        if isinstance(data_base, str):
            data_base = datetime.strptime(data_base, "%Y-%m-%d").date()

        if not orde_nume or not orde_clie or not orde_tota:
            return Response({"detail": "orde_nume, orde_clie e orde_tota são obrigatórios."}, status=400)

        # Buscar a ordem de serviço para pegar empresa e filial
        try:
            ordem = Ordemservico.objects.using(banco).get(orde_nume=orde_nume)
            orde_empr = ordem.orde_empr
            orde_fili = ordem.orde_fili
        except Ordemservico.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        valor_parcela = (orde_tota / parcelas).quantize(Decimal("0.01"))
        
        # Ajuste para garantir que a soma das parcelas seja igual ao total
        diferenca = orde_tota - (valor_parcela * parcelas)
        
        titulos = []
        for i in range(parcelas):
            vencimento = data_base + timedelta(days=30 * i)
            valor_atual = valor_parcela
            if i == 0:  # Adiciona a diferença na primeira parcela
                valor_atual += diferenca
                
            titulos.append(Titulosreceber(
                titu_empr=orde_empr,
                titu_fili=orde_fili,
                titu_seri="ORS",
                titu_titu=str(orde_nume),
                titu_clie=orde_clie,
                titu_parc=i + 1,
                titu_valo=valor_atual,
                titu_venc=vencimento,
                titu_form_reci=forma_pagamento or "",
                titu_emis=datetime.now().date(),
                titu_hist=f"Título gerado da OS {orde_nume}",
            ))

        with transaction.atomic(using=banco):
            Titulosreceber.objects.using(banco).bulk_create(titulos)

        return Response({
            "detail": f"{parcelas} títulos gerados com sucesso.",
            "total_gerado": float(orde_tota),
            "valor_parcelas": [float(t.titu_valo) for t in titulos],
            "vencimentos": [t.titu_venc.isoformat() for t in titulos]
        }, status=201)


class RemoverTitulosOSView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        orde_nume = request.data.get("orde_nume")

        if not orde_nume:
            return Response({"detail": "orde_nume é obrigatório."}, status=400)

        try:
            ordem = Ordemservico.objects.using(banco).get(orde_nume=orde_nume)
        except Ordemservico.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=ordem.orde_empr,
            titu_fili=ordem.orde_fili,
            titu_seri="ORS",
            titu_titu=str(orde_nume)
        )

        if not titulos.exists():
            return Response({"detail": "Nenhum título encontrado para essa OS."}, status=404)

        count = titulos.count()
        titulos.delete()

        return Response({"detail": f"{count} títulos removidos com sucesso."}, status=200)


class ConsultarTitulosOSView(APIView):
    def get(self, request, orde_nume, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        try:
            ordem = Ordemservico.objects.using(banco).get(orde_nume=orde_nume)
        except Ordemservico.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=ordem.orde_empr,
            titu_fili=ordem.orde_fili,
            titu_seri="ORS",
            titu_titu=str(orde_nume)
        ).order_by('titu_parc')

        if not titulos.exists():
            return Response({"detail": "Nenhum título encontrado para essa OS."}, status=200)

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


class RelatorioFinanceiroOSView(APIView):
    def get(self, request):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        data_inicial = request.query_params.get('data_inicial')
        data_final = request.query_params.get('data_final')
        cliente = request.query_params.get('cliente')
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')

        titulos = Titulosreceber.objects.using(banco).filter(titu_seri="OSMOBI")

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

        # Agrupamento por forma de pagamento
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
