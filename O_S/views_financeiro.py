from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction

from .models import Os
from contas_a_receber.models import Titulosreceber
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config


class GerarTitulosOS(APIView):
    def post(self, request, slug=None):
         
        banco = get_licenca_db_config(self.request)
        data = request.data
        os_os = data.get("os_os")
        os_clie = data.get("os_clie")
        os_tota = Decimal(data.get("os_tota", 0))
        forma_pagamento = data.get("forma_pagamento")
        parcelas = int(data.get("parcelas", 1))
        data_base = data.get("data_base", datetime.now().date().isoformat())
        
        if isinstance(data_base, str):
            data_base = datetime.strptime(data_base, "%Y-%m-%d").date()

        if not os_os or not os_clie or not os_tota:
            return Response({"detail": "os_os, os_clie e os_tota são obrigatórios."}, status=400)

        # Buscar a ordem de serviço para pegar empresa e filial
        try:
            ordem = Os.objects.using(banco).get(os_os=os_os)
            os_empr = ordem.os_empr
            os_fili = ordem.os_fili
        except Os.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        valor_parcela = (os_tota / parcelas).quantize(Decimal("0.01"))
        
        # Ajuste para garantir que a soma das parcelas seja igual ao total
        diferenca = os_tota - (valor_parcela * parcelas)
        
        titulos = []
        for i in range(parcelas):
            vencimento = data_base + timedelta(days=30 * i)
            valor_atual = valor_parcela
            if i == 0:  # Adiciona a diferença na primeira parcela
                valor_atual += diferenca
                
            titulos.append(Titulosreceber(
                titu_empr=os_empr,
                titu_fili=os_fili,
                titu_seri="ORS",
                titu_titu=str(os_os),
                titu_clie=os_clie,
                titu_parc=i + 1,
                titu_valo=valor_atual,
                titu_venc=vencimento,
                titu_form_reci=forma_pagamento or "",
                titu_emis=datetime.now().date(),
                titu_hist=f"Título gerado da OS {os_os}",
            ))

        with transaction.atomic(using=banco):
            Titulosreceber.objects.using(banco).bulk_create(titulos)

        return Response({
            "detail": f"{parcelas} títulos gerados com sucesso.",
            "total_gerado": float(os_tota),
            "valor_parcelas": [float(t.titu_valo) for t in titulos],
            "vencimentos": [t.titu_venc.isoformat() for t in titulos]
        }, status=201)


class RemoverTitulosOSView(APIView):
    def post(self, request, slug=None):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"detail": "Banco não encontrado"}, status=400)

        os_os = request.data.get("os_os")

        if not os_os:
            return Response({"detail": "os_os é obrigatório."}, status=400)

        try:
            ordem = Os.objects.using(banco).get(os_os=os_os)
        except Os.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=ordem.os_empr,
            titu_fili=ordem.os_fili,
            titu_seri="ORS",
            titu_titu=str(os_os)
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
            # Alterando a consulta para usar apenas os campos que existem no modelo
            ordem = Os.objects.using(banco).get(
                os_empr=request.query_params.get('empr'),
                os_fili=request.query_params.get('fili'),
                os_os=orde_nume
            )
        except Os.DoesNotExist:
            return Response({"detail": "Ordem de serviço não encontrada."}, status=404)

        titulos = Titulosreceber.objects.using(banco).filter(
            titu_empr=ordem.os_empr,
            titu_fili=ordem.os_fili,
            titu_seri="ORS",
            titu_titu=str(ordem.os_os)
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

