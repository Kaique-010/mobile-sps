from collections import defaultdict
from decimal import Decimal

from ..grades_models import Grade

from django.db.models import Q


class GradeService:
    
    def __init__(self, banco, empresa_id, filial_id):
        self.banco = banco
        self.empresa_id = empresa_id
        self.filial_id = filial_id
        
        
    def queryset(self):
        """
        Retorna um queryset de grades para a empresa e filial especificadas.
        """
        return Grade.objects.using(self.banco).filter(
            grad_empr=self.empresa_id,
            grad_fili=self.filial_id
        )
    
    def listar_por_produto(self, prod_codi):
        """
        Retorna uma lista de grades para um produto específico.
        """
        return self.queryset().filter(
            grad_prod=prod_codi
        ).order_by('grad_item')
    
    def buscar_item(self, prod_codi, item):
        """
        Retorna uma grade específica para um produto e item.
        """
        return self.queryset().filter(
            grad_prod=prod_codi,
            grad_item=item
        ).first()
    
    
    def produto_tem_grade(self, prod_codi):
        """
        Retorna se um produto tem grades associadas.
        """
        return self.queryset().filter(
            grad_prod=prod_codi
        ).exists()
    
    def listar_produtos_com_grade(self, prod_codi):
        """
        Retorna uma lista de produtos que tem grades associadas.
        """
        return self.queryset().filter(grad_prod__in=prod_codi).order_by('grad_prod', 'grad_item')

    def agrupar_por_produto(self, produtos_ids):
        """
        Retorna {str(prod_codi): [variações]} para vários produtos
        em uma única consulta. Produtos sem grade ficam fora do dict.
        """
        produtos_ids = list(produtos_ids)

        if not produtos_ids:
            return {}

        agrupado = defaultdict(list)

        for grade in self.listar_produtos_com_grade(produtos_ids):
            agrupado[str(grade.grad_prod)].append({
                "item_id": grade.grad_item,
                "descricao": grade.grad_desc,
                "tamanho": grade.grad_nume,
                "cor": grade.grad_cor,
                "saldo": grade.grad_sald or Decimal("0"),
                "quantidade": 0,
            })

        return dict(agrupado)

    def listar_para_etiquetas(self, produto_id):
        """
        Retorna as variações com os dados necessários
        para montar o modal de impressão.
        """
        grades = self.listar_por_produto(produto_id)

        return [
            {
                "produto_id": grade.grad_prod,
                "item_id": grade.grad_item,
                "descricao": grade.grad_desc,
                "tamanho": grade.grad_nume,
                "cor": grade.grad_cor,
                "saldo": grade.grad_sald or Decimal("0"),
                "quantidade": 0,
            }
            for grade in grades
        ]

    def obter_grade_por_produto(self, produto_id):
        """
        Retorna a grade organizada por tamanho e cor.
        """
        grades = self.listar_por_produto(produto_id)

        return {
            "produto_id": produto_id,
            "tem_grade": grades.exists(),
            "variacoes": [
                {
                    "item_id": grade.grad_item,
                    "descricao": grade.grad_desc,
                    "tamanho": grade.grad_nume,
                    "cor": grade.grad_cor,
                    "saldo": grade.grad_sald or Decimal("0"),
                }
                for grade in grades
            ],
        }

    def validar_itens(self, produto_id, itens):
        """
        Valida se os itens enviados pertencem à grade
        do produto, considerando empresa e filial.

        itens: lista de grad_item.
        """
        itens_validos = set(
            self.listar_por_produto(produto_id)
            .filter(grad_item__in=itens)
            .values_list("grad_item", flat=True)
        )

        return {
            "validos": itens_validos,
            "invalidos": set(itens) - itens_validos,
        }