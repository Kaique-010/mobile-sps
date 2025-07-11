from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from core.utils import get_licenca_db_config
from .utils_pedidos import verificar_volta_estoque_pedido
from .utils_estoque import (
    verificar_saida_automatica,
    verificar_estoque_disponivel,
    verificar_estoque_negativo
)
import logging

logger = logging.getLogger(__name__)


def processar_saida_estoque_pedido(pedido, itens_pedido, request):
    """
    Processa saída de estoque ao gravar um pedido
    
    Args:
        pedido: Instância do PedidoVenda
        itens_pedido: Lista de itens do pedido
        request: Request object
    
    Returns:
        dict: Resultado do processamento
    """
    try:
        banco = get_licenca_db_config(request)
        empresa_id = pedido.pedi_empr
        filial_id = pedido.pedi_fili
        
        # Verificar se saída automática está habilitada
        if not verificar_saida_automatica(empresa_id, filial_id, request):
            logger.info(f"Saída automática desabilitada para empresa {empresa_id}, filial {filial_id}")
            return {
                'sucesso': True,
                'processado': False,
                'motivo': 'Saída automática desabilitada'
            }
        
        saidas_criadas = []
        alertas = []
        
        with transaction.atomic(using=banco):
            for item in itens_pedido:
                produto_codigo = item.get('iped_prod')
                quantidade = Decimal(str(item.get('iped_quan', 0)))
                valor_unitario = Decimal(str(item.get('iped_unit', 0)))
                valor_total = quantidade * valor_unitario
                
                if quantidade <= 0:
                    continue
                
                # Verificar estoque disponível
                estoque_ok, estoque_atual = verificar_estoque_disponivel(
                    produto_codigo, quantidade, empresa_id, filial_id, request
                )
                
                if not estoque_ok:
                    permite_negativo = verificar_estoque_negativo(empresa_id, filial_id, request)
                    if not permite_negativo:
                        raise ValidationError(
                            f'Estoque insuficiente para produto {produto_codigo}. '
                            f'Disponível: {estoque_atual}, Solicitado: {quantidade}'
                        )
                    else:
                        alertas.append({
                            'produto': produto_codigo,
                            'tipo': 'estoque_negativo',
                            'mensagem': f'Produto {produto_codigo} ficará com estoque negativo'
                        })
                
                # Criar saída de estoque
                saida_data = criar_saida_estoque(
                    produto_codigo=produto_codigo,
                    quantidade=quantidade,
                    valor_total=valor_total,
                    empresa_id=empresa_id,
                    filial_id=filial_id,
                    pedido_numero=pedido.pedi_nume,
                    cliente_codigo=pedido.pedi_forn,
                    data_saida=pedido.pedi_data,
                    usuario_id=getattr(request.user, 'id', 1),
                    request=request
                )
                
                if saida_data:
                    saidas_criadas.append(saida_data)
                    
                    # Atualizar saldo do produto
                    atualizar_saldo_produto(
                        produto_codigo, -quantidade, empresa_id, filial_id, request
                    )
        
        return {
            'sucesso': True,
            'processado': True,
            'saidas_criadas': saidas_criadas,
            'alertas': alertas
        }
        
    except ValidationError as e:
        logger.error(f"Erro de validação ao processar saída de estoque: {e}")
        return {
            'sucesso': False,
            'erro': str(e)
        }
    except Exception as e:
        logger.error(f"Erro ao processar saída de estoque do pedido: {e}")
        return {
            'sucesso': False,
            'erro': 'Erro interno ao processar saída de estoque'
        }


def criar_saida_estoque(produto_codigo, quantidade, valor_total, empresa_id, filial_id, 
                       pedido_numero, cliente_codigo, data_saida, usuario_id, request):
    """
    Cria registro de saída de estoque
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Saidas_Estoque.models import SaidasEstoque
        
        # Obter próximo sequencial
        ultimo_sequencial = SaidasEstoque.objects.using(banco).filter(
            said_empr=empresa_id,
            said_fili=filial_id
        ).order_by('-said_sequ').first()
        
        proximo_sequencial = (ultimo_sequencial.said_sequ + 1) if ultimo_sequencial else 1
        
        # Criar saída
        saida = SaidasEstoque.objects.using(banco).create(
            said_sequ=proximo_sequencial,
            said_empr=empresa_id,
            said_fili=filial_id,
            said_prod=produto_codigo,
            said_enti=cliente_codigo,
            said_data=data_saida,
            said_quan=quantidade,
            said_tota=valor_total,
            said_obse=f'Saída automática - Pedido {pedido_numero}',
            said_usua=usuario_id
        )
        
        logger.info(f"Saída de estoque criada: {saida.said_sequ} - Produto: {produto_codigo}")
        
        return {
            'sequencial': saida.said_sequ,
            'produto': produto_codigo,
            'quantidade': quantidade,
            'valor_total': valor_total
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar saída de estoque: {e}")
        return None


def atualizar_saldo_produto(produto_codigo, quantidade_movimento, empresa_id, filial_id, request):
    """
    Atualiza saldo do produto
    
    Args:
        produto_codigo: Código do produto
        quantidade_movimento: Quantidade (positiva para entrada, negativa para saída)
        empresa_id: ID da empresa
        filial_id: ID da filial
        request: Request object
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Produtos.models import SaldoProduto
        
        # Buscar ou criar saldo do produto
        saldo, created = SaldoProduto.objects.using(banco).get_or_create(
            produto_codigo=produto_codigo,
            empresa=str(empresa_id),
            filial=str(filial_id),
            defaults={'saldo_estoque': Decimal('0.00')}
        )
        
        # Atualizar saldo
        saldo.saldo_estoque += Decimal(str(quantidade_movimento))
        saldo.save(using=banco)
        
        logger.info(
            f"Saldo atualizado - Produto: {produto_codigo}, "
            f"Movimento: {quantidade_movimento}, Saldo atual: {saldo.saldo_estoque}"
        )
        
        return saldo.saldo_estoque
        
    except Exception as e:
        logger.error(f"Erro ao atualizar saldo do produto {produto_codigo}: {e}")
        return None


