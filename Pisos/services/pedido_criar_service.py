from decimal import Decimal
from django.db import transaction

from Pisos.models import Pedidospisos, Itenspedidospisos
from Pisos.services.utils_service import parse_decimal, arredondar
from Pisos.services.cliente_service import ClienteEnderecoService


class PedidoCriarService:
    def executar(self, *, banco, dados, itens):
        if not itens:
            raise ValueError("Itens do pedido são obrigatórios.")

        with transaction.atomic(using=banco):
            pedido = self._criar_pedido(
                banco=banco,
                dados=dados,
            )

            total = self._criar_itens(
                banco=banco,
                pedido=pedido,
                itens=itens,
            )

            pedido.pedi_tota = arredondar(total)
            pedido.save(using=banco, update_fields=["pedi_tota"])

            return pedido

    def _criar_pedido(self, *, banco, dados):
        ultimo = (
            Pedidospisos.objects.using(banco)
            .filter(
                pedi_empr=dados["pedi_empr"],
                pedi_fili=dados["pedi_fili"],
            )
            .order_by("-pedi_nume")
            .first()
        )

        proximo_numero = (ultimo.pedi_nume + 1) if ultimo else 1

        dados_pedido = dict(dados)
        dados_pedido.pop("itens_input", None)
        dados_pedido.pop("itens", None)
        dados_pedido.pop("parametros", None)

        dados_pedido["pedi_nume"] = proximo_numero
        dados_pedido["pedi_tota"] = Decimal("0.00")

        pedido = Pedidospisos.objects.using(banco).create(**dados_pedido)

        ClienteEnderecoService.preencher_pedido(
            banco=banco,
            pedido=pedido,
        )

        pedido.save(using=banco)

        return pedido

    def _criar_itens(self, *, banco, pedido, itens):
        total = Decimal("0.00")
        campos_permitidos = {field.name for field in Itenspedidospisos._meta.fields}

        for idx, item in enumerate(itens, start=1):
            dados_item = self._normalizar_item(item)

            dados_item = {
                chave: valor
                for chave, valor in dados_item.items()
                if chave in campos_permitidos
            }

            quantidade = parse_decimal(dados_item.get("item_quan"))
            valor_unitario = parse_decimal(dados_item.get("item_unit"))
            subtotal = arredondar(quantidade * valor_unitario)

            item_ambi = dados_item.get("item_ambi")
            if item_ambi in (None, "", 0, "0"):
                item_ambi = idx

            Itenspedidospisos.objects.using(banco).create(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
                item_nume=idx,
                item_ambi=item_ambi,
                item_suto=subtotal,
                **{
                    chave: valor
                    for chave, valor in dados_item.items()
                    if chave not in {
                        "item_empr",
                        "item_fili",
                        "item_pedi",
                        "item_nume",
                        "item_ambi",
                        "item_suto",
                    }
                },
            )

            total += subtotal

        return total

    def _normalizar_item(self, item):
        dados = dict(item)

        mapa = {
            "area_m2": "item_m2",
            "observacoes": "item_obse",
            "produto_nome": "item_prod_nome",
            "item_nome": "item_nome_ambi",
            "quebra": "item_queb",
        }

        for origem, destino in mapa.items():
            if origem in dados:
                dados[destino] = dados.pop(origem)

        dados_calc = dados.pop("dados_calculo", None) or {}

        if dados_calc:
            if not dados.get("item_caix"):
                dados["item_caix"] = dados_calc.get("caixas_necessarias")

            if not dados.get("item_quan"):
                caixas = parse_decimal(dados.get("item_caix"))
                pc_por_caixa = parse_decimal(dados_calc.get("pc_por_caixa"))
                m2_por_caixa = parse_decimal(dados_calc.get("m2_por_caixa"))

                if pc_por_caixa > 0:
                    dados["item_quan"] = pc_por_caixa * caixas
                elif m2_por_caixa > 0:
                    dados["item_quan"] = m2_por_caixa * caixas

        dados["item_m2"] = parse_decimal(dados.get("item_m2"))
        dados["item_quan"] = parse_decimal(dados.get("item_quan"))
        dados["item_unit"] = parse_decimal(dados.get("item_unit"))
        dados["item_desc"] = parse_decimal(dados.get("item_desc"))
        dados["item_queb"] = parse_decimal(dados.get("item_queb"))

        return dados