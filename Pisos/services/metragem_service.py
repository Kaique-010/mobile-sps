from types import SimpleNamespace

from Produtos.models import Produtos
from Pisos.services.calculo_services import calcular_item
from Pisos.services.preco_service import get_preco_produto
from Pisos.services.utils_service import parse_decimal, arredondar


class MetragemProdutoService:
    def executar(self, *, banco, produto_id, tamanho_m2, percentual_quebra=0, condicao="0"):
        produto = Produtos.objects.using(banco).get(prod_codi=produto_id)

        calculo = calcular_item(
            SimpleNamespace(
                item_m2=tamanho_m2,
                item_queb=percentual_quebra,
                item_unit=0,
            ),
            produto=produto,
        )

        preco_origem = "tabela"

        try:
            preco_unitario = get_preco_produto(banco, produto_id, condicao)
        except Exception:
            preco_origem = "fallback_produto"
            preco_unitario = parse_decimal(getattr(produto, "prod_prec", 0))

        valor_total = arredondar(
            parse_decimal(calculo["metragem_real"]) * parse_decimal(preco_unitario)
        )

        unidade = self._normalizar_unidade(getattr(produto, "prod_unme", None))

        return {
            "produto_id": produto_id,
            "produto_nome": produto.prod_nome,
            "condicao_pagamento": "À Vista" if condicao == "0" else "A Prazo",
            "preco_unitario": preco_unitario,
            "valor_total": valor_total,
            "total": valor_total,
            "m2_por_caixa": parse_decimal(getattr(produto, "prod_cera_m2cx", 0)),
            "pc_por_caixa": parse_decimal(getattr(produto, "prod_cera_pccx", 0)),
            "metragem_total": calculo.get("metragem_real"),
            "metragem_real": calculo.get("metragem_real"),
            "metragem_com_perda": calculo.get("metragem_com_perda"),
            "caixas_necessarias": calculo.get("caixas_necessarias"),
            "preco_origem": preco_origem,
            "unidade_medida": unidade,
        }

    def _normalizar_unidade(self, unidade):
        if not unidade:
            return None

        unidade = str(unidade).strip().upper()

        if unidade in ["METRO QUADRADO", "M²", "M2", "M"]:
            return "M2"

        if unidade in ["PEÇA", "PÇ", "BARRA"]:
            return "PC"

        return unidade