def reverter_estoque_pedido(pedido, request):
    """
    Reverte estoque ao cancelar ou excluir um pedido
    
    Args:
        pedido: Instância do PedidoVenda
        request: Request object
    
    Returns:
        dict: Resultado da reversão
    """
    try:
        banco = get_licenca_db_config(request)
        empresa_id = pedido.pedi_empr
        filial_id = pedido.pedi_fili
        
        # Verificar se volta de estoque está habilitada
        if not verificar_volta_estoque_pedido(empresa_id, filial_id, request):
            logger.info(f"Volta de estoque desabilitada para empresa {empresa_id}, filial {filial_id}")
            return {
                'sucesso': True,
                'processado': False,
                'motivo': 'Volta de estoque desabilitada'
            }
        
        from Saidas_Estoque.models import SaidasEstoque
        from Pedidos.models import Itenspedidovenda
        
        # Buscar itens do pedido
        itens = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id,
            iped_fili=filial_id,
            iped_pedi=str(pedido.pedi_nume)
        )
        
        estoque_revertido = []
        
        with transaction.atomic(using=banco):
            for item in itens:
                produto_codigo = item.iped_prod
                quantidade = item.iped_quan
                
                # Buscar saídas relacionadas ao pedido
                saidas = SaidasEstoque.objects.using(banco).filter(
                    said_empr=empresa_id,
                    said_fili=filial_id,
                    said_prod=produto_codigo,
                    said_obse__icontains=f'Pedido {pedido.pedi_nume}'
                )
                
                for saida in saidas:
                    # Reverter saldo
                    saldo_atual = atualizar_saldo_produto(
                        produto_codigo, saida.said_quan, empresa_id, filial_id, request
                    )
                    
                    # Marcar saída como revertida
                    saida.said_obse = f'{saida.said_obse} - REVERTIDA'
                    saida.save(using=banco)
                    
                    estoque_revertido.append({
                        'produto': produto_codigo,
                        'quantidade_revertida': saida.said_quan,
                        'saldo_atual': saldo_atual
                    })
                    
                    logger.info(
                        f"Estoque revertido - Produto: {produto_codigo}, "
                        f"Quantidade: {saida.said_quan}, Saldo atual: {saldo_atual}"
                    )
        
        return {
            'sucesso': True,
            'processado': True,
            'estoque_revertido': estoque_revertido
        }
        
    except Exception as e:
        logger.error(f"Erro ao reverter estoque do pedido: {e}")
        return {
            'sucesso': False,
            'erro': 'Erro interno ao reverter estoque'
        }


def obter_status_estoque_pedido(pedido_numero, empresa_id, filial_id, request):
    """
    Obtém status do estoque relacionado a um pedido
    
    Args:
        pedido_numero: Número do pedido
        empresa_id: ID da empresa
        filial_id: ID da filial
        request: Request object
    
    Returns:
        dict: Status do estoque
    """
    try:
        banco = get_licenca_db_config(request)
        
        from Saidas_Estoque.models import SaidasEstoque
        from Pedidos.models import Itenspedidovenda
        
        # Buscar itens do pedido
        itens = Itenspedidovenda.objects.using(banco).filter(
            iped_empr=empresa_id,
            iped_fili=filial_id,
            iped_pedi=str(pedido_numero)
        )
        
        status_itens = []
        
        for item in itens:
            # Buscar saídas relacionadas
            saidas = SaidasEstoque.objects.using(banco).filter(
                said_empr=empresa_id,
                said_fili=filial_id,
                said_prod=item.iped_prod,
                said_obse__icontains=f'Pedido {pedido_numero}'
            )
            
            # Verificar estoque atual
            estoque_ok, estoque_atual = verificar_estoque_disponivel(
                item.iped_prod, 0, empresa_id, filial_id, request
            )
            
            status_itens.append({
                'produto': item.iped_prod,
                'quantidade_pedido': item.iped_quan,
                'saidas_criadas': len(saidas),
                'estoque_atual': estoque_atual,
                'saidas_revertidas': any('REVERTIDA' in s.said_obse for s in saidas)
            })
        
        return {
            'pedido_numero': pedido_numero,
            'itens': status_itens
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status do estoque do pedido: {e}")
        return {
            'erro': 'Erro ao obter status do estoque'
        }