
import os

from decimal import Decimal
from datetime import datetime
from io import BytesIO

from ofxparse import OfxParser

from django.db import connection, transaction
from django.core.exceptions import ValidationError


class ImportarOFXService:

    def __init__(
        self,
        empresa,
        filial,
        codigo_banco,
        numero_conciliacao,
    ):
        self.empresa = empresa
        self.filial = filial
        self.codigo_banco = codigo_banco
        self.numero_conciliacao = numero_conciliacao

    def importar_upload(self, arquivo):
        """
        Recebe um arquivo enviado pelo request.FILES.
        """
        conteudo = arquivo.read()

        return self._importar_conteudo(conteudo)

    def importar_caminho(self, caminho):
        """
        Recebe o caminho de um arquivo já salvo no servidor.
        """
        if not os.path.isfile(caminho):
            raise ValidationError(
                "Arquivo OFX não encontrado."
            )

        with open(caminho, "rb") as arquivo:
            conteudo = arquivo.read()

        return self._importar_conteudo(conteudo)

    def _importar_conteudo(self, conteudo):
        if not conteudo:
            raise ValidationError(
                "O arquivo OFX está vazio."
            )

        try:
            ofx = OfxParser.parse(
                BytesIO(conteudo)
            )
        except Exception as exc:
            raise ValidationError(
                "Não foi possível interpretar o OFX."
            ) from exc

        transacoes = []

        for conta in ofx.accounts:
            for transacao in conta.statement.transactions:

                valor = Decimal(
                    str(transacao.amount)
                ).quantize(
                    Decimal("0.01")
                )

                data_operacao = (
                    transacao.date.date()
                    if isinstance(
                        transacao.date,
                        datetime
                    )
                    else transacao.date
                )

                tipo = self._normalizar_tipo(
                    valor
                )

                documento = (
                    getattr(
                        transacao,
                        "id",
                        None
                    )
                    or ""
                )

                historico = (
                    getattr(
                        transacao,
                        "memo",
                        None
                    )
                    or getattr(
                        transacao,
                        "payee",
                        None
                    )
                    or ""
                )

                transacoes.append({
                    "documento": str(documento),
                    "data_operacao": data_operacao,
                    "tipo": tipo,
                    "valor": abs(valor),
                    "historico": str(historico),
                })

        if not transacoes:
            raise ValidationError(
                "Nenhuma transação encontrada no OFX."
            )

        return self._gravar_transacoes(
            transacoes
        )

    def _normalizar_tipo(self, valor):
        """
        Convenção provisória:
        D = débito
        C = crédito
        """
        return "D" if valor < 0 else "C"

    @transaction.atomic
    def _gravar_transacoes(self, transacoes):

        self._criar_cabecalho()

        total = 0

        with connection.cursor() as cursor:

            for linha, item in enumerate(
                transacoes,
                start=1
            ):
                cursor.execute(
                    """
                    INSERT INTO conciliacao_itens_extrato (
                        conc_extr_nume,
                        conc_extr_empr,
                        conc_extr_fili,
                        conc_extr_docu,
                        conc_extr_data_op,
                        conc_extr_tipo,
                        conc_extr_valo,
                        conc_extr_hist,
                        conc_extr_exis,
                        conc_extr_sele,
                        conc_extr_linh
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, FALSE, FALSE, %s
                    )
                    """,
                    [
                        self.numero_conciliacao,
                        self.empresa,
                        self.filial,
                        item["documento"],
                        item["data_operacao"],
                        item["tipo"],
                        item["valor"],
                        item["historico"],
                        linha,
                    ]
                )

                total += 1

        return {
            "numero_conciliacao": (
                self.numero_conciliacao
            ),
            "total_importado": total,
        }

    def _criar_cabecalho(self):

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO conciliacaobancaria (
                    conc_nume,
                    conc_empr,
                    conc_fili,
                    conc_codi_banc,
                    conc_data
                )
                VALUES (%s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT (
                    conc_nume,
                    conc_empr,
                    conc_fili
                )
                DO NOTHING
                """,
                [
                    self.numero_conciliacao,
                    self.empresa,
                    self.filial,
                    self.codigo_banco,
                ]
            )