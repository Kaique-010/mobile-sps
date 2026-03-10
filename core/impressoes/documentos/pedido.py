from core.impressoes.base import BasePrinter

class PedidoPrinter(BasePrinter):
    title = "Pedido"
    
    def render_body(self, pdf):
        
        pdf.add_label_value("Número", self.modelo.pedi_nume)
        # Dados principais
        pdf.add_label_value("Data", self.modelo.pedi_data)
        pdf.add_label_value("Cliente", self.modelo.pedi_forn)
        pdf.add_label_value("Vendedor", self.modelo.pedi_vend)

        # Itens
        if self.itens:
            tabela = [["Cód.", "Descrição", "Qtd", "Valor", "Total"]]
            for i in self.itens:
                # Tenta obter nome do produto se disponível, senão usa código
                descricao = getattr(i, 'produto_nome', i.iped_prod)
                # Se i for uma instância de modelo, pode ter property 'produto'
                if hasattr(i, 'produto') and i.produto:
                    descricao = i.produto.prod_nome
                
                tabela.append([
                    i.iped_prod,
                    descricao, 
                    f"{i.iped_quan:.2f}", 
                    f"{i.iped_unit:.2f}",
                    f"{i.iped_tota:.2f}"
                ])
            pdf.add_table(tabela, col_widths=[80, 200, 60, 80, 80])
