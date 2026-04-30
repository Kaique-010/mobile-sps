from decimal import Decimal
from django.db import transaction

from Pisos.models import Orcamentopisos, Itensorcapisos
from Pisos.services.utils_service import parse_decimal, arredondar
from Pisos.services.cliente_service import ClienteEnderecoService


class OrcamentoCriarService:
    def executar(self, *, banco, dados, itens):
        if not itens:
            raise ValueError("Itens do orçamento são obrigatórios.")

        with transaction.atomic(using=banco):
            orcamento = self._criar_orcamento(
                banco=banco,
                dados=dados,
            )

            total = self._criar_itens(
                banco=banco,
                orcamento=orcamento,
                itens=itens,
            )

            orcamento.orca_tota = arredondar(total)
            orcamento.save(using=banco, update_fields=["orca_tota"])

            return orcamento

    def _criar_orcamento(self, *, banco, dados):
        ultimo = (
            Orcamentopisos.objects.using(banco)
            .filter(
                orca_empr=dados["orca_empr"],
                orca_fili=dados["orca_fili"],
            )
            .order_by("-orca_nume")
            .first()
        )

        proximo_numero = (ultimo.orca_nume + 1) if ultimo else 1

        dados_orcamento = dict(dados)
        dados_orcamento.pop("itens_input", None)
        dados_orcamento.pop("itens", None)
        dados_orcamento.pop("parametros", None)

        dados_orcamento["orca_nume"] = proximo_numero
        dados_orcamento["orca_tota"] = Decimal("0.00")
        
        orcamento = Orcamentopisos.objects.using(banco).create(**dados_orcamento)

        ClienteEnderecoService.preencher_orcamento(
            banco=banco,
            orcamento=orcamento,
        )

        orcamento.save(using=banco)

        return orcamento

    def _criar_itens(self, *, banco, orcamento, itens):
        total = Decimal("0.00")
        campos_permitidos = {field.name for field in Itensorcapisos._meta.fields}

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

            Itensorcapisos.objects.using(banco).create(
                item_empr=orcamento.orca_empr,
                item_fili=orcamento.orca_fili,
                item_orca=orcamento.orca_nume,
                item_nume=idx,
                item_ambi=dados_item.get("item_ambi") or 1,
                item_suto=subtotal,
                **{
                    chave: valor
                    for chave, valor in dados_item.items()
                    if chave not in {
                        "item_empr",
                        "item_fili",
                        "item_orca",
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
            "quebra": "item_queb",
            "item_nome": "item_nome_ambi",
        }

        for origem, destino in mapa.items():
            if origem in dados:
                dados[destino] = dados.pop(origem)

        dados.pop("produto_nome", None)

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

        if not dados.get("item_ambi"):
            dados["item_ambi"] = 1

        if not dados.get("item_nome_ambi"):
            dados["item_nome_ambi"] = "Padrão"

        dados["item_m2"] = parse_decimal(dados.get("item_m2"))
        dados["item_quan"] = parse_decimal(dados.get("item_quan"))
        dados["item_unit"] = parse_decimal(dados.get("item_unit"))
        dados["item_desc"] = parse_decimal(dados.get("item_desc"))
        dados["item_queb"] = parse_decimal(dados.get("item_queb"))

        return dados