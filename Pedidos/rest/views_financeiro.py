from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction, connections

from ..models import PedidoVenda, Parcelaspedidovenda
from contas_a_receber.models import Titulosreceber, Baretitulos
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

        # Evita duplicidade: já existem títulos para este pedido/cliente
        ja_existe_qs = Titulosreceber.objects.using(banco).filter(
            titu_empr=pedi_empr,
            titu_fili=pedi_fili,
            titu_seri="PEV",
            titu_titu=str(pedi_nume),
            titu_clie=pedi_forn,
        )
        
        ja_existe_parcelas = Parcelaspedidovenda.objects.using(banco).filter(
            parc_empr=pedi_empr,
            parc_fili=pedi_fili,
            parc_pedi=int(pedi_nume),
        ).exists()
        
        print(f"DEBUG: GerarTitulos - Pedido: {pedi_nume}, Empr: {pedi_empr}, Fili: {pedi_fili}, Clie: {pedi_forn}")
        print(f"DEBUG: GerarTitulos - Query Titulos: {ja_existe_qs.query}")
        print(f"DEBUG: GerarTitulos - Count Titulos: {ja_existe_qs.count()}")
        print(f"DEBUG: GerarTitulos - Exists Parcelas: {ja_existe_parcelas}")
        
        if ja_existe_qs.exists() or ja_existe_parcelas:
            return Response(
                {"detail": "Já existe título ou parcelas com este pedido e cliente. Clique em Consultar ou Remover."},
                status=409,
            )
            

        total_restante = (pedi_tota - entrada).quantize(Decimal("0.01"))
        valor_parcela = (total_restante / (parcelas if parcelas > 0 else 1)).quantize(Decimal("0.01"))
        diferenca = total_restante - (valor_parcela * (parcelas if parcelas > 0 else 1))

        titulos = []
        parcelas_objs = []
        next_parcela_num = 1

        # Entrada como primeira parcela (se houver)
        if entrada > 0:
            parcelas_objs.append(Parcelaspedidovenda(
                parc_empr=pedi_empr,
                parc_fili=pedi_fili,
                parc_pedi=int(pedi_nume),
                parc_parc=next_parcela_num, # 1
                parc_forn=int(pedi_forn),
                parc_emis=datetime.now().date(),
                parc_venc=data_base, # Vencimento da entrada é hoje/data base
                parc_valo=entrada,
                parc_port=0,
                parc_situ=0,
                parc_form=forma_pagamento or "",
                parc_avis=False,
                parc_vend=int(pedido.pedi_vend or 0),
                parc_cecu=0
            ))
            next_parcela_num += 1

        # Demais parcelas
        for i in range(parcelas):
            vencimento = data_base + timedelta(days=30 * (i if entrada == 0 else i + 1))
            valor_atual = valor_parcela
            if i == 0:
                valor_atual += diferenca
            
            parcelas_objs.append(Parcelaspedidovenda(
                parc_empr=pedi_empr,
                parc_fili=pedi_fili,
                parc_pedi=int(pedi_nume),
                parc_parc=next_parcela_num,
                parc_forn=int(pedi_forn),
                parc_emis=datetime.now().date(),
                parc_venc=vencimento,
                parc_valo=valor_atual,
                parc_port=0,
                parc_situ=0,
                parc_form=forma_pagamento or "",
                parc_avis=False,
                parc_vend=int(pedido.pedi_vend or 0),
                parc_cecu=0
            ))
            next_parcela_num += 1

        try:
            with transaction.atomic(using=banco):
                # Habilitamos triggers (não desabilitamos)
                # Inserimos APENAS na tabela de Parcelas
                # A trigger trc_atualiza_financeiro_pedidos_venda encarrega-se de criar os títulos
                Parcelaspedidovenda.objects.using(banco).bulk_create(parcelas_objs)
                
        except Exception as e:
            # Integridade/duplicidade: retorna mensagem amigável
            import traceback
            import sys
            print(f"ERROR: Erro ao gerar títulos/parcelas: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return Response(
                {"detail": f"Erro ao gerar títulos: {e}"},
                status=409,
            )

        return Response({
            "detail": f"{len(parcelas_objs)} parcelas geradas com sucesso (títulos gerados via trigger).",
            "total_pedido": float(pedi_tota),
            "entrada": float(entrada),
            "total_parcelado": float(total_restante),
            "valor_parcelas": [float(p.parc_valo) for p in parcelas_objs],
            "vencimentos": [p.parc_venc.isoformat() for p in parcelas_objs]
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

        # Buscamos apenas parcelas para deletar. A trigger encarrega-se dos títulos.
        parcelas_objs = Parcelaspedidovenda.objects.using(banco).filter(
            parc_empr=pedido.pedi_empr,
            parc_fili=pedido.pedi_fili,
            parc_pedi=int(pedi_nume)
        )
        
        # Tenta remover baixas (Baretitulos) antes, para evitar erro de FK ao remover títulos via trigger
        try:
             # Identifica cliente (fornecedor no pedido)
             cliente_id = int(pedido.pedi_forn) if str(pedido.pedi_forn).isdigit() else 0
             
             baixas_qs = Baretitulos.objects.using(banco).filter(
                 bare_empr=pedido.pedi_empr,
                 bare_fili=pedido.pedi_fili,
                 bare_clie=cliente_id,
                 bare_titu=str(pedi_nume),
                 bare_seri="PEV"
             )
             
             count_baixas = baixas_qs.count()
             if count_baixas > 0:
                 print(f"DEBUG: RemoverTitulos - Removendo {count_baixas} baixas antes de deletar parcelas.")
                 baixas_qs.delete()
        except Exception as e:
             print(f"ERROR: Falha ao remover baixas: {e}")
        
        # Opcional: Verificar se títulos existem para informar o usuário, mas não usar para deleção manual.
        titulos_count = Titulosreceber.objects.using(banco).filter(
            titu_empr=pedido.pedi_empr,
            titu_fili=pedido.pedi_fili,
            titu_seri="PEV",
            titu_titu=str(pedi_nume)
        ).count()
        
        print(f"DEBUG: RemoverTitulos - Pedido: {pedi_nume}, Empr: {pedido.pedi_empr}, Fili: {pedido.pedi_fili}")
        print(f"DEBUG: RemoverTitulos - Count Titulos (Info): {titulos_count}")
        print(f"DEBUG: RemoverTitulos - Query Parcelas: {parcelas_objs.query}")
        print(f"DEBUG: RemoverTitulos - Count Parcelas: {parcelas_objs.count()}")

        if not parcelas_objs.exists() and titulos_count == 0:
            return Response({"detail": "Nenhum título/parcela encontrado para esse pedido."}, status=404)

        try:
            # Se não houver parcelas mas houver títulos (casos de erro anterior), tentamos remover os títulos órfãos
            if not parcelas_objs.exists() and titulos_count > 0:
                Titulosreceber.objects.using(banco).filter(
                    titu_empr=pedido.pedi_empr,
                    titu_fili=pedido.pedi_fili,
                    titu_seri="PEV",
                    titu_titu=str(pedi_nume)
                ).delete()
                return Response({"detail": f"{titulos_count} títulos órfãos removidos com sucesso."}, status=200)

            # Deletamos APENAS as parcelas usando raw SQL para evitar problema de PK composta
            count = parcelas_objs.count()
            
            # Usando delete direto via cursor para garantir constraints corretas
            # O delete() do Django pode falhar se a PK (parc_parc) não for única globalmente
            with connections[banco].cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM parcelaspedidovenda 
                    WHERE parc_empr = %s AND parc_fili = %s AND parc_pedi = %s
                    """,
                    [pedido.pedi_empr, pedido.pedi_fili, int(pedi_nume)]
                )
            
            # parcelas_objs.delete() -> Substituído pelo SQL acima
        except Exception as e:
             # Tratamento de erro específico para FK (baretitulos) se a trigger falhar
            import traceback
            import sys
            print(f"ERROR: Erro ao remover parcelas: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            if "violates foreign key constraint" in str(e):
                return Response({"detail": "Não é possível remover os títulos pois existem baixas ou movimentações associadas (baretitulos)."}, status=409)
            return Response({"detail": f"Erro ao remover títulos: {e}"}, status=409)

        return Response({"detail": f"{count} parcelas removidas com sucesso (títulos removidos via trigger)."}, status=200)


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
            "aberto": titulo.titu_aber,
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
        forma_pagamento = data.get("forma_pagamento")

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

        if titulo.titu_aber and str(titulo.titu_aber).upper() != 'A':
            return Response({"detail": "Título não pode ser editado pois não está aberto."}, status=409)

        # Validação de limite: soma dos títulos não pode ultrapassar total do pedido
        try:
            novo_valor = Decimal(str(valor))
        except Exception:
            return Response({"detail": "Valor inválido."}, status=400)
        if novo_valor < 0:
            return Response({"detail": "Valor da parcela não pode ser negativo."}, status=400)

        tota_limite = Decimal(str(getattr(pedido, 'pedi_tota', 0) or 0))
        soma_atual = Titulosreceber.objects.using(banco).filter(
            titu_empr=pedido.pedi_empr,
            titu_fili=pedido.pedi_fili,
            titu_seri="PEV",
            titu_titu=str(pedi_nume)
        ).aggregate(total=Sum('titu_valo'))['total'] or Decimal('0')
        soma_sem_parcela = Decimal(str(soma_atual)) - Decimal(str(titulo.titu_valo or 0))
        if (soma_sem_parcela + novo_valor) > tota_limite:
            return Response({"detail": "Soma dos títulos excede o total do pedido."}, status=409)

        if isinstance(vencimento, str):
            vencimento = datetime.strptime(vencimento, "%Y-%m-%d").date()

        with transaction.atomic(using=banco):
            Titulosreceber.objects.using(banco).filter(
                titu_empr=pedido.pedi_empr,
                titu_fili=pedido.pedi_fili,
                titu_seri="PEV",
                titu_titu=str(pedi_nume),
                titu_parc=parcela
            ).update(
                titu_valo=Decimal(str(valor)),
                titu_venc=vencimento,
                **({"titu_form_reci": forma_pagamento} if forma_pagamento is not None else {})
            )
            titulo = Titulosreceber.objects.using(banco).get(
                titu_empr=pedido.pedi_empr,
                titu_fili=pedido.pedi_fili,
                titu_seri="PEV",
                titu_titu=str(pedi_nume),
                titu_parc=parcela
            )

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
