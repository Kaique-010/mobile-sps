from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Count, Q
from django.db import models
from datetime import date, datetime, timedelta
from django.utils import timezone
from core.utils import get_licenca_db_config
from Licencas.models import Usuarios
from Produtos.models import Produtos, SaldoProduto
from .models import Notificacao
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Pedidos.models import PedidoVenda
from Orcamentos.models import Orcamentos


def ja_notificado_hoje(banco, usuario, tipo, chave_unica=None):
    """Verifica se já foi criada uma notificação do mesmo tipo hoje para o usuário"""
    hoje = timezone.now().date()
    filtros = {
        'usuario': usuario,
        'tipo': tipo,
        'data_criacao__date': hoje
    }
    
    if chave_unica:
        filtros['mensagem__contains'] = chave_unica
        
    return Notificacao.objects.using(banco).filter(**filtros).exists()


class NotificaEstoqueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Verificar se deve forçar criação mesmo se já existe
        forcar = request.data.get('forcar', False)

        produtos_baixo_estoque = SaldoProduto.objects.using(banco).filter(
            saldo_estoque__lt=0
        ).select_related('produto_codigo')

        usuarios = Usuarios.objects.using(banco).all()
        total = 0
        pulados = 0

        for usuario in usuarios:
            for saldo in produtos_baixo_estoque:
                chave_produto = saldo.produto_codigo.prod_nome
                
                # Verificar se já foi notificado hoje sobre este produto
                if not forcar and ja_notificado_hoje(banco, usuario, 'estoque', chave_produto):
                    pulados += 1
                    continue
                    
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
            "notificacoes_puladas": pulados,
            "produtos_baixo_estoque": produtos_baixo_estoque.count()
        })


class NotificaFinanceiroView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        forcar = request.data.get('forcar', False)
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
        pulados = 0

        for usuario in usuarios:
            for titulo in titulos_pagar:
                chave_titulo = titulo.titu_titu
                
                if not forcar and ja_notificado_hoje(banco, usuario, 'financeiro', chave_titulo):
                    pulados += 1
                    continue
                    
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Conta a Pagar Hoje',
                    mensagem=f'Título {titulo.titu_titu} - Valor: R$ {titulo.titu_valo:.2f} - Vencimento: {titulo.titu_venc.strftime("%d/%m/%Y")}',
                    tipo='financeiro',
                )
                total += 1

            for titulo in titulos_receber:
                chave_titulo = titulo.titu_titu
                
                if not forcar and ja_notificado_hoje(banco, usuario, 'financeiro', chave_titulo):
                    pulados += 1
                    continue
                    
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
            "notificacoes_puladas": pulados,
            "contas_pagar": titulos_pagar.count(),
            "contas_receber": titulos_receber.count()
        })


class NotificaVendasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        forcar = request.data.get('forcar', False)
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
        pulados = 0

        for usuario in usuarios:
            if total_pedidos > 0:
                if not forcar and ja_notificado_hoje(banco, usuario, 'vendas', 'Vendas do Dia'):
                    pulados += 1
                else:
                    Notificacao.objects.using(banco).create(
                        usuario=usuario,
                        titulo='Vendas do Dia',
                        mensagem=f'Hoje foram realizados {total_pedidos} pedido(s) totalizando R$ {valor_total_pedidos:.2f}',
                        tipo='vendas',
                    )
                    total_notificacoes += 1

            if total_orcamentos > 0:
                if not forcar and ja_notificado_hoje(banco, usuario, 'vendas', 'Orçamentos do Dia'):
                    pulados += 1
                else:
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
            "notificacoes_puladas": pulados,
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

        forcar = request.data.get('forcar', False)
        hoje = date.today()

        pedidos_count = PedidoVenda.objects.using(banco).filter(pedi_data=hoje).count()
        orcamentos_count = Orcamentos.objects.using(banco).filter(pedi_data=hoje).count()
        titulos_vencer = Titulospagar.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
        titulos_receber = Titulosreceber.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
        produtos_sem_estoque = SaldoProduto.objects.using(banco).filter(saldo_estoque=0).count()

        usuarios = Usuarios.objects.using(banco).all()
        total_notificacoes = 0
        pulados = 0

        for usuario in usuarios:
            if not forcar and ja_notificado_hoje(banco, usuario, 'resumo', 'Resumo Diário'):
                pulados += 1
                continue
                
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
            "notificacoes_puladas": pulados,
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
            # Tratamento robusto de autenticação
            usuario_nome = None
            usuario_id = None
            
            # Tentar diferentes formas de obter o usuário
            if hasattr(request.user, 'usua_nome') and request.user.usua_nome:
                usuario_nome = request.user.usua_nome
            elif hasattr(request.user, 'username') and request.user.username:
                usuario_nome = request.user.username
            elif hasattr(request.user, 'usua_codi') and request.user.usua_codi:
                usuario_id = request.user.usua_codi
            
            # Buscar usuário no banco
            if usuario_nome:
                usuario = Usuarios.objects.using(banco).get(usua_nome=usuario_nome)
            elif usuario_id:
                usuario = Usuarios.objects.using(banco).get(usua_codi=usuario_id)
            else:
                # Fallback: usar parâmetros da URL se disponíveis
                usua_param = request.query_params.get('usua')
                if usua_param:
                    usuario = Usuarios.objects.using(banco).get(usua_codi=usua_param)
                else:
                    return Response({
                        "error": "Usuário não identificado",
                        "debug": {
                            "user_attrs": [attr for attr in dir(request.user) if not attr.startswith('_')],
                            "user_type": str(type(request.user))
                        }
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado no banco de dados"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "error": f"Erro de autenticação: {str(e)}",
                "debug": {
                    "user_authenticated": request.user.is_authenticated if hasattr(request.user, 'is_authenticated') else False,
                    "user_type": str(type(request.user))
                }
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Paginação simples
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        notificacoes = Notificacao.objects.using(banco).filter(
            usuario=usuario
        ).order_by('-data_criacao')[offset:offset + page_size]

        total = Notificacao.objects.using(banco).filter(usuario=usuario).count()
        nao_lidas = Notificacao.objects.using(banco).filter(usuario=usuario, lida=False).count()

        data = [{
            "id": notif.id,
            "titulo": notif.titulo,
            "mensagem": notif.mensagem,
            "tipo": notif.tipo,
            "data_criacao": notif.data_criacao,
            "lida": notif.lida
        } for notif in notificacoes]

        return Response({
            "notificacoes": data,
            "total": total,
            "nao_lidas": nao_lidas,
            "page": page,
            "page_size": page_size,
            "usuario": {
                "id": usuario.usua_codi,
                "nome": usuario.usua_nome
            }
        })

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


class LimparNotificacoesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Parâmetros para limpeza
        dias_manter = int(request.data.get('dias_manter', 30))
        apenas_lidas = request.data.get('apenas_lidas', True)
        
        data_limite = timezone.now() - timedelta(days=dias_manter)
        
        filtros = {'data_criacao__lt': data_limite}
        if apenas_lidas:
            filtros['lida'] = True
            
        notificacoes_removidas = Notificacao.objects.using(banco).filter(**filtros).count()
        Notificacao.objects.using(banco).filter(**filtros).delete()
        
        return Response({
            "status": "ok",
            "notificacoes_removidas": notificacoes_removidas,
            "criterio": f"Removidas notificações {'lidas' if apenas_lidas else 'todas'} com mais de {dias_manter} dias"
        })


class StatusNotificacoesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Usar o mesmo sistema de autenticação robusto
            usuario_nome = None
            usuario_id = None
            
            if hasattr(request.user, 'usua_nome') and request.user.usua_nome:
                usuario_nome = request.user.usua_nome
            elif hasattr(request.user, 'username') and request.user.username:
                usuario_nome = request.user.username
            elif hasattr(request.user, 'usua_codi') and request.user.usua_codi:
                usuario_id = request.user.usua_codi
            
            if usuario_nome:
                usuario = Usuarios.objects.using(banco).get(usua_nome=usuario_nome)
            elif usuario_id:
                usuario = Usuarios.objects.using(banco).get(usua_codi=usuario_id)
            else:
                usua_param = request.query_params.get('usua')
                if usua_param:
                    usuario = Usuarios.objects.using(banco).get(usua_codi=usua_param)
                else:
                    return Response({"error": "Usuário não identificado"}, status=status.HTTP_401_UNAUTHORIZED)
                    
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        hoje = timezone.now().date()
        
        # Estatísticas gerais
        total_notificacoes = Notificacao.objects.using(banco).filter(usuario=usuario).count()
        nao_lidas = Notificacao.objects.using(banco).filter(usuario=usuario, lida=False).count()
        hoje_criadas = Notificacao.objects.using(banco).filter(
            usuario=usuario, 
            data_criacao__date=hoje
        ).count()
        
        # Por tipo
        por_tipo = Notificacao.objects.using(banco).filter(usuario=usuario).values('tipo').annotate(
            total=Count('id'),
            nao_lidas=Count('id', filter=Q(lida=False))
        )
        
        return Response({
            "total_notificacoes": total_notificacoes,
            "nao_lidas": nao_lidas,
            "criadas_hoje": hoje_criadas,
            "por_tipo": list(por_tipo)
        })


class GerarNotificacoesBadgeView(APIView):
    """
    Endpoint para gerar notificações SOB DEMANDA quando o usuário clicar no badge
    Não há agendamentos automáticos - apenas quando solicitado
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Autenticação robusta
            usuario_nome = None
            usuario_id = None
            
            if hasattr(request.user, 'usua_nome') and request.user.usua_nome:
                usuario_nome = request.user.usua_nome
            elif hasattr(request.user, 'username') and request.user.username:
                usuario_nome = request.user.username
            elif hasattr(request.user, 'usua_codi') and request.user.usua_codi:
                usuario_id = request.user.usua_codi
            
            if usuario_nome:
                usuario = Usuarios.objects.using(banco).get(usua_nome=usuario_nome)
            elif usuario_id:
                usuario = Usuarios.objects.using(banco).get(usua_codi=usuario_id)
            else:
                usua_param = request.query_params.get('usua')
                if usua_param:
                    usuario = Usuarios.objects.using(banco).get(usua_codi=usua_param)
                else:
                    return Response({"error": "Usuário não identificado"}, status=status.HTTP_401_UNAUTHORIZED)
                    
        except Usuarios.DoesNotExist:
            return Response({"error": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Erro de autenticação: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

        # Verificar se já foram geradas notificações hoje para este usuário
        hoje = timezone.now().date()
        ja_geradas_hoje = Notificacao.objects.using(banco).filter(
            usuario=usuario,
            data_criacao__date=hoje
        ).exists()

        # Parâmetro para forçar geração mesmo se já existirem
        forcar = request.data.get('forcar', False)
        
        if ja_geradas_hoje and not forcar:
            # Retornar notificações existentes
            nao_lidas = Notificacao.objects.using(banco).filter(usuario=usuario, lida=False).count()
            return Response({
                "status": "ja_existem",
                "message": "Notificações já foram geradas hoje",
                "nao_lidas": nao_lidas,
                "geradas_hoje": True
            })

        # Gerar notificações sob demanda
        resultados = {}
        total_criadas = 0

        try:
            # Gerar apenas para o usuário logado (não para todos)
            
            # 1. Estoque
            produtos_sem_estoque = SaldoProduto.objects.using(banco).filter(saldo_estoque=0).count()
            if produtos_sem_estoque > 0:
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Alerta de Estoque',
                    mensagem=f'Existem {produtos_sem_estoque} produto(s) sem estoque.',
                    tipo='estoque',
                )
                total_criadas += 1
                resultados['estoque'] = f"{produtos_sem_estoque} produtos sem estoque"

            # 2. Financeiro
            titulos_vencer = Titulospagar.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
            titulos_receber = Titulosreceber.objects.using(banco).filter(titu_venc=hoje, titu_aber='A').count()
            
            if titulos_vencer > 0 or titulos_receber > 0:
                mensagem = f"Vencimentos hoje: {titulos_vencer} conta(s) a pagar, {titulos_receber} conta(s) a receber"
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Vencimentos Hoje',
                    mensagem=mensagem,
                    tipo='financeiro',
                )
                total_criadas += 1
                resultados['financeiro'] = mensagem

            # 3. Vendas
            pedidos_count = Pedidos.objects.using(banco).filter(pedi_data=hoje).count()
            orcamentos_count = Orcamentos.objects.using(banco).filter(pedi_data=hoje).count()
            
            if pedidos_count > 0 or orcamentos_count > 0:
                mensagem = f"Hoje: {pedidos_count} pedido(s) e {orcamentos_count} orçamento(s)"
                Notificacao.objects.using(banco).create(
                    usuario=usuario,
                    titulo='Vendas do Dia',
                    mensagem=mensagem,
                    tipo='vendas',
                )
                total_criadas += 1
                resultados['vendas'] = mensagem

            # 4. Resumo (sempre criar)
            resumo_msg = f"""Resumo do dia {hoje.strftime('%d/%m/%Y')}:
• {pedidos_count} pedido(s) realizados
• {orcamentos_count} orçamento(s) criados
• {titulos_vencer} conta(s) a pagar vencendo
• {titulos_receber} conta(s) a receber vencendo
• {produtos_sem_estoque} produto(s) sem estoque"""

            Notificacao.objects.using(banco).create(
                usuario=usuario,
                titulo='Resumo do Dia',
                mensagem=resumo_msg,
                tipo='resumo',
            )
            total_criadas += 1
            resultados['resumo'] = "Resumo diário criado"

        except Exception as e:
            return Response({
                "error": f"Erro ao gerar notificações: {str(e)}",
                "resultados_parciais": resultados
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Contar notificações não lidas após criação
        nao_lidas = Notificacao.objects.using(banco).filter(usuario=usuario, lida=False).count()

        return Response({
            "status": "criadas",
            "message": f"{total_criadas} notificações criadas com sucesso",
            "notificacoes_criadas": total_criadas,
            "nao_lidas": nao_lidas,
            "detalhes": resultados,
            "usuario": {
                "id": usuario.usua_codi,
                "nome": usuario.usua_nome
            }
        })