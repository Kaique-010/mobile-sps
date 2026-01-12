# core/printing/documents/ordem_servico.py
"""
Impressão profissional de Ordem de Serviço/Locação.

Gera um PDF detalhado com:
- Cabeçalho customizado com logo e dados da empresa
- Informações do cliente e equipamento
- Tabela de horas trabalhadas (manhã e tarde)
- Discriminação de peças e serviços
- Resumo financeiro
- Bloco de assinaturas
"""

from datetime import datetime, timedelta
from io import BytesIO
import base64
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from core.impressoes.base import BasePrinter


class OrdemServicoPrinter(BasePrinter):
    """
    Impressão de Ordem de Serviço/Locação.
    
    Layout profissional em paisagem com:
    - Cabeçalho dividido em blocos (empresa + título)
    - Campos de identificação organizados
    - Tabela de horas com totalizador
    - Discriminação detalhada de serviços
    - Resumo financeiro lado a lado com dados extras
    """
    
    title = "Ordem de Serviço"
    default_header = False  # Usa cabeçalho customizado
    orientation = 'landscape'

    def render_body(self, pdf):
        """
        Renderiza o corpo completo da Ordem de Serviço.
        
        Estrutura:
        1. Cabeçalho customizado (logo + empresa + título)
        2. Campos de identificação (cliente, equipamento, etc)
        3. Tabela de horas trabalhadas
        4. Discriminação de peças e serviços
        5. Observações
        6. Resumo financeiro
        """
        # ===============================================================
        # 1. CABEÇALHO CUSTOMIZADO
        # ===============================================================
        self._render_custom_header(pdf)
        
        # ===============================================================
        # 2. CAMPOS DE IDENTIFICAÇÃO
        # ===============================================================
        self._render_identification_fields(pdf)
        
        # ===============================================================
        # 3. TABELA DE HORAS TRABALHADAS
        # ===============================================================
        total_horas, km_saida, km_chegada = self._render_hours_table(pdf)
        
        # ===============================================================
        # 4. DISCRIMINAÇÃO DE PEÇAS E SERVIÇOS
        # ===============================================================
        self._render_items_and_services(pdf)
        
        # ===============================================================
        # 5. OBSERVAÇÕES
        # ===============================================================
        self._render_observations(pdf)
        
        # ===============================================================
        # 6. RESUMO FINANCEIRO
        # ===============================================================
        self._render_financial_summary(pdf, total_horas, km_saida, km_chegada)

    def _safe_getattr(self, obj, attr, default=""):
        try:
            v = getattr(obj, attr, default)
            return v if v is not None else default
        except Exception:
            return default

    def _format_date(self, d):
        try:
            return d.strftime("%d/%m/%Y") if d else ""
        except Exception:
            return str(d) if d else ""

    def _format_time(self, t):
        try:
            return t.strftime("%H:%M") if t else ""
        except Exception:
            return str(t) if t else ""

    def _format_currency(self, v):
        try:
            f = float(v or 0)
            return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return f"R$ {v}"

    def _decode_logo_value(self, val):
        try:
            if val is None:
                return None
            if isinstance(val, memoryview):
                return BytesIO(val.tobytes())
            if isinstance(val, (bytes, bytearray)):
                b = bytes(val)
                if b.startswith(b"\x89PNG") or b.startswith(b"\xff\xd8"):
                    return BytesIO(b)
                try:
                    return BytesIO(base64.b64decode(b))
                except Exception:
                    return BytesIO(b)
            if isinstance(val, str):
                data = val.split(",", 1)[1] if "," in val else val
                return BytesIO(base64.b64decode(data))
        except Exception:
            return None
        return None

    def _create_logo_image(self, val, max_width=160, max_height=60):
        try:
            buf = self._decode_logo_value(val)
            if not buf:
                return None
            reader = ImageReader(buf)
            iw, ih = reader.getSize()
            if not iw or not ih:
                return None
            scale = min(max_width / float(iw), max_height / float(ih))
            sw = max(1, int(iw * scale))
            sh = max(1, int(ih * scale))
            return Image(buf, width=sw, height=sh)
        except Exception:
            return None

    def _render_custom_header(self, pdf):
        """
        Renderiza cabeçalho customizado com logo, dados da empresa e título.
        
        Layout:
        +------------------------------------------+------------------+
        | [LOGO] Nome da Empresa                   | ORDEM DE LOCAÇÃO |
        |        CNPJ: XX.XXX.XXX/XXXX-XX          | Nº 33            |
        +------------------------------------------+------------------+
        
        Args:
            pdf: Instância do PDFBuilder
        """
        # Extrai dados da filial
        filial_nome = (
            self._safe_getattr(self.filial, "empr_fant") or 
            self._safe_getattr(self.filial, "empr_nome", "Empresa")
        )
        filial_doc = self._safe_getattr(self.filial, "empr_docu", "")
        filial_logo = getattr(self.filial, "empr_logo", None)

        # ---------------------------------------------------------------
        # BLOCO ESQUERDO: Logo + Dados da Empresa
        # ---------------------------------------------------------------
        
        # Cria elemento de logo (ou vazio se não houver)
        logo_cell = self._create_logo_image(
            filial_logo, 
            max_width=160, 
            max_height=60
        ) or Paragraph('', pdf.styles['Normal'])

        # Tabela com dados da empresa (nome e CNPJ)
        empresa_info = Table([
            [Paragraph(f"<b>{filial_nome}</b>", pdf.styles['Normal'])],
            [Paragraph(f"CNPJ: {filial_doc}", pdf.styles['Normal'])]
        ], colWidths=[340], rowHeights=[24, 24])
        
        empresa_info.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        # Combina logo + dados em uma tabela
        left_block = Table([[logo_cell, empresa_info]], colWidths=[180, 360], rowHeights=[54])
        left_block.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.7, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),     # Alinha verticalmente
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        # ---------------------------------------------------------------
        # BLOCO DIREITO: Título e Número da Ordem
        # ---------------------------------------------------------------
        
        right_header = Table([
            [Paragraph("<b>ORDEM DE LOCAÇÃO</b>", pdf.styles['Heading2'])],
            [Paragraph(f"<b>Nº {self.documento}</b>", pdf.styles['Heading3'])]
        ], colWidths=[220], rowHeights=[26, 26])
        
        right_header.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.7, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        # ---------------------------------------------------------------
        # Combina blocos esquerdo e direito
        # ---------------------------------------------------------------
        
        outer = Table([[left_block, right_header]], colWidths=[540, 220])
        outer.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        pdf.flow.append(outer)
        pdf.add_spacer(10)

    def _render_identification_fields(self, pdf):
        """
        Renderiza campos de identificação do serviço.
        
        Tabela com 2 linhas e 4 colunas:
        - Cliente / Local de Trabalho
        - Equipamento / Placa
        
        Args:
            pdf: Instância do PDFBuilder
        """
        # Extrai dados do modelo
        cliente_nome = self._safe_getattr(self.cliente, "enti_nome", "")
        
        # Local de trabalho (tenta diferentes campos)
        local_trabalho = (
            self._safe_getattr(self.modelo, "os_loca_apli") or 
            self._safe_getattr(self.modelo, "os_ende_apli", "")
        )
        
        # Equipamento (motor ou automóvel)
        equipamento = (
            self._safe_getattr(self.modelo, "os_moto") or 
            self._safe_getattr(self.modelo, "os_auto", "")
        )
        
        # Placa do veículo
        placa = (
            self._safe_getattr(self.modelo, "os_plac") or 
            self._safe_getattr(self.modelo, "os_plac_1", "")
        )

        # Monta tabela de campos
        campos = [
            [
                Paragraph("<b>Cliente:</b>", pdf.styles['Normal']),
                Paragraph(cliente_nome, pdf.styles['Normal']),
                Paragraph("<b>Equipamento:</b>", pdf.styles['Normal']),
                Paragraph(equipamento, pdf.styles['Normal']),
            ],
            [
                Paragraph("<b>Local de Trabalho:</b>", pdf.styles['Normal']),
                Paragraph(local_trabalho, pdf.styles['Normal']),
                Paragraph("<b>Placa:</b>", pdf.styles['Normal']),
                Paragraph(placa, pdf.styles['Normal']),
            ],
        ]
        
        tbl = Table(campos, colWidths=[120, 350, 100, 190])
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        pdf.flow.append(tbl)
        pdf.add_spacer(6)

    def _render_hours_table(self, pdf):
        """
        Renderiza tabela de horas trabalhadas com turnos manhã e tarde.
        
        Colunas: Data | Início Manhã | Fim Manhã | Início Tarde | Fim Tarde | Total
        
        Args:
            pdf: Instância do PDFBuilder
            
        Returns:
            tuple: (total_horas, km_saida, km_chegada)
        """
        # Cabeçalho da tabela
        header = ["Data", "Início", "Fim", "Intervalo", "Início", "Fim", "Total"]
        data = [header]
        
        total_horas = 0.0
        km_saida = ""
        km_chegada = ""

        # Processa cada registro de hora
        for h in self.horas or []:
            # Captura KM de saída (primeiro registro)
            if km_saida == "" and self._safe_getattr(h, "os_hora_km_sai", None):
                km_saida = self._safe_getattr(h, "os_hora_km_sai", "")
            
            # Atualiza KM de chegada (último registro)
            if self._safe_getattr(h, "os_hora_km_che", None):
                km_chegada = self._safe_getattr(h, "os_hora_km_che", "")
            
            # Extrai horários
            manh_ini = getattr(h, "os_hora_manh_ini", None)
            manh_fim = getattr(h, "os_hora_manh_fim", None)
            tard_ini = getattr(h, "os_hora_tard_ini", None)
            tard_fim = getattr(h, "os_hora_tard_fim", None)
            data_ref = getattr(h, "os_hora_data", None) or datetime.today().date()
            
            # Calcula total de horas (usa valor salvo ou calcula)
            row_total = float(self._safe_getattr(h, "os_hora_tota", 0))
            if not row_total:
                # Calculate interval hours if enabled
                if self._safe_getattr(h, "os_hora_manh_inte", False):
                    interval_hours = self._calculate_hours_diff(data_ref, manh_fim, tard_ini)
                else:
                    interval_hours = 0.0
                
                row_total = (
                    self._calculate_hours_diff(data_ref, manh_ini, manh_fim) +
                    self._calculate_hours_diff(data_ref, tard_ini, tard_fim) +
                    interval_hours
                )
            
            total_horas += row_total

            # Adiciona linha à tabela
            data.append([
                self._format_date(data_ref),
                self._format_time(manh_ini),
                self._format_time(manh_fim),
                self._format_time(manh_fim, manh_ini) if manh_inte else "",
                self._format_time(tard_ini),
                self._format_time(tard_fim),
                f"{row_total:.2f}",
            ])
        
        # Se não houver horas, adiciona linha vazia
        if len(data) == 1:
            data.append(["", "", "", "", "", "0.00"])

        # Cria tabela de horas
        tbl = Table(data, colWidths=[95, 85, 85, 85, 85, 75])
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ]))
        
        pdf.flow.append(tbl)
        pdf.add_spacer(6)

        # Linha de total de horas
        total_row = Table([
            [
                Paragraph("<b>Total de Horas Trabalhadas:</b>", pdf.styles['Normal']),
                Paragraph(f"<b>{total_horas:.2f} horas</b>", pdf.styles['Normal'])
            ]
        ], colWidths=[350, 150])
        
        total_row.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.7, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        
        pdf.flow.append(total_row)
        pdf.add_spacer(6)

        return total_horas, km_saida, km_chegada

    def _render_items_and_services(self, pdf):
        """
        Renderiza discriminação detalhada de peças e serviços.
        
        Lista cada peça e serviço utilizado com:
        - Código do produto
        - Quantidade
        - Observações (se houver)
        
        Args:
            pdf: Instância do PDFBuilder
        """
        # Cabeçalho da seção
        data = [[
            Paragraph("<b>DISCRIMINAÇÃO DOS SERVIÇOS</b>", pdf.styles['Heading3']),
            ""
        ]]
        
        # ---------------------------------------------------------------
        # PEÇAS UTILIZADAS
        # ---------------------------------------------------------------
        if self.itens:
            data.append([
                Paragraph("<b>PEÇAS:</b>", pdf.styles['Normal']),
                ""
            ])
            
            for p in self.itens:
                prod = self._safe_getattr(p, "peca_prod", "")
                quan = self._safe_getattr(p, "peca_quan", "")
                obse = self._safe_getattr(p, "peca_obse", None)
                
                # Monta descrição da peça
                linha = f"• Peça {prod} - Quantidade: {quan}"
                if obse:
                    linha = f"{linha} - {obse}"
                
                data.append([Paragraph(linha, pdf.styles['Normal']), ""])
        
        # ---------------------------------------------------------------
        # SERVIÇOS EXECUTADOS
        # ---------------------------------------------------------------
        if self.servicos:
            data.append([
                Paragraph("<b>SERVIÇOS:</b>", pdf.styles['Normal']),
                ""
            ])
            
            for s in self.servicos:
                prod = self._safe_getattr(s, "serv_prod", "")
                quan = self._safe_getattr(s, "serv_quan", "")
                obse = self._safe_getattr(s, "serv_obse", None)
                
                # Monta descrição do serviço
                linha = f"• Serviço {prod} - Quantidade: {quan}"
                if obse:
                    linha = f"{linha} - {obse}"
                
                data.append([Paragraph(linha, pdf.styles['Normal']), ""])
        
        # Se não houver itens nem serviços, adiciona linha vazia
        if len(data) == 1:
            data.append([
                Paragraph("Nenhum item ou serviço lançado", pdf.styles['Normal']),
                ""
            ])

        # Cria tabela de discriminação
        tbl = Table(data, colWidths=[600, 160])
        tbl.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ]))
        
        pdf.flow.append(tbl)
        pdf.add_spacer(6)

    def _render_observations(self, pdf):
        """
        Renderiza campo de observações.
        
        Args:
            pdf: Instância do PDFBuilder
        """
        obs = self._safe_getattr(self.modelo, "os_obse", "")
        
        obs_table = Table([
            [
                Paragraph("<b>OBSERVAÇÕES:</b>", pdf.styles['Normal']),
                Paragraph(obs, pdf.styles['Normal'])
            ]
        ], colWidths=[120, 640])
        
        obs_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        pdf.flow.append(obs_table)
        pdf.add_spacer(6)

    def _render_financial_summary(self, pdf, total_horas, km_saida, km_chegada):
        """
        Renderiza resumo financeiro lado a lado com dados extras.
        
        Layout:
        +-----------------------------+-------------------------+
        | Mínimo de Horas: X          | Anotações Extras:       |
        | Horas Trabalhadas: Y        | Solicitante: Nome       |
        | Valor Total: R$ Z           | Resp. em Campo: Nome    |
        | Km Saída / Chegada          | Função: Operador        |
        | TOTAL: R$ XXX               |                         |
        +-----------------------------+-------------------------+
        
        Args:
            pdf: Instância do PDFBuilder
            total_horas: Total de horas calculado
            km_saida: KM de saída
            km_chegada: KM de chegada
        """
        # ---------------------------------------------------------------
        # BLOCO ESQUERDO: Resumo Financeiro
        # ---------------------------------------------------------------
        
        minimo_horas = self._safe_getattr(self.modelo, "os_hori", "")
        total_rs = self._format_currency(self._safe_getattr(self.modelo, "os_tota", 0))
        
        left_data = [
            ["Mínimo de Horas:", f"{minimo_horas} hs"],
            ["Horas Trabalhadas:", f"{total_horas:.2f} hs"],
            ["Valor Hora:", "R$ _______"],
            ["Valor Deslocamento:", "R$ _______"],
            ["Km Saída:", str(km_saida)],
            ["Km Chegada:", str(km_chegada)],
            ["TOTAL", total_rs],
        ]
        
        left_table = Table(left_data, colWidths=[180, 200])
        left_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))

        # ---------------------------------------------------------------
        # BLOCO DIREITO: Dados Extras
        # ---------------------------------------------------------------
        
        solicitante_nome = ""
        if self.solicitante:
            solicitante_nome = self._safe_getattr(self.solicitante, 'enti_nome', '')
        else:
            solicitante_nome = self._safe_getattr(self.cliente, 'enti_nome', '')
        
        resp_campo_nome = ""
        if self.responsavel_campo:
            resp_campo_nome = self._safe_getattr(self.responsavel_campo, 'enti_nome', '')
        
        funcao = self._safe_getattr(self.modelo, 'os_funcao', '')

        right_data = [
            ["Anotações Extras:", ""],
            ["Solicitante:", Paragraph(solicitante_nome, pdf.styles['Normal'])],
            ["Resp. em Campo:", Paragraph(resp_campo_nome, pdf.styles['Normal'])],
            ["Função:", Paragraph(funcao, pdf.styles['Normal'])],
        ]
        
        right_table = Table(right_data, colWidths=[130, 230])
        right_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))

        # ---------------------------------------------------------------
        # Combina ambos os blocos
        # ---------------------------------------------------------------
        
        outer = Table([[left_table, right_table]], colWidths=[400, 360])
        outer.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        pdf.flow.append(outer)
        pdf.add_spacer(8)

    def _calculate_hours_diff(self, date, time_start, time_end):
        """
        Calcula diferença em horas entre dois horários.
        
        Args:
            date: Data de referência
            time_start: Horário de início
            time_end: Horário de fim
            
        Returns:
            float: Diferença em horas (ex: 2.5 = 2h30min)
        """
        try:
            if not time_start or not time_end:
                return 0.0
            
            # Combina data com horários
            dt_start = datetime.combine(date, time_start) if hasattr(time_start, 'hour') else None
            dt_end = datetime.combine(date, time_end) if hasattr(time_end, 'hour') else None
            
            if not dt_start or not dt_end:
                return 0.0
            
            # Calcula diferença
            delta = dt_end - dt_start
            
            # Retorna em horas (arredondado para 2 decimais)
            return round(delta.total_seconds() / 3600.0, 2) if delta.total_seconds() > 0 else 0.0
        except Exception:
            return 0.0
