from .sequencial_Service import SequencialService
from ..models import ProdutoAgro, SequencialControle, MovimentacaoEstoque
from django.db import transaction

class ProdutoAgroService:

    @staticmethod
    def criar_produto(*, data, using):

        if not data.get("prod_codi_agro"):
            numero = SequencialService.gerar(
                empresa=data["prod_empr_agro"],
                filial=data["prod_fili_agro"],
                tipo="PRODUTO",
                using=using,
            )

            data["prod_codi_agro"] = str(numero).zfill(6)

        return ProdutoAgro.objects.using(using).create(**data)




class MovimentacaoEstoqueService:
    @staticmethod
    def registrar_movimentacao(*, data, using):
        # Fallback para chaves com nomes incorretos ou corretos
        empresa = data.get("movi_estq_empr") or data.get("mov_esto_empr")
        filial = data.get("movi_estq_fili") or data.get("mov_esto_fili")
        
        if not data.get("id"):
            numero = SequencialService.gerar(
                empresa=empresa,
                filial=filial,
                tipo="MOVIMENTACAO_ESTOQUE",
                using=using,
            )

            data["id"] = str(numero).zfill(6)
        
        return MovimentacaoEstoque.objects.using(using).create(**data)
    
    @staticmethod
    def atualizar_movimentacao(*, data, using):
        movimentacao = MovimentacaoEstoque.objects.using(using).get(id=data["id"])
        movimentacao.__dict__.update(data)
        movimentacao.save()
        return movimentacao
    
    @staticmethod
    def excluir_movimentacao(*, id, using):
        movimentacao = MovimentacaoEstoque.objects.using(using).get(id=id)
        movimentacao.delete()
        return movimentacao
    
    @staticmethod
    def listar_movimentacoes(*, using):
        return MovimentacaoEstoque.objects.using(using).all().order_by("movi_estq_data")
    
    @staticmethod
    def listar_movimentacoes_por_filial(*, filial, using):
        return MovimentacaoEstoque.objects.using(using).filter(movi_estq_fili=filial).order_by("movi_estq_data")
    
    @staticmethod
    def listar_movimentacoes_por_produto(*, produto, using):
        return MovimentacaoEstoque.objects.using(using).filter(movi_estq_prod=produto).order_by("movi_estq_data")
    
    @staticmethod
    def listar_movimentacoes_por_tipo(*, tipo, using):
        return MovimentacaoEstoque.objects.using(using).filter(movi_estq_tipo=tipo).order_by("movi_estq_data")
    
    @staticmethod
    def listar_movimentacoes_por_empresa(*, empresa, using):
        return MovimentacaoEstoque.objects.using(using).filter(movi_estq_empr=empresa).order_by("movi_estq_data")

    @staticmethod
    def inumeras_movimentacoes_por_tipo(*, filial, using):
        movimentacoes = MovimentacaoEstoque.objects.using(using).filter(
            movi_estq_empr=filial.movi_estq_empr,
            movi_estq_fili=filial,
            movi_estq_faze=filial.movi_estq_faze,
            movi_estq_prod=filial.movi_estq_prod,
        ).order_by("movi_estq_data")
        
        movimentacoes_varias = []
        while movimentacoes:
            movimentacao = movimentacoes.pop(0)
            if movimentacao.movi_estq_tipo == "ENTRADA":
                movimentacoes_varias.append(movimentacao)
            elif movimentacao.movi_estq_tipo == "SAIDA":
                movimentacoes_varias.append(movimentacao)
        return movimentacoes_varias