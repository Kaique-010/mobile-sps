from decimal import Decimal
from django.db import transaction
from ParametrosSps.models import Parametros
from core.utils import get_licenca_db_config
from Produtos.models import SaldoProduto, Movimentoestoque
from django.db.models import Max


class PedidosService:
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
            for item_data in itens_data:
                produto_codigo = item_data.get('iped_prod')
                quantidade = Decimal(str(item_data.get('iped_quan', 0)))
                
                if quantidade <= 0:
                    continue
                    
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
        quantidade = Decimal(str(item_data.get('iped_quan', 0)))
        valor_unitario = Decimal(str(item_data.get('iped_unit', 0)))
        
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
        next_doc_number = PedidosService._get_next_document_number(
            empresa=pedido.pedi_empr,
            filial=pedido.pedi_fili,
            entidade=pedido.pedi_forn,
            tipo="S",
            banco=banco
        )
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
            moes_docu=next_doc_number,  # Número sequencial do documento
            moes_mode="01",  # Modo de operação
            moes_item=1,  # Número do item
           
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
    def estornar_estoque_pedido(pedido, request):
        """
        Reverte a movimentação de estoque feita no pedido.
        Cria movimento de entrada e devolve quantidade ao saldo.
        """
        banco = get_licenca_db_config(request)
        
        # Obter empresa e filial dos headers
        empresa = int(request.headers.get('X-Empresa', 1))
        
        if not PedidosService.pedido_movimenta_estoque(banco, empresa):
            return "Parâmetro de movimentação de estoque desativado."

        for item in pedido.itens.all():
            PedidosService._estornar_item(pedido, item, banco)

        return "Baixa de estoque revertida com sucesso."

    @staticmethod
    def _estornar_item(pedido, item, banco):
        total_movimentacao = item.iped_unit * abs(Decimal(item.iped_quan))
        
        # Gerar número sequencial do documento para estorno
        next_doc_number = PedidosService._get_next_document_number(
            empresa=pedido.pedi_empr,
            filial=pedido.pedi_fili,
            entidade=pedido.pedi_forn,
            tipo="E",
            banco=banco
        )
        
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
            moes_docu=next_doc_number,  # Número sequencial do documento
            moes_mode="01",  # Modo de operação
            moes_item=1,  # Número do item
         
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
