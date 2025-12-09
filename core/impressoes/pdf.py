# core/printing/pdf_builder.py
import base64
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


class PDFBuilder:
    def __init__(self, buffer):
        self.buffer = buffer
        self.styles = getSampleStyleSheet()
        self.flow = []
        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20,
        )

    def add_title(self, text):
        self.flow.append(Paragraph(text, self.styles['Title']))
        self.flow.append(Spacer(1, 15))

    def add_label_value(self, label, value):
        txt = f"<b>{label}:</b> {value}"
        self.flow.append(Paragraph(txt, self.styles['Normal']))
        self.flow.append(Spacer(1, 8))

    def add_table(self, data, col_widths=None, style=None):
        tbl = Table(data, colWidths=col_widths)
        if style is None:
            style = TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
            ])
        tbl.setStyle(style)
        self.flow.append(tbl)
        self.flow.append(Spacer(1, 15))

    def add_spacer(self, height):
        self.flow.append(Spacer(1, height))

    def _decode_base64_image(self, base64_str):
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        return BytesIO(base64.b64decode(base64_str))

    def add_signature(self, label, base64_img):
        self.flow.append(Paragraph(label, self.styles['Heading3']))
        img = self._decode_base64_image(base64_img)
        self.flow.append(Image(img, width=250, height=120))
        self.flow.append(Spacer(1, 20))

    def build(self):
        self.doc.build(self.flow)
        return self.buffer
