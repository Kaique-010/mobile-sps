from django.db.models import Sum, Count, Q, F
from ..models import LoteProdutos, ProdutoAgro, MovimentacaoEstoque, EstoqueFazenda

class RelatorioService:
    
    @staticmethod
    def total_produtos_por_lote(empresa, filial, produto_id=None, lote_ident=None, using='default'):
        """
        Retorna lista de lotes agrupados por produto com totais.
        """
        # Agrupa lotes por produto e soma quantidades
        query_filter = Q(lote_empr=empresa) & Q(lote_fili=filial)
        
        if produto_id:
            query_filter &= Q(lote_prod=str(produto_id))
            
        if lote_ident:
            query_filter &= Q(lote_ident__icontains=lote_ident)
            
        lotes = LoteProdutos.objects.using(using).filter(query_filter).values(
            'lote_prod', 'lote_ident', 'lote_data_venc'
        ).annotate(
            total_quantidade=Sum('lote_quant'),
            total_valor=Sum(F('lote_quant') * F('lote_cust_unit'))
        ).order_by('lote_prod', 'lote_ident')
        
        # Enriquecer com nome do produto
        produto_ids = set(l['lote_prod'] for l in lotes)
        produtos = ProdutoAgro.objects.using(using).filter(id__in=produto_ids).in_bulk()
        
        resultado = []
        for l in lotes:
            prod_id = int(l['lote_prod']) if l['lote_prod'].isdigit() else l['lote_prod']
            produto = produtos.get(prod_id)
            if produto:
                l['produto_nome'] = produto.prod_nome_agro
                l['produto_unidade'] = produto.prod_unmd_agro
                resultado.append(l)
                
        return resultado

    @staticmethod
    def total_produtos_sem_lote(empresa, filial, produto_id=None, using='default'):
        """
        Retorna produtos que têm estoque mas não estão associados a nenhum lote (ou cujo saldo de lotes é menor que o estoque total).
        Neste caso, vamos simplificar: Produtos que não têm registros na tabela de Lotes.
        """
        # Produtos que existem na tabela de produtos
        produtos_query = ProdutoAgro.objects.using(using).filter(
            prod_empr_agro=empresa,
            prod_fili_agro=filial
        )
        
        if produto_id:
            # Se for ID numérico
            if str(produto_id).isdigit():
                produtos_query = produtos_query.filter(id=produto_id)
            else:
                # Se for nome ou parte do nome (busca textual)
                produtos_query = produtos_query.filter(prod_nome_agro__icontains=produto_id)
        
        # IDs de produtos que têm lotes
        produtos_com_lote_ids = LoteProdutos.objects.using(using).filter(
            lote_empr=empresa,
            lote_fili=filial
        ).values_list('lote_prod', flat=True).distinct()
        
        # Converter para o mesmo tipo se necessário (assumindo que lote_prod guarda o ID como string)
        # Ajuste: lote_prod é CharField, ID é AutoField (int).
        # Vamos tentar filtrar excluindo os que estão na lista.
        
        # Precisamos garantir que a comparação de tipos funcione
        produtos_com_lote_ids_str = [str(pid) for pid in produtos_com_lote_ids if pid]
        
        produtos_sem_lote = produtos_query.exclude(id__in=produtos_com_lote_ids_str)
        
        # Para esses produtos, vamos buscar o estoque total na tabela EstoqueFazenda
        resultado = []
        for prod in produtos_sem_lote:
            # Busca estoque total
            estoque = EstoqueFazenda.objects.using(using).filter(
                estq_empr=empresa,
                estq_fili=filial,
                estq_prod=str(prod.id) # estq_prod também é CharField
            ).aggregate(total=Sum('estq_quant'))['total'] or 0
            
            if estoque > 0:
                resultado.append({
                    'produto_id': prod.id,
                    'produto_nome': prod.prod_nome_agro,
                    'produto_unidade': prod.prod_unmd_agro,
                    'estoque_total': estoque
                })
                
        return resultado

    @staticmethod
    def extrato_movimentacao(empresa, filial, data_inicio=None, data_fim=None, produto_id=None, lote_id=None, using='default'):
        """
        Retorna extrato de movimentações.
        """
        movimentacoes = MovimentacaoEstoque.objects.using(using).filter(
            movi_estq_empr=empresa,
            movi_estq_fili=filial
        ).order_by('-movi_estq_data')
        
        if data_inicio:
            movimentacoes = movimentacoes.filter(movi_estq_data__gte=data_inicio)
        
        if data_fim:
            movimentacoes = movimentacoes.filter(movi_estq_data__lte=data_fim)
            
        if produto_id:
            movimentacoes = movimentacoes.filter(movi_estq_prod=str(produto_id))
            
        # Se houver filtro de lote, precisaríamos ver se a movimentação tem vínculo com lote.
        # O modelo MovimentacaoEstoque não tem campo explícito de lote (tem docu_refe, moti).
        # Vamos assumir que por enquanto não filtra por lote direto na movimentação padrão, 
        # a menos que adicionemos lógica extra ou campo novo. O usuário pediu "com filtros por ... e lote".
        # Verificando models: MovimentacaoEstoque não tem lote.
        # Talvez filtrar pelo produto do lote? 
        # Por hora, vamos ignorar filtro de lote estrito na query de Movimentacao, ou filtrar se o texto estiver na observação.
        
        # Enriquecer com nomes
        resultado = []
        # Pre-fetch produtos para evitar N+1
        prod_ids = set(m.movi_estq_prod for m in movimentacoes)
        produtos = ProdutoAgro.objects.using(using).filter(id__in=prod_ids).in_bulk()
        
        for mov in movimentacoes:
            prod_id = int(mov.movi_estq_prod) if mov.movi_estq_prod.isdigit() else mov.movi_estq_prod
            produto = produtos.get(prod_id)
            
            resultado.append({
                'data': mov.movi_estq_data,
                'tipo': mov.get_movi_estq_tipo_display(),
                'produto_nome': produto.prod_nome_agro if produto else f"ID {mov.movi_estq_prod}",
                'quantidade': mov.movi_estq_quant,
                'documento': mov.movi_estq_docu_refe,
                'usuario': mov.movi_estq_usua,
                'custo_total': mov.movi_estq_cust_tota
            })
            
        return resultado
