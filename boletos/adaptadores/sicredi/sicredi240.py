from cnab240.tipos import Arquivo
from cnab240.remessa.sicredi import Registro0, Registro1, Registro3P, Registro3Q
from cnab240.retornos.sicredi import SicrediRetorno


class SicrediCnab240Adapter:
    def gerar_remessa(self, banco_cfg, cedente, titulos):
        arquivo = Arquivo()
        documento = cedente["documento"].replace(".", "").replace("/", "").replace("-", "")
        arquivo.header = Registro0(
            codigo_banco=banco_cfg["codigo_banco"],
            tipo_inscricao="2",
            numero_inscricao=documento,
            agencia=banco_cfg["agencia"],
            conta=banco_cfg["conta"],
            dv_conta=banco_cfg["dv"],
            nome_empresa=cedente["nome"],
        )
        lote = arquivo.incluir_lote(Registro1(
            operacao="1",
            servico="01",
            agencia=banco_cfg["agencia"],
            conta=banco_cfg["conta"],
            dv_conta=banco_cfg["dv"],
            nome_empresa=cedente["nome"],
        ))
        for t in titulos:
            lote.incluir_registro(Registro3P(
                nosso_numero=t.titu_noss_nume,
                carteira=banco_cfg.get("carteira", "01"),
                numero_documento=t.titu_titu,
                data_vencimento=t.titu_venc.strftime("%d%m%Y"),
                valor_titulo=int(t.titu_valo * 100),
                especie="02",
            ))
            sacado = {
                "nome": f"Cliente {t.titu_clie}",
                "endereco": "",
                "cep": "00000000",
                "cidade": "",
                "uf": "",
            }
            lote.incluir_registro(Registro3Q(
                nome_sacado=sacado["nome"],
                endereco_sacado=sacado["endereco"],
                cep_sacado=sacado["cep"],
                cidade_sacado=sacado["cidade"],
                uf_sacado=sacado["uf"],
            ))
        arquivo.incluir_lote(lote)
        return arquivo.as_txt()

    def processar_retorno(self, caminho):
        retorno = SicrediRetorno(caminho)
        dados = []
        for item in retorno.titulos:
            dados.append({
                "nosso_numero": item.nosso_numero,
                "valor_pago": item.valor_pago,
                "data_pagamento": item.data_pagamento,
            })
        return dados
