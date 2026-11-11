
# Pisos/services/rentabilidade_service.py

from decimal import Decimal, ROUND_HALF_UP

from Produtos.models import Tabelaprecos, Produtos
from Pisos.models import (
    Orcamentopisos,
    Itensorcapisos,
    Pedidospisos,
    Itenspedidospisos,
)

ZERO = Decimal("0")
CENTAVO = Decimal("0.01")
CEM = Decimal("100")


def dec(valor):
    return Decimal(str(valor or 0))


def moeda(valor):
    return dec(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


class RentabilidadeService:

    @classmethod
    def calcular_documento(cls, *, tipo, numero, banco):
        if tipo == "orcamento":
            documento = Orcamentopisos.objects.using(banco).filter(
                orca_nume=numero
            ).first()

            if not documento:
                raise ValueError("Orçamento não encontrado.")

            empresa = documento.orca_empr
            filial = documento.orca_fili
            desconto_geral = dec(documento.orca_desc)
            frete = dec(documento.orca_fret)

            itens = Itensorcapisos.objects.using(banco).filter(
                item_empr=empresa,
                item_fili=filial,
                item_orca=numero,
            )

        elif tipo == "pedido":
            documento = Pedidospisos.objects.using(banco).filter(
                pedi_nume=numero
            ).first()

            if not documento:
                raise ValueError("Pedido não encontrado.")

            empresa = documento.pedi_empr
            filial = documento.pedi_fili
            desconto_geral = dec(documento.pedi_desc)
            frete = dec(documento.pedi_fret)

            itens = Itenspedidospisos.objects.using(banco).filter(
                item_empr=empresa,
                item_fili=filial,
                item_pedi=numero,
            )

        else:
            raise ValueError("Tipo de documento inválido.")

        itens = list(itens)

        if not itens:
            raise ValueError("O documento não possui itens.")

        codigos = {str(item.item_prod) for item in itens}

        tabela_custos = Tabelaprecos.objects.using(banco).filter(
            tabe_empr=empresa,
            tabe_fili=filial,
            tabe_prod__in=codigos,
        )

        custos = {
            str(p.tabe_prod): p.tabe_cuge
            for p in tabela_custos
        }

        produtos = {
            str(p.prod_codi): p
            for p in Produtos.objects.using(banco).filter(
                prod_codi__in=codigos
            )
        }

        linhas = []
        subtotal = ZERO
        custo_total = ZERO

        for item in itens:
            codigo = str(item.item_prod)
            custo_unitario = custos.get(codigo)

            if custo_unitario is None:
                raise ValueError(
                    f"Produto {codigo} sem custo gerencial (tabe_cuge)."
                )

            produto = produtos.get(codigo)

            # A mesma regra de metragem/caixas usada pelo ERP.
            quantidade = dec(item.item_quan)
            metragem = dec(item.item_m2)
            caixas = dec(item.item_caix)
            m2_caixa = dec(
                getattr(produto, "prod_cera_m2cx", 0)
            )

            # Base de custo: m² efetivo vendido.
            # Quando há informação de caixas e conversão, usa as caixas.
            if caixas > 0 and m2_caixa > 0:
                quantidade_custo = caixas * m2_caixa
            elif metragem > 0:
                quantidade_custo = metragem
            else:
                quantidade_custo = quantidade

            custo = quantidade_custo * dec(custo_unitario)

            bruto = dec(item.item_suto)
            desconto_percentual = dec(item.item_desc)
            desconto_item = bruto * desconto_percentual / CEM

            receita = max(bruto - desconto_item, ZERO)

            linhas.append({
                "codigo": codigo,
                "descricao": (
                    getattr(item, "item_prod_nome", None)
                    or getattr(produto, "prod_nome", None)
                    or codigo
                ),
                "quantidade": quantidade,
                "metragem": metragem,
                "caixas": caixas,
                "venda_bruta": bruto,
                "desconto_item": desconto_item,
                "receita": receita,
                "custo_unitario": dec(custo_unitario),
                "custo": custo,
            })

            subtotal += receita
            custo_total += custo

        if desconto_geral < ZERO or frete < ZERO:
            raise ValueError("Desconto ou frete negativo no documento.")

        if desconto_geral > subtotal:
            raise ValueError(
                "O desconto geral supera o valor líquido dos itens."
            )

        resultado = []
        lucro_total = ZERO
        custo_frete_total = ZERO
        receita_total = ZERO
        custo_produtos_total = ZERO

        for linha in linhas:
            proporcao = (
                linha["receita"] / subtotal
                if subtotal > ZERO else ZERO
            )

            desconto_rateado = desconto_geral * proporcao
            frete_rateado = frete * proporcao
            receita_liquida = linha["receita"] - desconto_rateado

            lucro = (
                receita_liquida
                - linha["custo"]
                - frete_rateado
            )

            margem = (
                lucro / receita_liquida * CEM
                if receita_liquida > ZERO else ZERO
            )

            resultado.append({
                **linha,
                "desconto_rateado": moeda(desconto_rateado),
                "frete_rateado": moeda(frete_rateado),
                "receita_liquida": moeda(receita_liquida),
                "custo": moeda(linha["custo"]),
                "lucro": moeda(lucro),
                "margem_percentual": margem.quantize(
                    CENTAVO, rounding=ROUND_HALF_UP
                ),
            })

            receita_total += receita_liquida
            custo_produtos_total += linha["custo"]
            custo_frete_total += frete_rateado
            lucro_total += lucro

        margem_total = (
            lucro_total / receita_total * CEM
            if receita_total > ZERO else ZERO
        )

        return {
            "tipo": tipo,
            "numero": numero,
            "empresa": empresa,
            "filial": filial,
            "itens": resultado,
            "resumo": {
                "receita_liquida": moeda(receita_total),
                "custo_produtos": moeda(custo_produtos_total),
                "custo_frete": moeda(custo_frete_total),
                "lucro": moeda(lucro_total),
                "margem_percentual": margem_total.quantize(
                    CENTAVO, rounding=ROUND_HALF_UP
                ),
            },
        }
