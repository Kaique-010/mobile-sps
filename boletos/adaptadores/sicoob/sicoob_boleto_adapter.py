from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
from ...services.validation_service import build_barcode_data, render_barcode_image, linha_digitavel_from_barcode


class SicoobBoletoAdapter:
    def gerar_pdf(self, titulo, cedente, sacado, banco_cfg, caminho):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)

        try:
            from boleto.boleto_itau import BoletoItau
            b = BoletoItau()
        except Exception:
            b = None

        pdf = canvas.Canvas(caminho)
        variation = banco_cfg.get("logo_variation", "Colorido")
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        logo_path = banco_cfg.get("logo_path") or os.path.join(base_dir, "Logos", variation, str(banco_cfg.get("codigo_banco", "756")) + ".bmp")
        try:
            if os.path.exists(logo_path):
                pdf.drawImage(ImageReader(logo_path), 40, 750, width=120, height=40, mask='auto')
        except Exception:
            pass

        if b:
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
            b.numero_documento = getattr(titulo, 'titu_titu', '')
            b.nosso_numero = getattr(titulo, 'titu_noss_nume', '')
            b.drawBoleto(pdf)
        else:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(40, 720, f"Cedente: {cedente.get('nome', '')} ({cedente.get('documento', '')})")
            pdf.drawString(40, 700, f"Sacado: {sacado.get('nome', '')}")
            pdf.drawString(40, 680, f"Agência: {banco_cfg.get('agencia', '')} Conta: {banco_cfg.get('conta', '')}-{banco_cfg.get('dv', '')}")
            pdf.drawString(40, 660, f"Documento: {getattr(titulo, 'titu_titu', '')} Vencimento: {getattr(titulo, 'titu_venc', '')}")
            pdf.drawString(40, 640, f"Valor: {getattr(titulo, 'titu_valo', 0)} Nosso número: {getattr(titulo, 'titu_noss_nume', '')}")

        try:
            codigo = build_barcode_data(banco_cfg, titulo)
            linha = linha_digitavel_from_barcode(codigo)
            img = render_barcode_image(codigo)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(40, 600, f"Linha Digitável: {linha}")
            pdf.drawImage(ImageReader(img), 40, 580, width=420, height=60, mask='auto')
        except Exception:
            pass
        pdf.save()
        return caminho
