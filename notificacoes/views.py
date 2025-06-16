from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Count
from datetime import date
from core.utils import get_licenca_db_config
from Licencas.models import Usuarios
from Produtos.models import Produtos, SaldoProduto
from .models import Notificacao
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Pedidos.models import PedidoVenda
from Orcamentos.models import Orcamentos


class NotificaEstoqueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        produtos_baixo_estoque = SaldoProduto.objects.using(banco).filter(
            saldo_estoque__lt=2
        ).select_related('produto_codigo')

        usuarios = Usuarios.objects.using(banco).all()
        total = 0

        for usuario in usuarios:
            for saldo in produtos_baixo_estoque:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Estoque Baixo',
                    mensagem=f'Produto {saldo.produto_codigo.prod_nome} está com {saldo.saldo_estoque} unidade(s) em estoque.',
                    tipo='estoque',
                )
                total += 1

        return Response({
            "status": "ok",
            "notificacoes_criadas": total,
            "produtos_baixo_estoque": produtos_baixo_estoque.count()
        })


class NotificaFinanceiroView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        hoje = date.today()
        usuarios = Usuarios.objects.using(banco).all()

        titulos_pagar = Titulospagar.objects.using(banco).filter(
            titu_venc=hoje,
            titu_aber='A'
        )

        titulos_receber = Titulosreceber.objects.using(banco).filter(
            titu_venc=hoje,
            titu_aber='A'
        )

        total = 0

        for usuario in usuarios:
            for titulo in titulos_pagar:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Conta a Pagar Hoje',
                    mensagem=f'Título {titulo.titu_titu} - Valor: R$ {titulo.titu_valo:.2f} - Vencimento: {titulo.titu_venc.strftime("%d/%m/%Y")}',
                    tipo='financeiro',
                )
                total += 1

            for titulo in titulos_receber:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Recebimento Hoje',
                    mensagem=f'Título {titulo.titu_titu} - Valor: R$ {titulo.titu_valo:.2f} - Vencimento: {titulo.titu_venc.strftime("%d/%m/%Y")}',
                    tipo='financeiro',
                )
                total += 1

        return Response({
            "status": "ok",
            "notificacoes_criadas": total,
            "contas_pagar": titulos_pagar.count(),
            "contas_receber": titulos_receber.count()
        })


class NotificaVendasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        hoje = date.today()
        pedidos_hoje = PedidoVenda.objects.using(banco).filter(pedi_data=hoje)
        total_pedidos = pedidos_hoje.count()
        valor_total_pedidos = pedidos_hoje.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0

        orcamentos_hoje = Orcamentos.objects.using(banco).filter(pedi_data=hoje)
        total_orcamentos = orcamentos_hoje.count()
        valor_total_orcamentos = orcamentos_hoje.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0

        if total_pedidos == 0 and total_orcamentos == 0:
            return Response({"status": "sem_dados"})

        usuarios = Usuarios.objects.using(banco).all()
        total_notificacoes = 0

        for usuario in usuarios:
            if total_pedidos > 0:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Vendas do Dia',
                    mensagem=f'Hoje foram realizados {total_pedidos} pedido(s) totalizando R$ {valor_total_pedidos:.2f}',
                    tipo='vendas',
                )
                total_notificacoes += 1

            if total_orcamentos > 0:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Orçamentos do Dia',
                    mensagem=f'Hoje foram criados {total_orcamentos} orçamento(s) totalizando R$ {valor_total_orcamentos:.2f}',
                    tipo='vendas',
                )
                total_notificacoes += 1

        return Response({
            "status": "ok",
            "notificacoes_criadas": total_notificacoes,
            "pedidos": total_pedidos,
            "valor_pedidos": float(valor_total_pedidos),
            "orcamentos": total_orcamentos,
            "valor_orcamentos": float(valor_total_orcamentos)
        })


class NotificaResumoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        hoje = date.today()

        pedidos_count = PedidoVenda.objects.using(banco).filter(pedi_data=hoje).count()
        orcamentos_count = Orcamentos.objects.using(banco).filter(pedi_data=hoje).count()
        titulos_vencer = Titulospagar.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
        titulos_receber = Titulosreceber.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
        produtos_sem_estoque = SaldoProduto.objects.using(banco).filter(saldo_estoque=0).count()

        usuarios = Usuarios.objects.using(banco).all()
        total_notificacoes = 0

        for usuario in usuarios:
            mensagem = f"""Resumo do dia {hoje.strftime('%d/%m/%Y')}:
            • {pedidos_count} pedido(s) realizados
            • {orcamentos_count} orçamento(s) criados
            • {titulos_vencer} conta(s) a pagar vencendo
            • {titulos_receber} conta(s) a receber vencendo
            • {produtos_sem_estoque} produto(s) sem estoque"""

            Notificacao.objects.using(banco).create(
                usuario=usuario,
                titulo='Resumo Diário',
                mensagem=mensagem,
                tipo='resumo',
            )
            total_notificacoes += 1

        return Response({
            "status": "ok",
            "notificacoes_criadas": total_notificacoes,
            "resumo": {
                "pedidos": pedidos_count,
                "orcamentos": orcamentos_count,
                "contas_pagar": titulos_vencer,
                "contas_receber": titulos_receber,
                "produtos_sem_estoque": produtos_sem_estoque
            }
        })


class NotificacaoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome=request.user.usua_nome)
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado"}, status=404)

        notificacoes = Notificacao.objects.using(banco).filter(usuario=usuario)[:50]

        data = [{
            "id": notif.id,
            "titulo": notif.titulo,
            "mensagem": notif.mensagem,
            "tipo": notif.tipo,
            "data_criacao": notif.data_criacao,
            "lida": notif.lida
        } for notif in notificacoes]

        return Response({"notificacoes": data})

    def patch(self, request, notificacao_id, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome=request.user.usua_nome)
            notificacao = Notificacao.objects.using(banco).get(id=notificacao_id, usuario=usuario)
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado"}, status=404)
        except Notificacao.DoesNotExist:
            return Response({"error": "Notificação não encontrada"}, status=404)

        notificacao.lida = True
        notificacao.save()
        return Response({"status": "ok"})


class NotificaTudoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        estoque = NotificaEstoqueView().post(request, slug=slug).data
        financeiro = NotificaFinanceiroView().post(request, slug=slug).data
        vendas = NotificaVendasView().post(request, slug=slug).data
        resumo = NotificaResumoView().post(request, slug=slug).data

        return Response({
            "estoque": estoque,
            "financeiro": financeiro,
            "vendas": vendas,
            "resumo": resumo,
        })