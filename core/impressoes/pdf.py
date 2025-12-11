# core/printing/pdf_builder.py
"""
Módulo responsável por construir documentos PDF usando ReportLab.
Fornece uma interface simplificada para criar PDFs profissionais com
tabelas, imagens, textos e assinaturas.
"""

import base64
from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate, 
    Paragraph, 
    Image, 
    Spacer, 
    Table, 
    TableStyle
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class PDFBuilder:
    """
    Construtor de documentos PDF usando ReportLab.
    
    Responsável por:
    - Configurar as dimensões e margens do documento
    - Adicionar elementos (títulos, parágrafos, tabelas, imagens)
    - Gerenciar estilos de texto
    - Construir o PDF final
    
    Attributes:
        buffer: Buffer de bytes onde o PDF será escrito
        styles: Estilos de texto disponíveis (título, normal, etc)
        flow: Lista de elementos que serão renderizados no PDF
        doc: Documento ReportLab configurado
    """
    
    def __init__(self, buffer, orientation='landscape', margins=None):
        """
        Inicializa o construtor de PDF.
        
        Args:
            buffer: BytesIO buffer para armazenar o PDF
            orientation: 'landscape' (paisagem) ou 'portrait' (retrato)
            margins: Dict com margens customizadas {'left': 12, 'right': 12, ...}
        """
        self.buffer = buffer
        
        # Carrega estilos padrão do ReportLab e adiciona estilos customizados
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Lista de elementos que serão adicionados ao PDF na ordem
        self.flow = []
        
        # Configura as margens do documento
        default_margins = {
            'leftMargin': 8 * mm,
            'rightMargin': 8 * mm,
            'topMargin': 8 * mm,
            'bottomMargin': 8 * mm,
        }
        if margins:
            default_margins.update(margins)
        
        # Define a orientação da página (paisagem ou retrato)
        pagesize = landscape(A4) if orientation == 'landscape' else A4
        
        # Cria o documento PDF com as configurações definidas
        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            **default_margins
        )

    def _setup_custom_styles(self):
        """
        Configura estilos customizados para o documento.
        
        Cria estilos adicionais além dos padrão do ReportLab:
        - Heading2: Subtítulos grandes e centralizados
        - Heading3: Subtítulos médios
        - TableHeader: Cabeçalhos de tabelas com fundo cinza
        """
        # Estilo para subtítulos grandes (ex: "ORDEM DE LOCAÇÃO")
        if 'H2Center' not in self.styles.byName:
            self.styles.add(ParagraphStyle(
                name='H2Center',
                parent=self.styles['Heading2'],
                fontSize=16,
                textColor=colors.black,
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ))
        
        # Estilo para subtítulos médios (ex: "Nº 33")
        if 'H3Center' not in self.styles.byName:
            self.styles.add(ParagraphStyle(
                name='H3Center',
                parent=self.styles['Heading3'],
                fontSize=14,
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ))
        
        # Estilo para cabeçalhos de tabelas
        if 'TableHeader' not in self.styles.byName:
            self.styles.add(ParagraphStyle(
                name='TableHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.white,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER
            ))

    def add_title(self, text, style='Title'):
        """
        Adiciona um título ao documento.
        
        Args:
            text: Texto do título
            style: Nome do estilo a ser usado (padrão: 'Title')
        """
        self.flow.append(Paragraph(text, self.styles[style]))
        self.flow.append(Spacer(1, 6))

    def add_paragraph(self, text, style='Normal'):
        """
        Adiciona um parágrafo de texto ao documento.
        
        Args:
            text: Texto do parágrafo (pode conter tags HTML simples)
            style: Nome do estilo a ser usado
        """
        self.flow.append(Paragraph(text, self.styles[style]))

    def add_label_value(self, label, value, style='Normal'):
        """
        Adiciona um par label: valor formatado.
        
        Útil para exibir informações como "Cliente: João Silva"
        
        Args:
            label: Rótulo em negrito
            value: Valor a ser exibido
            style: Estilo do texto
        """
        txt = f"<b>{label}:</b> {value}"
        self.flow.append(Paragraph(txt, self.styles[style]))
        self.flow.append(Spacer(1, 8))

    def add_table(self, data, col_widths=None, style=None, header_row=False):
        """
        Adiciona uma tabela ao documento.
        
        A tabela é o elemento mais versátil para layouts profissionais.
        Permite organizar dados em linhas e colunas com bordas e estilos.
        
        Args:
            data: Lista de listas representando as linhas e colunas
                  Ex: [['Nome', 'Idade'], ['João', '30'], ['Maria', '25']]
            col_widths: Lista com larguras de cada coluna em pontos
                       Ex: [200, 100] para 2 colunas
            style: TableStyle customizado (usa padrão se None)
            header_row: Se True, aplica estilo especial à primeira linha
        """
        tbl = Table(data, colWidths=col_widths, repeatRows=1 if header_row else 0)
        
        if style is None:
            # Estilo padrão: grid preto, texto alinhado, padding confortável
            style = TableStyle([
                # Desenha grade ao redor de todas as células
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                
                # Alinhamento vertical no meio da célula
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Alinhamento horizontal à esquerda
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                
                # Fonte e tamanho padrão
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
                
                # Espaçamento interno das células (padding)
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ])
            
            # Se tem cabeçalho, aplica estilo especial à primeira linha
            if header_row and data:
                style.add('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(''))
                style.add('TEXTCOLOR', (0, 0), (-1, 0), colors.black)
                style.add('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
                style.add('ALIGN', (0, 0), (-1, 0), 'CENTER')
        
        tbl.setStyle(style)
        self.flow.append(tbl)
        self.flow.append(Spacer(1, 6))

    def add_spacer(self, height):
        """
        Adiciona espaço vertical entre elementos.
        
        Args:
            height: Altura do espaço em pontos (1 ponto ≈ 0.35mm)
        """
        self.flow.append(Spacer(1, height))

    def add_image(self, image_data, width=None, height=None, alignment='CENTER'):
        """
        Adiciona uma imagem ao documento.
        
        Args:
            image_data: Pode ser:
                       - BytesIO buffer com dados da imagem
                       - String base64 da imagem
                       - Caminho para arquivo de imagem
            width: Largura desejada (None = tamanho original)
            height: Altura desejada (None = tamanho original)
            alignment: 'CENTER', 'LEFT' ou 'RIGHT'
        """
        # Se for string base64, decodifica
        if isinstance(image_data, str):
            image_data = self._decode_base64_image(image_data)
        
        # Cria o elemento Image do ReportLab
        img = Image(image_data, width=width, height=height)
        
        # Centraliza se solicitado
        if alignment == 'CENTER':
            img.hAlign = 'CENTER'
        elif alignment == 'LEFT':
            img.hAlign = 'LEFT'
        elif alignment == 'RIGHT':
            img.hAlign = 'RIGHT'
        
        self.flow.append(img)

    def _decode_base64_image(self, base64_str):
        """
        Decodifica uma string base64 em um buffer de imagem.
        
        Suporta formato data URI: "data:image/png;base64,iVBORw0KG..."
        
        Args:
            base64_str: String base64 da imagem
            
        Returns:
            BytesIO buffer com os dados da imagem decodificados
        """
        # Remove prefixo data URI se presente
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        # Decodifica base64 para bytes e retorna como buffer
        return BytesIO(base64.b64decode(base64_str))

    def add_signature_block(self, signatures):
        """
        Adiciona um bloco de assinaturas ao documento.
        
        Organiza múltiplas assinaturas lado a lado (2 por linha).
        Cada assinatura tem um label e uma imagem opcional.
        
        Args:
            signatures: Lista de tuplas (label, base64_image)
                       Ex: [("Assinatura do Cliente", "data:image/png;base64,..."),
                            ("Assinatura do Operador", "data:image/png;base64,...")]
        """
        if not signatures:
            return
        
        def make_signature_cell(label, base64_img):
            """
            Cria uma célula de assinatura com label e imagem.
            
            Returns:
                Table com o label e imagem (ou espaço vazio) organizados
            """
            flowables = []
            
            # Adiciona o label (ex: "Assinatura do Cliente")
            flowables.append(Paragraph(
                f"<b>{label}</b>", 
                self.styles['Normal']
            ))
            flowables.append(Spacer(1, 5))
            
            # Adiciona a imagem da assinatura se existir
            if base64_img:
                try:
                    img_buf = self._decode_base64_image(base64_img)
                    flowables.append(Image(img_buf, width=150, height=50))
                except Exception:
                    # Se falhar ao decodificar, adiciona espaço vazio
                    flowables.append(Spacer(1, 50))
            else:
                # Sem assinatura, adiciona espaço vazio
                flowables.append(Spacer(1, 50))
            
            # Adiciona linha horizontal para assinatura manual se necessário
            flowables.append(Spacer(1, 5))
            flowables.append(Paragraph(
                "_" * 50, 
                self.styles['Normal']
            ))
            
            # Organiza tudo em uma mini-tabela
            cell = Table([[f] for f in flowables], colWidths=[180])
            cell.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            return cell
        
        # Organiza assinaturas em pares (2 por linha)
        rows = []
        for i in range(0, len(signatures), 2):
            pair = signatures[i:i+2]
            
            # Cria célula esquerda
            left = make_signature_cell(pair[0][0], pair[0][1])
            
            # Cria célula direita (ou vazia se não houver segunda assinatura)
            if len(pair) == 2:
                right = make_signature_cell(pair[1][0], pair[1][1])
            else:
                right = Paragraph('', self.styles['Normal'])
            
            rows.append([left, right])
        
        # Cria tabela principal com todas as assinaturas
        if rows:
            tbl = Table(rows, colWidths=[380, 380])
            tbl.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            self.flow.append(tbl)
            self.add_spacer(15)

    def build(self):
        """
        Constrói o PDF final com moldura externa nas páginas.
        """
        def _frame(canvas, doc):
            canvas.saveState()
            canvas.setLineWidth(0.7)
            canvas.setStrokeColor(colors.black)
            pad = 7 * mm
            x = doc.leftMargin - pad
            y = doc.bottomMargin - pad
            w = doc.width + (pad * 2)
            h = doc.height + (pad * 2)
            try:
                canvas.roundRect(x, y, w, h, 6)
            except Exception:
                canvas.rect(x, y, w, h)
            canvas.restoreState()

        self.doc.build(self.flow, onFirstPage=_frame, onLaterPages=_frame)
        return self.buffer
