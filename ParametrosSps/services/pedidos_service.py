from decimal import Decimal
from django.db import transaction
from ParametrosSps.models import Parametros
from core.utils import get_licenca_db_config
from Produtos.models import SaldoProduto, Movimentoestoque
from Pedidos.models import PedidoVenda
from django.db.models import Max


class PedidosService:
    @staticmethod
    def pedido_tem_baixa(banco: str, pedido) -> bool:
        return Movimentoestoque.objects.using(banco).filter(
            moes_empr=pedido.pedi_empr,
            moes_fili=pedido.pedi_fili,
            moes_tipo="S",
            moes_seri="PEV",
            moes_mode="PV",
            moes_docu=int(pedido.pedi_nume),
        ).exists()

    @staticmethod
    def pedido_tem_estorno(banco: str, pedido) -> bool:
        return Movimentoestoque.objects.using(banco).filter(
            moes_empr=pedido.pedi_empr,
            moes_fili=pedido.pedi_fili,
            moes_tipo="E",
            moes_seri="PEV",
            moes_mode="PV",
            moes_docu=int(pedido.pedi_nume),
        ).exists()

    @staticmethod
    def pedido_movimenta_estoque(banco: str, empresa: int = 1, filial: int = 1) -> bool:
        """
        Verifica se o parâmetro de movimentação de estoque está ativo para a empresa fornecida.
        """
        try:
            parametro = Parametros.objects.using(banco).get(
               empresa_id=empresa
            )
            return parametro.pedido_movimenta_estoque == True
        except Parametros.DoesNotExist:
            return False

    @staticmethod
    def _get_next_document_number(empresa, filial, entidade, tipo, banco):
        """
        Gera o próximo número sequencial de documento para Movimentoestoque
        baseado em empresa, filial, entidade e tipo.
        """
        max_doc = Movimentoestoque.objects.using(banco).filter(
            moes_empr=empresa,
            moes_fili=filial,
            moes_enti=entidade,
            moes_tipo=tipo
        ).aggregate(Max('moes_docu'))['moes_docu__max']
        
        return (max_doc or 0) + 1

    # ============================================================
    # ↓ BAIXA ESTOQUE DO PEDIDO
    # ============================================================
    @staticmethod
    @transaction.atomic
    def baixa_estoque_pedido(pedido, itens_data, request):
        """
        Processa a baixa de estoque para um pedido
        Retorna formato compatível com o serializer
        """
        banco = get_licenca_db_config(request)
        
        # Obter empresa e filial dos headers
        empresa = int(request.headers.get('X-Empresa', 1))
        
        try:
            if not PedidosService.pedido_movimenta_estoque(banco, empresa):
                print("⚠️ [ESTOQUE] Movimentação de estoque desativada para esta empresa.")
                return {
                    'sucesso': True,
                    'processado': False,
                    'motivo': 'Movimentação de estoque desativada para esta empresa'
                }
            
            # Processar cada item
            for idx, item_data in enumerate(itens_data, start=1):
                produto_codigo = item_data.get('iped_prod')
                quantidade = Decimal(str(item_data.get('iped_quan', 0)))
                
                if quantidade <= 0:
                    continue
                    
                if 'iped_item' not in item_data or not item_data.get('iped_item'):
                    item_data = {**item_data, 'iped_item': idx}

                resultado_item = PedidosService._baixar_item_data(
                    pedido, item_data, banco
                )
                
                if not resultado_item.get('sucesso', True):
                    return resultado_item
            
            print(f"✅ [ESTOQUE] Estoque baixado com sucesso para pedido {pedido.pedi_nume}")
            return {
                'sucesso': True,
                'processado': True,
                'motivo': 'Estoque processado com sucesso'
            }
            
        except Exception as e:
            print(f"❌ [ESTOQUE] Erro ao processar estoque: {e}")
            return {
                'sucesso': False,
                'processado': False,
                'erro': str(e)
            }

    @staticmethod
    def _baixar_item_data(pedido, item_data, banco):
        """
        Baixa estoque baseado nos dados do item (item_data)
        """
        from Produtos.models import Produtos
        
        produto_codigo = item_data.get('iped_prod')
        item_numero = int(item_data.get('iped_item') or 1)
        quantidade = Decimal(str(item_data.get('iped_quan', 0)))
        valor_unitario = Decimal(str(item_data.get('iped_unit', 0)))

        ja_baixado = Movimentoestoque.objects.using(banco).filter(
            moes_empr=pedido.pedi_empr,
            moes_fili=pedido.pedi_fili,
            moes_tipo="S",
            moes_seri="PEV",
            moes_mode="PV",
            moes_docu=int(pedido.pedi_nume),
            moes_item=item_numero,
            moes_prod=str(produto_codigo),
        ).exists()
        if ja_baixado:
            return {'sucesso': True, 'processado': False, 'motivo': 'Item já baixado para este pedido'}
        
        produto = Produtos.objects.using(banco).filter(
            prod_codi=produto_codigo,
            prod_empr=pedido.pedi_empr
        ).first()
        
        if not produto:
            return {
                'sucesso': False,
                'erro': f"Produto {produto_codigo} não encontrado"
            }
            
        saldo = SaldoProduto.objects.using(banco).filter(
            produto_codigo=produto_codigo,
            empresa=pedido.pedi_empr,
            filial=pedido.pedi_fili
        ).first()
        
        if saldo and saldo.saldo_estoque < abs(quantidade):
            return {
                'sucesso': False,
                'erro': f"Produto {produto.prod_nome} sem estoque suficiente"
            }
            
        print(f"🔄 [ESTOQUE] Baixando item {produto_codigo} do pedido {pedido.pedi_nume}")
        total_movimentacao = valor_unitario * abs(quantidade)
        # Criar movimentação de estoque (SAÍDA)
        Movimentoestoque.objects.using(banco).create(
            moes_empr=pedido.pedi_empr,
            moes_fili=pedido.pedi_fili,
            moes_prod=item_data.get('iped_prod'),
            moes_quan=abs(quantidade),  # Quantidade sempre positiva para saída
            moes_unit=valor_unitario,
            moes_tota=total_movimentacao,
            moes_tipo="S",  # Saída de estoque
            moes_enti=pedido.pedi_forn,   
            moes_data=pedido.pedi_data,
            moes_seri="PEV",  # Série do pedido
            moes_docu=pedido.pedi_nume,  # Usa o número do pedido gerado
            moes_mode="PV",  # Modo de operação
            moes_item=item_numero,  # Número do item
           
        )

        # Atualizar saldo (DIMINUIR para saída)
        # Usar get_or_create para evitar duplicatas
        saldo, created = SaldoProduto.objects.using(banco).get_or_create(
            produto_codigo=produto_codigo,
            empresa=pedido.pedi_empr,
            filial=pedido.pedi_fili,
            defaults={'saldo_estoque': 0}
        )
        
        # Diminuir do estoque
        saldo.saldo_estoque -= abs(quantidade)
        saldo.save(using=banco)
        
        return {'sucesso': True}

    # ============================================================
    # ↑ REVERTE ESTOQUE (CANCELAMENTO) DO PEDIDO
    # ============================================================
    @staticmethod
    @transaction.atomic
    def estornar_estoque_pedido(pedido, request=None, banco: str | None = None):
        """
        Reverte a movimentação de estoque feita no pedido.
        Cria movimento de entrada e devolve quantidade ao saldo.
        """
        if banco is None:
            if request is None:
                raise ValueError("Informe request ou banco para estornar_estoque_pedido")
            banco = get_licenca_db_config(request)
        empresa = int(getattr(request, "headers", {}).get('X-Empresa', getattr(pedido, 'pedi_empr', 1)) if request is not None else getattr(pedido, 'pedi_empr', 1))
        
        try:
            if not PedidosService.pedido_movimenta_estoque(banco, empresa):
                print("⚠️ [ESTOQUE] Movimentação de estoque desativada para esta empresa.")
                return {
                    'sucesso': True,
                    'processado': False,
                    'motivo': 'Movimentação de estoque desativada para esta empresa'
                }

            if not PedidosService.pedido_tem_baixa(banco, pedido):
                return {
                    'sucesso': True,
                    'processado': False,
                    'motivo': 'Pedido sem baixa de estoque para estornar'
                }

            from Pedidos.models import Itenspedidovenda
            itens = Itenspedidovenda.objects.using(banco).filter(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_pedi=str(pedido.pedi_nume),
            ).order_by('iped_item')

            # Processar cada item
            for item in itens:
                resultado_item = PedidosService._estornar_item(pedido, item, banco)
                
                if not resultado_item.get('sucesso', True):
                    return resultado_item

            print(f"✅ [ESTOQUE] Estoque revertido com sucesso para pedido {pedido.pedi_nume}")
            return {
                'sucesso': True,
                'processado': True,
                'motivo': 'Estoque revertido com sucesso'
            }
            
        except Exception as e:
            print(f"❌ [ESTOQUE] Erro ao reverter estoque: {e}")
            return {
                'sucesso': False,
                'processado': False,
                'erro': str(e)
            }

    @staticmethod
    def _estornar_item(pedido, item, banco):
        """
        Estorna um item específico do pedido
        """
        try:
            teve_baixa = Movimentoestoque.objects.using(banco).filter(
                moes_empr=pedido.pedi_empr,
                moes_fili=pedido.pedi_fili,
                moes_tipo="S",
                moes_seri="PEV",
                moes_mode="PV",
                moes_docu=int(pedido.pedi_nume),
                moes_item=int(getattr(item, 'iped_item', 1) or 1),
                moes_prod=str(item.iped_prod),
            ).exists()
            if not teve_baixa:
                return {'sucesso': True, 'processado': False, 'motivo': 'Item sem baixa para estornar'}

            ja_estornado = Movimentoestoque.objects.using(banco).filter(
                moes_empr=pedido.pedi_empr,
                moes_fili=pedido.pedi_fili,
                moes_tipo="E",
                moes_seri="PEV",
                moes_mode="PV",
                moes_docu=int(pedido.pedi_nume),
                moes_item=int(getattr(item, 'iped_item', 1) or 1),
                moes_prod=str(item.iped_prod),
            ).exists()
            if ja_estornado:
                return {'sucesso': True, 'processado': False, 'motivo': 'Item já estornado para este pedido'}

            total_movimentacao = item.iped_unit * abs(Decimal(item.iped_quan))
            
            # Criar movimentação de estoque (ENTRADA para estorno)
            Movimentoestoque.objects.using(banco).create(
                moes_empr=pedido.pedi_empr,
                moes_fili=pedido.pedi_fili,
                moes_prod=item.iped_prod,
                moes_quan=abs(Decimal(item.iped_quan)),  # Quantidade sempre positiva para entrada
                moes_unit=item.iped_unit,
                moes_tota=total_movimentacao,
                moes_tipo="E",  # Entrada de estoque (estorno)
                moes_enti=pedido.pedi_forn,   
                moes_data=pedido.pedi_data,
                moes_seri="PEV",  # Série do pedido
                moes_docu=int(pedido.pedi_nume),
                moes_mode="PV",  # Modo de operação
                moes_item=int(getattr(item, 'iped_item', 1) or 1),
             
            )

            # Atualizar saldo (AUMENTAR para estorno)
            # Usar get_or_create para evitar duplicatas
            saldo, created = SaldoProduto.objects.using(banco).get_or_create(
                produto_codigo=item.iped_prod,
                empresa=pedido.pedi_empr,
                filial=pedido.pedi_fili,
                defaults={'saldo_estoque': 0}
            )
            
            # Somar de volta ao estoque
            saldo.saldo_estoque += abs(Decimal(item.iped_quan))
            saldo.save(using=banco, update_fields=["saldo_estoque"])
            
            return {'sucesso': True}
            
        except Exception as e:
            return {
                'sucesso': False,
                'erro': f"Erro ao estornar item {item.iped_prod}: {str(e)}"
            }


    @staticmethod
    def pedido_cancela_nao_exclui(banco: str, empresa: int = 1) -> bool:
        """
        Verifica se o parâmetro de cancelamento de pedido está ativo para a empresa fornecida.
        """
        try:
            parametro = Parametros.objects.using(banco).get(
               empresa_id=empresa
               
            )
            return parametro.pedido_cancelamento_habilitado == True
        except Parametros.DoesNotExist:
            return False


    @staticmethod
    def pedido_status_4_retorna_estoque(banco: str, empresa: int = 1, pedido: PedidoVenda = None):
        """
        Verifica se o Status do pedido está em 4 para retornar o estoque ao cancelar.
        """
        try:
            cancelado = PedidoVenda.objects.using(banco).get(
                pedi_nume=pedido.pedi_nume,
                pedi_empr=empresa,
                pedi_fili=pedido.pedi_fili,
                pedi_stat=4
            )
            if cancelado:
                return PedidosService.estornar_estoque_pedido(pedido, banco=banco)
        except PedidoVenda.DoesNotExist:
            return False
