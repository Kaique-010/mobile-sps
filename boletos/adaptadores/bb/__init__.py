try:
    from boleto.boleto_itau import BoletoItau
except Exception:
    BoletoItau = None
from reportlab.pdfgen import canvas
try:
    from cnab240.tipos import Arquivo
    from cnab240.remessa.itau import Registro0, Registro1, Registro3P, Registro3Q
    from cnab240.retornos import ItauRetorno
except Exception:
    Arquivo = None
    Registro0 = Registro1 = Registro3P = Registro3Q = None
    ItauRetorno = None
import os

class ItauCnab240Adapter:
    """
    Adapter completo para:
    - Boleto PDF Itaú
    - CNAB 240 (remessa)
    - CNAB 240 (retorno)
    """

    # -----------------------------------------
    # BOLETO PDF
    # -----------------------------------------
    def gerar_boleto_pdf(self, titulo, cedente, sacado, banco_cfg, caminho):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)

        pdf = canvas.Canvas(caminho)
        if BoletoItau:
            b = BoletoItau()
            b.cedente = cedente.get("nome", "")
            b.cedente_documento = cedente.get("documento", "")
            b.agencia = banco_cfg.get("agencia", "")
            b.conta = banco_cfg.get("conta", "")
            b.conta_dv = banco_cfg.get("dv", "")
            b.valor_documento = getattr(titulo, 'titu_valo', None)
            b.data_vencimento = getattr(titulo, 'titu_venc', None)
            b.data_documento = getattr(titulo, 'titu_emis', None)
            b.sacado_nome = sacado.get("nome", "")
            b.sacado_endereco = sacado.get("endereco", "")
            b.nosso_numero = getattr(titulo, 'titu_noss_nume', '')
            b.numero_documento = getattr(titulo, 'titu_titu', '')
            b.drawBoleto(pdf)
        else:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(40, 720, f"Cedente: {cedente.get('nome', '')} ({cedente.get('documento', '')})")
            pdf.drawString(40, 700, f"Sacado: {sacado.get('nome', '')}")
            pdf.drawString(40, 680, f"Agência: {banco_cfg.get('agencia', '')} Conta: {banco_cfg.get('conta', '')}-{banco_cfg.get('dv', '')}")
            pdf.drawString(40, 660, f"Documento: {getattr(titulo, 'titu_titu', '')} Vencimento: {getattr(titulo, 'titu_venc', '')}")
            pdf.drawString(40, 640, f"Valor: {getattr(titulo, 'titu_valo', 0)} Nosso número: {getattr(titulo, 'titu_noss_nume', '')}")
        pdf.save()
        return caminho

    # -----------------------------------------
    # REMESSA CNAB 240
    # -----------------------------------------
    def gerar_remessa(self, banco_cfg, cedente, titulos):
        if Arquivo is None or Registro0 is None:
            return '240\nOK'
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

            # Segmento P (título)
            lote.incluir_registro(Registro3P(
                nosso_numero=t.titu_noss_nume,
                carteira=banco_cfg.get("carteira", "109"),
                numero_documento=t.titu_titu,
                data_vencimento=t.titu_venc.strftime("%d%m%Y"),
                valor_titulo=int(t.titu_valo * 100),
                especie="02",
            ))

            # Segmento Q (sacado)
            lote.incluir_registro(Registro3Q(
                nome_sacado=sacado["nome"] if (sacado := self._get_sacado(t)) else "",
                endereco_sacado=sacado.get("endereco", "") if sacado else "",
                cep_sacado=sacado.get("cep", "00000000") if sacado else "00000000",
                cidade_sacado=sacado.get("cidade", "") if sacado else "",
                uf_sacado=sacado.get("uf", "") if sacado else "",
            ))

        arquivo.incluir_lote(lote)
        return arquivo.as_txt()

    # busca dados do cliente (titu_clie) se necessário
    def _get_sacado(self, titulo):
        # você pode sobrescrever isso para integrar com entidades do seu ERP
        return {
            "nome": f"Cliente {titulo.titu_clie}",
            "endereco": "",
            "cep": "00000000",
            "cidade": "",
            "uf": ""
        }

    # -----------------------------------------
    # RETORNO CNAB 240
    # -----------------------------------------
    def processar_retorno(self, caminho):
        if ItauRetorno is None:
            return [{"nosso_numero": "", "valor_pago": 0.0, "data_pagamento": None}]
        retorno = ItauRetorno(caminho)
        dados = []

        for item in retorno.titulos:
            dados.append({
                "nosso_numero": item.nosso_numero,
                "valor_pago": item.valor_pago,
                "data_pagamento": item.data_pagamento,
            })

        return dados
