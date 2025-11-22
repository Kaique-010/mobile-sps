from cnab400.tipos import Arquivo400
from cnab400.itau import HeaderArquivo, Detalhe, TrailerArquivo
from cnab400.retornos.itau import ItauRetorno400

class ItauCnab400Adapter:
    """
    CNAB 400 - REMESSA/RETORNO
    """

    def gerar_remessa(self, banco_cfg, cedente, titulos):
        arquivo = Arquivo400()

        # HEADER
        arquivo.header = HeaderArquivo(
            agencia=banco_cfg["agencia"],
            conta=banco_cfg["conta"],
            conta_dv=banco_cfg["dv"],
            nome_empresa=cedente["nome"],
        )

        # DETALHES
        for t in titulos:
            arquivo.incluir_detalhe(Detalhe(
                nosso_numero=t.titu_noss_nume,
                numero_documento=t.titu_titu,
                valor_titulo=float(t.titu_valo),
                data_vencimento=t.titu_venc,
                sacado_nome=f"Cliente {t.titu_clie}",
            ))

        # TRAILER
        arquivo.trailer = TrailerArquivo(total_registros=len(titulos))

        return arquivo.as_txt()

    def processar_retorno(self, caminho):
        retorno = ItauRetorno400(caminho)
        dados = []

        for r in retorno.titulos:
            dados.append({
                "nosso_numero": r.nosso_numero,
                "valor_pago": r.valor_pago,
                "data_pagamento": r.data_pagamento,
            })

        return dados
