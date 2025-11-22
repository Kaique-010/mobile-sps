from cnab400.tipos import Arquivo400
from cnab400.sicoob import HeaderArquivo, Detalhe, TrailerArquivo
from cnab400.retornos.sicoob import SicoobRetorno400


class SicoobCnab400Adapter:
    def gerar_remessa(self, banco_cfg, cedente, titulos):
        arquivo = Arquivo400()
        arquivo.header = HeaderArquivo(
            agencia=banco_cfg["agencia"],
            conta=banco_cfg["conta"],
            conta_dv=banco_cfg["dv"],
            nome_empresa=cedente["nome"],
        )
        for t in titulos:
            arquivo.incluir_detalhe(Detalhe(
                nosso_numero=t.titu_noss_nume,
                numero_documento=t.titu_titu,
                valor_titulo=float(t.titu_valo),
                data_vencimento=t.titu_venc,
                sacado_nome=f"Cliente {t.titu_clie}",
            ))
        arquivo.trailer = TrailerArquivo(total_registros=len(titulos))
        return arquivo.as_txt()

    def processar_retorno(self, caminho):
        retorno = SicoobRetorno400(caminho)
        dados = []
        for r in retorno.titulos:
            dados.append({
                "nosso_numero": r.nosso_numero,
                "valor_pago": r.valor_pago,
                "data_pagamento": r.data_pagamento,
            })
        return dados
