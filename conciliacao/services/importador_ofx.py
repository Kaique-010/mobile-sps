
import os

from decimal import Decimal, InvalidOperation
from datetime import datetime
from io import BytesIO

from ofxparse import OfxParser

from django.db import connections, transaction
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class ImportarOFXService:

    def __init__(
        self,
        empresa,
        filial,
        codigo_banco,
        db_alias="default",
    ):
        self.empresa = empresa
        self.filial = filial
        self.codigo_banco = codigo_banco
        self.db_alias = db_alias

    def importar_upload(self, arquivo):
        conteudo = arquivo.read()
        return self._importar_conteudo(conteudo)

    def importar_caminho(self, caminho):
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
            # O arquivo contém UTF-8, embora declare USASCII.
            if b"ENCODING:USASCII" in conteudo:
                conteudo = conteudo.replace(
                    b"ENCODING:USASCII",
                    b"ENCODING:UTF-8",
                    1,
                )

            ofx = OfxParser.parse(BytesIO(conteudo))

        except Exception as exc:
            logger.exception(
                "Erro ao interpretar OFX. "
                "Empresa=%s Filial=%s Banco=%s",
                self.empresa,
                self.filial,
                self.codigo_banco,
            )

            raise ValidationError(
                "Não foi possível interpretar o OFX: {}".format(
                    str(exc)
                )
            ) from exc



        transacoes = []

        for conta in ofx.accounts:
            for transacao in conta.statement.transactions:

                try:
                    valor = Decimal(
                        str(transacao.amount)
                    ).quantize(Decimal("0.01"))
                except (InvalidOperation, TypeError):
                    raise ValidationError(
                        "O OFX contém uma transação com valor inválido."
                    )

                data = transacao.date
                data_operacao = (
                    data.date()
                    if isinstance(data, datetime)
                    else data
                )

                documento = (
                    getattr(transacao, "id", None) or ""
                )

                historico = (
                    getattr(transacao, "memo", None)
                    or getattr(transacao, "payee", None)
                    or ""
                )

                transacoes.append({
                    "documento": str(documento),
                    "data_operacao": data_operacao,
                    "tipo": self._normalizar_tipo(valor),
                    "valor": abs(valor),
                    "historico": str(historico)[:255],
                })

        if not transacoes:
            raise ValidationError(
                "Nenhuma transação encontrada no OFX."
            )

        return self._gravar_transacoes(transacoes)

    def _normalizar_tipo(self, valor):
        """
        E = Entrada / crédito
        S = Saída / débito
        """
        return "S" if valor < 0 else "E"

    def _criar_cabecalho(self, cursor):
        cursor.execute(
            """
            INSERT INTO conciliacaobancaria (
                conc_empr,
                conc_fili,
                conc_codi_banc,
                conc_data
            )
            VALUES (%s, %s, %s, CURRENT_DATE)
            RETURNING conc_nume
            """,
            [
                self.empresa,
                self.filial,
                self.codigo_banco,
            ],
        )

        return cursor.fetchone()[0]

    def _gravar_transacoes(self, transacoes):
        db = connections[self.db_alias]

        with transaction.atomic(using=self.db_alias):
            with db.cursor() as cursor:
                numero = self._criar_cabecalho(cursor)

                for linha, item in enumerate(
                    transacoes,
                    start=1,
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
                            numero,
                            self.empresa,
                            self.filial,
                            item["documento"],
                            item["data_operacao"],
                            item["tipo"],
                            item["valor"],
                            item["historico"],
                            linha,
                        ],
                    )

        return {
            "numero_conciliacao": numero,
            "empresa": self.empresa,
            "filial": self.filial,
            "total_importado": len(transacoes),
            "ja_importado": False,
        }