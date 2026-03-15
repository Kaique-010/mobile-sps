from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from ..models import (
    EstoqueFazenda,
    HistoricoMovimentacao,
    MovimentacaoEstoque,
)
from .parametros import ParametroAgricolaService
from .lote_service import LoteService


class EstoqueDomainService:

    @staticmethod
    @transaction.atomic
    def processar_movimentacao(instance, using):

        empresa = instance.estq_empr
        filial = instance.estq_fili
        fazenda = instance.estq_faze
        produto = instance.estq_prod
        quantidade = instance.estq_quant
        tipo = instance.estq_tipo

        # 🔎 Verifica se controle de estoque está ativo
        controla_estoque = ParametroAgricolaService.get(
            empresa, filial, "controla_estoque", using=using
        )

        if not controla_estoque:
            return

        permite_negativo = ParametroAgricolaService.get(
            empresa, filial, "permite_estoque_negativo", using=using
        )

        controla_lote = ParametroAgricolaService.get(
            empresa, filial, "controla_lote", using=using
        )

        # 🔒 Lock pessimista para evitar concorrência
        estoque, _ = (
            EstoqueFazenda.objects
            .using(using)
            .select_for_update()
            .get_or_create(
                estq_empr=empresa,
                estq_fili=filial,
                estq_faze=fazenda,
                estq_prod=produto,
                defaults={"estq_quant": 0},
            )
        )

        # 📉 SAÍDA
        if tipo == "saida":

            if not permite_negativo and estoque.estq_quant < quantidade:
                raise ValidationError("Estoque insuficiente.")

            estoque.estq_quant = F("estq_quant") - quantidade

            if controla_lote:
                LoteService.registrar_movimentacao(
                    using=using,
                    empresa=empresa,
                    filial=filial,
                    fazenda=fazenda,
                    produto=produto,
                    quantidade=quantidade,
                    tipo=tipo,
                    permite_negativo=permite_negativo,
                )

        # 📈 ENTRADA
        elif tipo == "entrada":

            estoque.estq_quant = F("estq_quant") + quantidade

            if controla_lote:
                LoteService.registrar_movimentacao(
                    using=using,
                    empresa=empresa,
                    filial=filial,
                    fazenda=fazenda,
                    produto=produto,
                    quantidade=quantidade,
                    tipo=tipo,
                    permite_negativo=permite_negativo,
                )

        else:
            raise ValidationError("Tipo de movimentação inválido.")

        estoque.save(using=using)
        
        

        # 📝 Histórico (sempre registra)
        HistoricoMovimentacao.objects.using(using).create(
            estq_empr=empresa,
            estq_fili=filial,
            estq_faze=fazenda,
            estq_prod=produto,
            estq_quant=quantidade,
            estq_tipo=tipo,
            estq_data=instance.estq_data,
            estq_obse=instance.estq_obsw,
        )
        
        # 📝 Movimentação
        MovimentacaoEstoque.objects.using(using).create(
            estq_empr=empresa,
            estq_fili=filial,
            estq_faze=fazenda,
            estq_prod=produto,
            estq_quant=quantidade,
            estq_tipo=tipo,
            estq_data=instance.estq_data,
            estq_obse=instance.estq_obsw,
            movi_estq_usua=instance.estq_usua,
            movi_estq_docu_refe=instance.estq_docu_refe,
        )
