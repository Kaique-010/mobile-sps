from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from conciliacao.models import (
    ItemExtrato,
    ConciliacaoHist,
)

from contas_a_receber.models import Titulosreceber
from contas_a_receber.services import (
    baixar_titulo_receber,
    excluir_baixa_receber,
)

from contas_a_pagar.models import Titulospagar
from contas_a_pagar.services import (
    baixar_titulo_pagar,
    excluir_baixa_titulo,
)

from Lancamentos_Bancarios.utils import get_next_lcto_number
from Lancamentos_Bancarios.models import Lctobancario
import logging

logger = logging.getLogger(__name__)

# Origens que contam como "vínculo válido" para efeito de saldo
# disponível e status de conciliação do item de extrato.
ORIGENS_VINCULO = ["PAGAR", "RECEBER", "AVULSO"]


class ConciliarExtratoService:

    def __init__(self, *, banco, empresa, filial, numero):
        self.banco = banco
        self.empresa = empresa
        self.filial = filial
        self.numero = numero

    # ---------------------------------------------------------
    # VALIDAÇÕES
    # ---------------------------------------------------------

    @staticmethod
    def _validar_valor(valor):
        try:
            valor = Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Valor inválido.")

        if not valor.is_finite() or valor <= 0:
            raise ValidationError(
                "O valor deve ser maior que zero."
            )

        return valor

    @staticmethod
    def _valor_extrato(valor):
        """
        O extrato pode ter valores negativos (débitos).
        Para controle de saldo, considera o valor absoluto.
        """
        try:
            valor = abs(Decimal(str(valor)))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError(
                "O valor do item de extrato é inválido."
            )

        if not valor.is_finite() or valor <= 0:
            raise ValidationError(
                "O item de extrato precisa ter valor diferente de zero."
            )

        return valor

    def _buscar_item_extrato(self, item_extrato_id):
        item = (
            ItemExtrato.objects
            .using(self.banco)
            .select_for_update()
            .filter(
                id=item_extrato_id,
                nume=self.numero,
                empresa=self.empresa,
                filial=self.filial,
            )
            .first()
        )

        if not item:
            raise ValidationError(
                "Item do extrato não encontrado."
            )

        return item

    def _total_ja_vinculado(self, item):
        """
        Soma os vínculos registrados no histórico
        para este item de extrato. Inclui PAGAR, RECEBER
        e AVULSO -- os três representam valor já baixado
        contra o item do extrato.
        """
        resultado = (
            ConciliacaoHist.objects
            .using(self.banco)
            .filter(
                nume=self.numero,
                empresa=self.empresa,
                filial=self.filial,
                item_extrato=item.id,
                origem__in=ORIGENS_VINCULO,
            )
            .aggregate(total=Sum("valor"))
        )

        return resultado["total"] or Decimal("0.00")

    def _validar_saldo_disponivel(self, item, valor_novo):
        valor_extrato = self._valor_extrato(item.valor)
        total_vinculado = self._total_ja_vinculado(item)

        saldo_disponivel = valor_extrato - total_vinculado

        if saldo_disponivel < 0:
            raise ValidationError(
                "Este item possui vínculos acima do valor do extrato."
            )

        if valor_novo > saldo_disponivel:
            raise ValidationError(
                "O valor informado ultrapassa o saldo disponível. "
                "Saldo disponível: R$ {:.2f}".format(
                    saldo_disponivel
                )
            )

        return saldo_disponivel

    def _recalcular_selecionado(self, item):
        """
        Recalcula o campo `selecionado` do item de extrato com base
        no total atualmente vinculado -- em QUALQUER direção.

        Diferente da versão antiga (que só ligava `selecionado=True`
        e nunca desligava), esta função também REABRE o item quando
        um vínculo é desfeito e o total cai abaixo do valor do extrato.
        Isso é essencial para o fluxo de "desvincular".
        """
        valor_extrato = self._valor_extrato(item.valor)
        total_vinculado = self._total_ja_vinculado(item)

        novo_selecionado = total_vinculado >= valor_extrato

        atualizado = (
            ItemExtrato.objects
            .using(self.banco)
            .filter(
                id=item.id,
                nume=self.numero,
                empresa=self.empresa,
                filial=self.filial,
            )
            .update(selecionado=novo_selecionado)
        )

        logger.info(
            "CONCILIACAO STATUS | item=%s | extrato=%s | vinculado=%s | "
            "saldo=%s | selecionado=%s | registros_atualizados=%s",
            item.id,
            valor_extrato,
            total_vinculado,
            valor_extrato - total_vinculado,
            novo_selecionado,
            atualizado,
        )

    # Mantido por compatibilidade com quem já chamava o nome antigo.
    def _atualizar_selecionado_se_completo(self, item):
        self._recalcular_selecionado(item)

    @staticmethod
    def _validar_titulos(titulos):
        if not isinstance(titulos, list) or not titulos:
            raise ValidationError(
                "Selecione ao menos um título."
            )

        for dados in titulos:
            if not isinstance(dados, dict):
                raise ValidationError(
                    "Os dados de um dos títulos são inválidos."
                )

            if "valor" not in dados:
                raise ValidationError(
                    "Informe o valor de cada título."
                )

    @staticmethod
    def _validar_forma_pagamento(forma):
        """
        Não converte automaticamente códigos de dois
        caracteres para os campos legados de um caractere.

        O mapeamento deve seguir a regra real do ERP.
        """
        if forma is None or not str(forma).strip():
            raise ValidationError(
                "Informe a forma de pagamento."
            )

        return str(forma).strip()

    # ---------------------------------------------------------
    # RECEBIMENTOS
    # ---------------------------------------------------------

    def conciliar_recebimentos(
        self,
        *,
        item_extrato_id: int,
        titulos: list[dict],
        data_recebimento,
        forma_recebimento: str,
    ):
        self._validar_titulos(titulos)

        forma_recebimento = self._validar_forma_pagamento(
            forma_recebimento
        )

        with transaction.atomic(using=self.banco):
            item = self._buscar_item_extrato(
                item_extrato_id
            )

            total_solicitado = sum(
                (
                    self._validar_valor(dados["valor"])
                    for dados in titulos
                ),
                Decimal("0.00"),
            )

            self._validar_saldo_disponivel(
                item,
                total_solicitado,
            )

            total_vinculos = Decimal("0.00")
            resultados = []

            for dados_titulo in titulos:
                valor = self._validar_valor(
                    dados_titulo["valor"]
                )

                titulo = (
                    Titulosreceber.objects
                    .using(self.banco)
                    .select_for_update()
                    .filter(
                        titu_empr=self.empresa,
                        titu_fili=self.filial,
                        titu_clie=dados_titulo["cliente"],
                        titu_titu=dados_titulo["titulo"],
                        titu_seri=dados_titulo["serie"],
                        titu_parc=dados_titulo["parcela"],
                    )
                    .first()
                )

                if not titulo:
                    raise ValidationError(
                        "Título a receber não encontrado."
                    )

                baixa, lancamento = baixar_titulo_receber(
                    titulo,
                    banco=self.banco,
                    dados={
                        "valor_recebido": valor,
                        "data_recebimento": data_recebimento,
                        "forma_pagamento": forma_recebimento,
                    },
                )

                ConciliacaoHist.objects.using(
                    self.banco
                ).create(
                    nume=self.numero,
                    empresa=self.empresa,
                    filial=self.filial,
                    item_extrato=item.id,
                    origem="RECEBER",
                    titulo=titulo.titu_titu,
                    entidade=titulo.titu_clie,
                    serie=titulo.titu_seri,
                    parcela=titulo.titu_parc,
                    banco=None,
                    controle_bancario=(
                        lancamento.laba_ctrl
                        if lancamento
                        else None
                    ),
                    baixa_pagar_sequ=None,
                    baixa_receber_sequ=baixa.bare_sequ,
                    valor=valor,
                )

                total_vinculos += valor

                resultados.append({
                    "titulo": titulo.titu_titu,
                    "baixa_sequ": baixa.bare_sequ,
                    "valor": valor,
                })

            self._recalcular_selecionado(item)

            return {
                "item_extrato_id": item.id,
                "total_vinculado": total_vinculos,
                "baixas": resultados,
            }

    # ---------------------------------------------------------
    # PAGAMENTOS
    # ---------------------------------------------------------

    def conciliar_pagamentos(
        self,
        *,
        item_extrato_id: int,
        titulos: list[dict],
        data_pagamento,
        forma_pagamento: str,
    ):
        self._validar_titulos(titulos)

        forma_pagamento = self._validar_forma_pagamento(
            forma_pagamento
        )

        with transaction.atomic(using=self.banco):
            item = self._buscar_item_extrato(
                item_extrato_id
            )

            total_solicitado = sum(
                (
                    self._validar_valor(dados["valor"])
                    for dados in titulos
                ),
                Decimal("0.00"),
            )

            self._validar_saldo_disponivel(
                item,
                total_solicitado,
            )

            total_vinculos = Decimal("0.00")
            resultados = []

            for dados_titulo in titulos:
                valor = self._validar_valor(
                    dados_titulo["valor"]
                )

                titulo = (
                    Titulospagar.objects
                    .using(self.banco)
                    .select_for_update()
                    .filter(
                        titu_empr=self.empresa,
                        titu_fili=self.filial,
                        titu_forn=dados_titulo["fornecedor"],
                        titu_titu=dados_titulo["titulo"],
                        titu_seri=dados_titulo["serie"],
                        titu_parc=dados_titulo["parcela"],
                    )
                    .first()
                )

                if not titulo:
                    raise ValidationError(
                        "Título a pagar não encontrado."
                    )

                baixa, lancamento = baixar_titulo_pagar(
                    titulo,
                    banco=self.banco,
                    dados={
                        "valor_pago": valor,
                        "data_pagamento": data_pagamento,
                        "forma_pagamento": forma_pagamento,
                    },
                )

                ConciliacaoHist.objects.using(
                    self.banco
                ).create(
                    nume=self.numero,
                    empresa=self.empresa,
                    filial=self.filial,
                    item_extrato=item.id,
                    origem="PAGAR",
                    titulo=titulo.titu_titu,
                    entidade=titulo.titu_forn,
                    serie=titulo.titu_seri,
                    parcela=titulo.titu_parc,
                    banco=None,
                    controle_bancario=(
                        lancamento.laba_ctrl
                        if lancamento
                        else None
                    ),
                    baixa_pagar_sequ=baixa.bapa_sequ,
                    baixa_receber_sequ=None,
                    valor=valor,
                )

                total_vinculos += valor

                resultados.append({
                    "titulo": titulo.titu_titu,
                    "baixa_sequ": baixa.bapa_sequ,
                    "valor": valor,
                })

            self._recalcular_selecionado(item)

            return {
                "item_extrato_id": item.id,
                "total_vinculado": total_vinculos,
                "baixas": resultados,
            }

    def _status_conciliacao(self, item):
        valor_extrato = self._valor_extrato(item.valor)
        total_vinculado = self._total_ja_vinculado(item)

        if total_vinculado <= Decimal("0.00"):
            return {
                "status": "NAO_CONCILIADO",
                "total_vinculado": Decimal("0.00"),
                "saldo": valor_extrato,
            }

        if total_vinculado < valor_extrato:
            return {
                "status": "PARCIAL",
                "total_vinculado": total_vinculado,
                "saldo": valor_extrato - total_vinculado,
            }

        return {
            "status": "CONCILIADO",
            "total_vinculado": total_vinculado,
            "saldo": Decimal("0.00"),
        }

    def listar_vinculos(self, item_extrato_id):
        """
        Retorna os registros de ConciliacaoHist de um item, pra
        alimentar o modal de detalhe ("o que foi vinculado aqui").
        """
        item = self._buscar_item_extrato(item_extrato_id)

        vinculos = list(
            ConciliacaoHist.objects
            .using(self.banco)
            .filter(
                nume=self.numero,
                empresa=self.empresa,
                filial=self.filial,
                item_extrato=item.id,
            )
            .order_by("data")
        )

        return item, vinculos

    def lancar_avulso(
        self,
        *,
        item_extrato_id,
        valor,
        data_lancamento,
        historico,
        banco,
    ):
        """
        Cria um lançamento bancário sem vínculo com
        título a pagar ou receber.

        O lançamento fica registrado também no
        ConciliacaoHist como AVULSO.
        """

        valor = self._validar_valor(valor)

        if not historico or not str(historico).strip():
            raise ValidationError(
                "Informe o histórico do lançamento."
            )

        try:
            banco = int(banco)
        except (TypeError, ValueError):
            raise ValidationError(
                "Banco/conta inválido."
            )

        with transaction.atomic(using=self.banco):

            item = self._buscar_item_extrato(
                item_extrato_id
            )

            # --------------------------------------------------
            # SALDO DISPONÍVEL
            # --------------------------------------------------

            self._validar_saldo_disponivel(
                item,
                valor,
            )

            # --------------------------------------------------
            # CONTROLE DO LANÇAMENTO
            # --------------------------------------------------

            ctrl = get_next_lcto_number(
                self.empresa,
                self.filial,
                self.banco,
            )

            # --------------------------------------------------
            # DÉBITO / CRÉDITO
            # --------------------------------------------------

            dbcr = (
                "D"
                if item.tipo == "S"
                else "C"
            )

            # --------------------------------------------------
            # LANÇAMENTO BANCÁRIO
            # --------------------------------------------------

            lancamento = (
                Lctobancario.objects
                .using(self.banco)
                .create(
                    laba_ctrl=ctrl,
                    laba_empr=self.empresa,
                    laba_fili=self.filial,
                    laba_banc=banco,
                    laba_data=data_lancamento,
                    laba_valo=valor,
                    laba_hist=historico.strip(),
                    laba_dbcr=dbcr,
                )
            )

            # --------------------------------------------------
            # HISTÓRICO DA CONCILIAÇÃO
            # --------------------------------------------------

            ConciliacaoHist.objects.using(
                self.banco
            ).create(
                nume=self.numero,
                empresa=self.empresa,
                filial=self.filial,
                item_extrato=item.id,
                origem="AVULSO",

                # Não existe título
                titulo=None,
                entidade=None,
                serie=None,
                parcela=None,

                banco=banco,
                controle_bancario=lancamento.laba_ctrl,

                baixa_pagar_sequ=None,
                baixa_receber_sequ=None,

                valor=valor,
            )

            # --------------------------------------------------
            # ATUALIZA STATUS
            # --------------------------------------------------

            self._recalcular_selecionado(item)

            logger.info(
                "CONCILIACAO AVULSA | "
                "item=%s | valor=%s | banco=%s | ctrl=%s",
                item.id,
                valor,
                banco,
                lancamento.laba_ctrl,
            )

            return lancamento

    # ---------------------------------------------------------
    # DESVINCULAR
    # ---------------------------------------------------------

    def desvincular(self, *, hist_id):
        """
        Desfaz um vínculo de conciliação, qualquer que seja a origem:

          AVULSO  -> apaga o Lctobancario criado e o histórico
          PAGAR   -> chama excluir_baixa_titulo (estorna adiantamento
                     se houver, apaga Lctobancario vinculado, apaga a
                     baixa e recalcula titu_aber do título)
          RECEBER -> equivalente via excluir_baixa_receber

        Em todos os casos, recalcula `selecionado` do item de extrato
        no final -- reabrindo-o se o total vinculado cair abaixo do
        valor do extrato.

        Retorna o item de extrato afetado.
        """

        with transaction.atomic(using=self.banco):

            hist = (
                ConciliacaoHist.objects
                .using(self.banco)
                .select_for_update()
                .filter(
                    id=hist_id,
                    nume=self.numero,
                    empresa=self.empresa,
                    filial=self.filial,
                )
                .first()
            )

            if not hist:
                raise ValidationError(
                    "Vínculo não encontrado ou já foi desfeito."
                )

            item = self._buscar_item_extrato(hist.item_extrato)

            if hist.origem == "AVULSO":

                if hist.controle_bancario:
                    Lctobancario.objects.using(self.banco).filter(
                        laba_ctrl=hist.controle_bancario,
                        laba_empr=self.empresa,
                        laba_fili=self.filial,
                    ).delete()

                hist.delete()

            elif hist.origem == "PAGAR":

                if not hist.baixa_pagar_sequ:
                    raise ValidationError(
                        "Vínculo de pagamento sem baixa associada."
                    )

                titulo = (
                    Titulospagar.objects
                    .using(self.banco)
                    .select_for_update()
                    .filter(
                        titu_empr=self.empresa,
                        titu_fili=self.filial,
                        titu_forn=hist.entidade,
                        titu_titu=hist.titulo,
                        titu_seri=hist.serie,
                        titu_parc=hist.parcela,
                    )
                    .first()
                )

                if not titulo:
                    raise ValidationError(
                        "Título a pagar não encontrado para desvincular."
                    )

                excluir_baixa_titulo(
                    titulo,
                    hist.baixa_pagar_sequ,
                    banco=self.banco,
                )

                hist.delete()

            elif hist.origem == "RECEBER":

                if not hist.baixa_receber_sequ:
                    raise ValidationError(
                        "Vínculo de recebimento sem baixa associada."
                    )

                titulo = (
                    Titulosreceber.objects
                    .using(self.banco)
                    .select_for_update()
                    .filter(
                        titu_empr=self.empresa,
                        titu_fili=self.filial,
                        titu_clie=hist.entidade,
                        titu_titu=hist.titulo,
                        titu_seri=hist.serie,
                        titu_parc=hist.parcela,
                    )
                    .first()
                )

                if not titulo:
                    raise ValidationError(
                        "Título a receber não encontrado para desvincular."
                    )

                excluir_baixa_receber(
                    titulo,
                    hist.baixa_receber_sequ,
                    banco=self.banco,
                )

                hist.delete()

            else:
                raise ValidationError(
                    "Origem de vínculo desconhecida: {}".format(
                        hist.origem
                    )
                )

            self._recalcular_selecionado(item)

            logger.info(
                "CONCILIACAO DESVINCULADA | item=%s | hist_id=%s | origem=%s",
                item.id,
                hist_id,
                hist.origem,
            )

            return item