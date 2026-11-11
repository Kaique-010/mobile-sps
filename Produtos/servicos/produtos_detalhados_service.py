# Produtos/servicos/produtos_detalhados_service.py
"""Service de leitura do relatório de Produtos Detalhados (view produtos_detalhados).

Centraliza filtros e paginação (limit/offset = 50 por página) por tenant,
reutilizando o padrão de ListView + infinite scroll da aplicação.
"""

import os
from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.contrib.staticfiles.finders import find as find_static
from django.core.paginator import Paginator
from django.db.models import Q
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Image, Table, TableStyle

from core.db_columns import campo_existe_no_banco
from core.impressoes.pdf import PDFBuilder
from Produtos.models import ProdutosDetalhados


class ProdutosDetalhadosService:
    PAGE_SIZE = 50

    CAMPOS_EXPORTACAO = (
        ("empresa", "Empresa"),
        ("filial", "Filial"),
        ("codigo", "Código"),
        ("nome", "Nome"),
        ("unidade", "Unidade"),
        ("grupo_id", "Cód. Grupo"),
        ("grupo_nome", "Grupo"),
        ("marca_id", "Cód. Marca"),
        ("marca_nome", "Marca"),
        ("ncm", "NCM"),
        ("codigo_do_fabricante", "Cód. Fabricante"),
        ("custo", "Custo"),
        ("preco_vista", "Preço à Vista"),
        ("preco_prazo", "Preço a Prazo"),
        ("saldo", "Saldo"),
        ("valor_total_estoque", "Valor em Estoque"),
        ("valor_total_venda_vista", "Venda à Vista"),
        ("valor_total_venda_prazo", "Venda a Prazo"),
        ("peso_bruto", "Peso Bruto"),
        ("peso_liquido", "Peso Líquido"),
    )

    # PDF não repete Empresa/Filial (já exibidos no header do relatório)
    CAMPOS_PDF = tuple(
        (campo, rotulo)
        for campo, rotulo in CAMPOS_EXPORTACAO
        if campo not in ("empresa", "filial")
    )

    # Formatação de campos numéricos (Decimal) para exportação
    CAMPOS_2_CASAS = {
        "custo",
        "preco_vista",
        "preco_prazo",
        "saldo",
        "valor_total_estoque",
        "valor_total_venda_vista",
        "valor_total_venda_prazo",
    }
    CAMPOS_3_CASAS = {"peso_bruto", "peso_liquido"}

    def _formatar_valor(self, campo, valor):
        if valor is None or valor == "":
            return ""
        if campo in self.CAMPOS_2_CASAS:
            try:
                return f"{float(valor):.2f}"
            except (TypeError, ValueError):
                return valor
        if campo in self.CAMPOS_3_CASAS:
            try:
                return f"{float(valor):.3f}"
            except (TypeError, ValueError):
                return valor
        return valor

    CAMPOS_ORDENACAO = {
        "codigo": "codigo",
        "nome": "nome",
        "nome_desc": "-nome",
        "saldo": "-saldo",
        "menor_preco": "preco_vista",
        "maior_preco": "-preco_vista",
        "maior_valor_estoque": "-valor_total_estoque",
    }

    def __init__(self, *, db_alias="default", empresa=None, filial=None):
        self.db_alias = db_alias
        self.empresa = str(empresa) if empresa not in (None, "") else None
        self.filial = str(filial) if filial not in (None, "") else None

    def get_queryset(self, filtros=None):
        filtros = filtros or {}
        qs = ProdutosDetalhados.objects.using(self.db_alias).all()

        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if self.filial:
            qs = qs.filter(filial=self.filial)

        codigo = (filtros.get("codigo") or "").strip()
        if codigo:
            qs = qs.filter(codigo__icontains=codigo)

        nome = (filtros.get("nome") or "").strip()
        if nome:
            qs = qs.filter(nome__icontains=nome)

        grupo = (filtros.get("grupo") or "").strip()
        if grupo:
            qs = qs.filter(Q(grupo_nome__icontains=grupo) | Q(grupo_id__icontains=grupo))

        marca = (filtros.get("marca") or "").strip()
        if marca:
            qs = qs.filter(Q(marca_nome__icontains=marca) | Q(marca_id__icontains=marca))

        ncm = (filtros.get("ncm") or "").strip()
        if ncm:
            qs = qs.filter(ncm__icontains=ncm)

        fabricante = (filtros.get("codigo_do_fabricante") or "").strip()
        if fabricante and campo_existe_no_banco(
            model=ProdutosDetalhados,
            field_name="codigo_do_fabricante",
            using=self.db_alias,
        ):
            qs = qs.filter(codigo_do_fabricante__icontains=fabricante)

        estoque = (filtros.get("estoque") or "").strip().lower()
        if estoque in ("com", "1", "true", "sim"):
            qs = qs.filter(saldo__gt=0)
        elif estoque in ("sem", "0", "false", "nao", "não"):
            qs = qs.filter(saldo__lte=0)

        ordenar = (filtros.get("ordenar") or "nome").strip()
        return qs.order_by(self.CAMPOS_ORDENACAO.get(ordenar, "nome"))

    def paginar(self, *, page=1, filtros=None, per_page=None):
        """Retorna a página (limit/offset) já no padrão do Django Paginator."""
        per_page = int(per_page or self.PAGE_SIZE)
        return Paginator(self.get_queryset(filtros=filtros), per_page).get_page(page)

    def _iter_linhas(self, filtros=None, campos=None):
        campos = campos or self.CAMPOS_EXPORTACAO
        nomes = [campo for campo, _ in campos]
        for obj in self.get_queryset(filtros=filtros).iterator():
            yield [
                "" if getattr(obj, nome, None) is None else getattr(obj, nome, None)
                for nome in nomes
            ]

    def _iter_linhas_formatadas(self, filtros=None, campos=None):
        campos = campos or self.CAMPOS_EXPORTACAO
        nomes = [campo for campo, _ in campos]
        for linha in self._iter_linhas(filtros=filtros, campos=campos):
            yield [
                self._formatar_valor(nomes[i], valor)
                for i, valor in enumerate(linha)
            ]

    def gerar_excel(self, filtros=None):
        """Gera o workbook Excel com todos os campos de ProdutosDetalhados."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Produtos Detalhados"

        headers = [rotulo for _, rotulo in self.CAMPOS_EXPORTACAO]
        ws.append(headers)

        header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
        header_font = Font(color="FFFFFF", bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        for linha in self._iter_linhas(filtros=filtros):
            ws.append(linha)

        # Larguras automáticas baseadas no cabeçalho
        for col_idx, (_, rotulo) in enumerate(self.CAMPOS_EXPORTACAO, start=1):
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max(12, len(rotulo) + 4)

        return wb

    def gerar_pdf(self, filtros=None, titulo="Relatório de Produtos Detalhados", usuario=None):
        """Gera o PDF em paisagem com tabela de todos os campos, sem cortes.

        Footer: logo (esquerda) | data/hora (centro) | usuário (direita).
        """
        buffer = BytesIO()
        pdf = PDFBuilder(buffer, orientation="landscape")

        pdf.add_title(titulo, style="H2Center")

        if self.empresa or self.filial:
            contexto = []
            if self.empresa:
                contexto.append(f"Empresa: {self.empresa}")
            if self.filial:
                contexto.append(f"Filial: {self.filial}")
            pdf.add_paragraph(" | ".join(contexto), style="Normal")
            pdf.add_spacer(4)

        headers = [rotulo for _, rotulo in self.CAMPOS_PDF]
        linhas = []
        for linha in self._iter_linhas_formatadas(filtros=filtros, campos=self.CAMPOS_PDF):
            linhas.append([str(valor) if valor is not None else "" for valor in linha])

        data = [headers] + linhas

        # Largura útil da página paisagem A4 (297mm - margens)
        max_w = landscape(A4)[0] - pdf.doc.leftMargin - pdf.doc.rightMargin

        # Mede a largura real do texto (em pontos) para cada coluna
        from reportlab.pdfbase.pdfmetrics import stringWidth

        fonte = 7
        fonte_nome = "Helvetica"
        header_nome = "Helvetica-Bold"
        padding = 6  # espaço interno (le+ri) em pontos

        # Inicializa com a largura do cabeçalho
        larguras = []
        for h in headers:
            larguras.append(stringWidth(h, header_nome, fonte) + padding)

        # Atualiza com a largura do maior conteúdo
        for linha in linhas:
            for i, valor in enumerate(linha):
                w = stringWidth(valor, fonte_nome, fonte) + padding
                if w > larguras[i]:
                    larguras[i] = w

        total_w = sum(larguras)

        # Se exceder a largura útil, reduz tudo proporcionalmente (escala) e baixa a fonte
        if total_w > max_w:
            escala = max_w / total_w
            larguras = [w * escala for w in larguras]
            fonte = max(5, int(fonte * escala))
            # Recalcula padding na nova fonte
            larguras = []
            for h in headers:
                larguras.append(stringWidth(h, header_nome, fonte) + padding)
            for linha in linhas:
                for i, valor in enumerate(linha):
                    w = stringWidth(valor, fonte_nome, fonte) + padding
                    if w > larguras[i]:
                        larguras[i] = w
            total_w = sum(larguras)
            if total_w > max_w:
                # Ajuste fino final
                escala = max_w / total_w
                larguras = [w * escala for w in larguras]

        style = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (-1, -1), "Helvetica", fonte),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            # Cabeçalho estilizado
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Zebra striping
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FB")]),
        ])

        tbl = Table(data, colWidths=larguras, repeatRows=1)
        tbl.setStyle(style)
        pdf.flow.append(tbl)

        return self._build_com_footer(pdf, usuario=usuario)

    @staticmethod
    def _caminho_logo():
        caminho = find_static("logo.png")
        if not caminho or not os.path.exists(caminho):
            return None
        return caminho

    def _build_com_footer(self, pdf, usuario=None):
        """Constrói o PDF desenhando moldura + footer (logo, data/hora, usuário) em todas as páginas."""
        logo_caminho = self._caminho_logo()
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        usuario = str(usuario) if usuario else "Sistema"

        def _page(canvas, doc):
            # Moldura externa (mesmo do PDFBuilder.build)
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

            # Footer
            page_w, page_h = landscape(A4)
            footer_y = 10 * mm
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.grey)

            # Esquerda: logo
            if logo_caminho:
                try:
                    canvas.drawImage(
                        logo_caminho,
                        doc.leftMargin,
                        footer_y - 1 * mm,
                        width=10 * mm,
                        height=10 * mm,
                        mask="auto",
                        preserveAspectRatio=True,
                    )
                except Exception:
                    canvas.drawString(doc.leftMargin, footer_y, "SPS")

            # Centro: data/hora
            canvas.drawCentredString(page_w / 2, footer_y, f"Emitido em: {data_hora}")

            # Direita: usuário
            canvas.drawRightString(
                page_w - doc.rightMargin,
                footer_y,
                f"Usuário: {usuario}",
            )
            canvas.restoreState()

        pdf.doc.build(pdf.flow, onFirstPage=_page, onLaterPages=_page)
        return pdf.buffer
