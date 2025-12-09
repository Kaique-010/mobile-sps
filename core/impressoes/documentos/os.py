# core/printing/documents/ordem_servico.py
from core.impressoes.base import BasePrinter

class OrdemServicoPrinter(BasePrinter):
    title = "Ordem de Serviço"

    def render_body(self, pdf):
        filial_nome = getattr(self.filial, "empr_fant", None) or getattr(self.filial, "empr_nome", "")
        filial_doc = getattr(self.filial, "empr_docu", "")
        left_header = [[filial_nome], [f"CNPJ: {filial_doc}"], [""]]
        right_header = [["ORDEM DE LOCAÇÃO"], [f"Nº {self.documento}"]]
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        lh = Table(left_header, colWidths=[500])
        rh = Table(right_header, colWidths=[260])
        lh.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.7, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONT', (0,0), (-1,-1), 'Helvetica', 12),
        ]))
        rh.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.7, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 12),
            ('FONT', (0,1), (-1,-1), 'Helvetica', 12),
        ]))
        outer = Table([[lh, rh]], colWidths=[500, 260])
        outer.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        pdf.flow.append(outer)
        pdf.add_spacer(10)

        cliente_nome = getattr(self.cliente, "enti_nome", "")
        local_trabalho = getattr(self.modelo, "os_loca_apli", "") or getattr(self.modelo, "os_ende_apli", "")
        equipamento = getattr(self.modelo, "os_moto", "") or getattr(self.modelo, "os_auto", "")
        placa = getattr(self.modelo, "os_plac", "") or getattr(self.modelo, "os_plac_1", "")
        campos_topo = [
            ["Cliente:", cliente_nome, "Equipamento:", equipamento],
            ["Local de Trabalho:", local_trabalho, "Placa:", placa],
        ]
        pdf.add_table(campos_topo, col_widths=[90, 410, 90, 170])

        horas_header = ["Data", "Início", "Fim", "Início", "Fim", "Total"]
        horas_data = [horas_header]
        def fmt_date(d):
            try:
                return d.strftime("%d/%m/%Y") if d else ""
            except Exception:
                return str(d) if d else ""
        def fmt_time(t):
            try:
                return t.strftime("%H:%M") if t else ""
            except Exception:
                return str(t) if t else ""
        total_horas = 0
        km_saida = ""
        km_chegada = ""
        for h in self.horas or []:
            if km_saida == "" and getattr(h, "os_hora_km_sai", None):
                km_saida = getattr(h, "os_hora_km_sai", "")
            if getattr(h, "os_hora_km_che", None):
                km_chegada = getattr(h, "os_hora_km_che", "")
            total_horas += float(getattr(h, "os_hora_tota", 0) or 0)
            horas_data.append([
                fmt_date(getattr(h, "os_hora_data", None)),
                fmt_time(getattr(h, "os_hora_manh_ini", None)),
                fmt_time(getattr(h, "os_hora_manh_fim", None)),
                fmt_time(getattr(h, "os_hora_tard_ini", None)),
                fmt_time(getattr(h, "os_hora_tard_fim", None)),
                str(getattr(h, "os_hora_tota", "")),
            ])
        pdf.add_table(horas_data, col_widths=[80, 70, 70, 70, 70, 80])

        pdf.add_table([["Total Horas", str(total_horas)]], col_widths=[150, 150])

        discr_data = [["DISCRIMINAÇÃO DOS SERVIÇOS", ""]]
        for s in self.servicos or []:
            desc = getattr(s, "serv_obse", None) or getattr(s, "serv_prod", "")
            discr_data.append([desc, ""])
        pdf.add_table(discr_data, col_widths=[520, 240])

        obs = getattr(self.modelo, "os_obse", "") or ""
        pdf.add_table([["OBS:", obs]], col_widths=[60, 700])

        minimo_horas = getattr(self.modelo, "os_hori", "")
        total_rs = getattr(self.modelo, "os_tota", 0) or 0
        left_summary = [
            ["Mínimo de Horas:", f"{minimo_horas} hs"],
            ["Horas Trabalhadas:", f"{total_horas} hs"],
            ["Valor Total de Horas:", ""],
            ["Valor Hora: R$", ""],
            ["Valor Desl.: R$", ""],
            ["Km Saída:", str(km_saida)],
            ["Km Chegada:", str(km_chegada)],
            ["TOTAL", f"R$ {total_rs}"],
        ]
        right_block = [
            ["Recebi os serviços constantes Nesta Ordem de Locação"],
            ["Solicitante:"],
            ["Resp. em Campo:"],
            ["Função:"],
            ["Assinatura:"],
            ["Operador:"],
        ]
        from reportlab.platypus import Table
        ls = Table(left_summary, colWidths=[160, 240])
        rb = Table(right_block, colWidths=[260])
        outer2 = Table([[ls, rb]], colWidths=[420, 260])
        pdf.add_table([[ls, rb]], col_widths=[520, 240])
