
from io import BytesIO
import base64
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib import colors
from .pdf import PDFBuilder

class BasePrinter:
    title = "Documento"
    default_header = True

    def __init__(self, filial, documento, cliente, modelo, itens=None, servicos=None, horas=None, assinaturas=None, solicitante=None, responsavel_campo=None):
        self.filial = filial
        self.documento = documento
        self.cliente = cliente
        self.modelo = modelo
        self.itens = itens or []
        self.servicos = servicos or []
        self.horas = horas or []
        self.assinaturas = assinaturas or {}
        self.solicitante = solicitante
        self.responsavel_campo = responsavel_campo

    def render(self):
        buf = BytesIO()
        pdf = PDFBuilder(buf)

        pdf.add_title(self.title)

        if self.default_header:
            filial_nome = (
                getattr(self.filial, "empr_nome", None)
                or getattr(self.filial, "nome", None)
                or str(self.filial)
            )
            pdf.add_label_value("Filial", filial_nome)
            pdf.add_label_value("Documento Nº", self.documento)

            pdf.add_label_value("Cliente", self.cliente.enti_nome)
            pdf.add_label_value("CNPJ/CPF", self.cliente.enti_cpf or self.cliente.enti_cnpj)

        self.render_body(pdf)
        self.render_signatures(pdf)

        return pdf.build()

    def render_body(self, pdf):
        raise NotImplementedError

    def render_signatures(self, pdf):
        assinaturas = []
        pref_order = ["Assinatura do Cliente", "Assinatura do Operador"]
        for l in pref_order:
            if l in self.assinaturas:
                assinaturas.append((l, self.assinaturas.get(l)))
        for label, img in self.assinaturas.items():
            if not any(label == a[0] for a in assinaturas):
                assinaturas.append((label, img))

        def decode_img(b64):
            if not b64:
                return None
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            try:
                return BytesIO(base64.b64decode(b64))
            except Exception:
                return None

        def make_cell(lbl, b64):
            img_buf = decode_img(b64)
            flowables = []
            flowables.append(Paragraph(lbl, pdf.styles['Heading3']))
            if img_buf:
                flowables.append(Image(img_buf, width=90, height=28))
            cell = Table([[f] for f in flowables], colWidths=[150])
            cell.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            return cell

        rows = []
        for i in range(0, len(assinaturas), 2):
            pair = assinaturas[i:i+2]
            if len(pair) == 1:
                left = make_cell(pair[0][0], pair[0][1])
                right = Table([[Paragraph('', pdf.styles['Normal'])]])
            else:
                left = make_cell(pair[0][0], pair[0][1])
                right = make_cell(pair[1][0], pair[1][1])
            rows.append([left, right])

        if rows:
            tbl = Table(rows, colWidths=[350, 350])
            tbl.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            pdf.flow.append(tbl)
            pdf.add_spacer(6)
