from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from Licencas.models import Usuarios
from Produtos.models import Produtos, SaldoProduto
from .models import Notificacao
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Pedidos.models import PedidoVenda
from Orcamentos.models import Orcamentos
from datetime import date
from django.contrib.auth.models import User
from django.db.models import Count, Sum


class NotificaEstoqueView(APIView):
  

    def post(self, request):
        # Produtos com estoque baixo (menos de 5 unidades)
        produtos_baixo_estoque = SaldoProduto.objects.filter(
            saldo_estoque__lt=5
        ).select_related('produto_codigo')
        
        usuarios = Usuarios.objects.all()
        total = 0

        for usuario in usuarios:
            for saldo in produtos_baixo_estoque:
                Notificacao.objects.create(
                    usuario=usuario,
                    titulo='Estoque Baixo',
                    mensagem=f'Produto {saldo.produto_codigo.prod_nome} está com {saldo.saldo_estoque} unidade(s) em estoque.',
                    tipo='estoque',
                    prioridade='alta' if saldo.saldo_estoque == 0 else 'media'
                )
                total += 1
                
        return Response({
            "status": "ok", 
            "notificacoes_criadas": total,
            "produtos_baixo_estoque": produtos_baixo_estoque.count()
        })


class NotificaFinanceiroView(APIView):
 

    def post(self, request):
        hoje = date.today()
        usuarios = Usuarios.objects.all()
        
        # Títulos a pagar vencendo hoje
        titulos_pagar = Titulospagar.objects.filter(
            titu_venc=hoje,
            titu_aber='A'  # Apenas títulos em aberto
        )
        
        # Títulos a receber vencendo hoje
        titulos_receber = Titulosreceber.objects.filter(
            titu_venc=hoje,
            titu_aber='A'  # Apenas títulos em aberto
        )

        total = 0
        
        for usuario in usuarios:
            # Notificações para contas a pagar
            for titulo in titulos_pagar:
                Notificacao.objects.create(
                    usuario=usuario,
                    titulo='Conta a Pagar Hoje',
                    mensagem=f'Título {titulo.titu_titu} - Valor: R$ {titulo.titu_valo:.2f} - Vencimento: {titulo.titu_venc.strftime("%d/%m/%Y")}',
                    tipo='financeiro',
                    prioridade='alta'
                )
                total += 1
                
            # Notificações para contas a receber
            for titulo in titulos_receber:
                Notificacao.objects.create(
                    usuario=usuario,
                    titulo='Recebimento Hoje',
                    mensagem=f'Título {titulo.titu_titu} - Valor: R$ {titulo.titu_valo:.2f} - Vencimento: {titulo.titu_venc.strftime("%d/%m/%Y")}',
                    tipo='financeiro',
                    prioridade='media'
                )
                total += 1

        return Response({
            "status": "ok", 
            "notificacoes_criadas": total,
            "contas_pagar": titulos_pagar.count(),
            "contas_receber": titulos_receber.count()
        })


class NotificaVendasView(APIView):
 

    def post(self, request):
        hoje = date.today()
        
        # Pedidos do dia
        pedidos_hoje = PedidoVenda.objects.filter(pedi_data=hoje)
        total_pedidos = pedidos_hoje.count()
        valor_total_pedidos = pedidos_hoje.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0
        
        # Orçamentos do dia
        orcamentos_hoje = Orcamentos.objects.filter(pedi_data=hoje)
        total_orcamentos = orcamentos_hoje.count()
        valor_total_orcamentos = orcamentos_hoje.aggregate(Sum('pedi_tota'))['pedi_tota__sum'] or 0

        if total_pedidos == 0 and total_orcamentos == 0:
            return Response({"status": "sem_dados"})

        usuarios = Usuarios.objects.all()
        total_notificacoes = 0
        
        for usuario in usuarios:
            if total_pedidos > 0:
                Notificacao.objects.create(
                    usuario=usuario,
                    titulo='Vendas do Dia',
                    mensagem=f'Hoje foram realizados {total_pedidos} pedido(s) totalizando R$ {valor_total_pedidos:.2f}',
                    tipo='vendas',
                    prioridade='media'
                )
                total_notificacoes += 1
                
            if total_orcamentos > 0:
                Notificacao.objects.create(
                    usuario=usuario,
                    titulo='Orçamentos do Dia',
                    mensagem=f'Hoje foram criados {total_orcamentos} orçamento(s) totalizando R$ {valor_total_orcamentos:.2f}',
                    tipo='vendas',
                    prioridade='baixa'
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


    def post(self, request):
        hoje = date.today()
        
        # Estatísticas do dia
        pedidos_count = PedidoVenda.objects.filter(pedi_data=hoje).count()
        orcamentos_count = Orcamentos.objects.filter(pedi_data=hoje).count()
        titulos_vencer = Titulospagar.objects.filter(titu_venc=hoje, titu_aber='A').count()
        titulos_receber = Titulosreceber.objects.filter(titu_venc=hoje, titu_aber='A').count()
        produtos_sem_estoque = SaldoProduto.objects.filter(saldo_estoque=0).count()

        usuarios = Usuarios.objects.all()
        total_notificacoes = 0
        
        for usuario in usuarios:
            mensagem = f"""Resumo do dia {hoje.strftime('%d/%m/%Y')}:
• {pedidos_count} pedido(s) realizados
• {orcamentos_count} orçamento(s) criados
• {titulos_vencer} conta(s) a pagar vencendo
• {titulos_receber} conta(s) a receber vencendo
• {produtos_sem_estoque} produto(s) sem estoque"""
            
            Notificacao.objects.create(
                usuario=usuario,
                titulo='Resumo Diário',
                mensagem=mensagem,
                tipo='resumo',
                prioridade='baixa'
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

    
    def get(self, request):
        # Buscar usuário baseado no request
        try:
            usuario = Usuarios.objects.get(user=request.user)
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado"}, status=404)
            
        notificacoes = Notificacao.objects.filter(usuario=usuario)[:50]  # Últimas 50
        
        data = []
        for notif in notificacoes:
            data.append({
                "id": notif.id,
                "titulo": notif.titulo,
                "mensagem": notif.mensagem,
                "tipo": notif.tipo,
                "prioridade": notif.prioridade,
                "data_criacao": notif.data_criacao,
                "lida": notif.lida
            })
            
        return Response({"notificacoes": data})
    
    def patch(self, request, notificacao_id):
        try:
            usuario = Usuarios.objects.get(user=request.user)
            notificacao = Notificacao.objects.get(id=notificacao_id, usuario=usuario)
            notificacao.lida = True
            notificacao.save()
            return Response({"status": "ok"})
        except (Usuarios.DoesNotExist, Notificacao.DoesNotExist):
            return Response({"error": "Notificação não encontrada"}, status=404)
