from core.impressoes.base import BasePrinter

class PedidoPrinter(BasePrinter):
    title = "Pedido"
    
    def render_body(self, pdf):
        # Dados principais
        pdf.add_label_value("Data", self.modelo.ped_data)
        pdf.add_label_value("Cliente", self.modelo.ped_cliente)

        # Itens
        if self.itens:
            tabela = [["Descrição", "Qtd", "Valor"]]
            for i in self.itens:
                tabela.append([i.item_desc, i.item_qtd, i.item_valo])
            pdf.add_table(tabela, col_widths=[250, 80, 80])
