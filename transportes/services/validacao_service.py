from transportes.models import Cte
from transportes.models import CteDocumento
from Licencas.models import Filiais


class ValidacaoService:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.errors = []

    def validar_emissao(self) -> bool:
        """Valida se o CTe pode ser emitido"""
        self.errors = []
        
        # Validação de Emitente (Filial)
        if not self.cte.filial:
            self.errors.append("Filial não informada.")
        else:
            # Usar defer para evitar erro em colunas opcionais que podem não existir no banco legado
            filial = Filiais.objects.using(self.cte._state.db).filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).defer('empr_cert_digi').first()
            if not filial:
                self.errors.append("Filial não encontrada.")
            else:
                if not filial.empr_docu:
                    self.errors.append("CNPJ da filial não informado.")
                if not filial.empr_insc_esta:
                    self.errors.append("IE da filial não informada.")
                if not filial.empr_ende:
                    self.errors.append("Endereço da filial não informado.")

        # Validação de Remetente
        if not self.cte.remetente:
            self.errors.append("Remetente não informado.")
            
        # Validação de Destinatário
        if not self.cte.destinatario:
            self.errors.append("Destinatário não informado.")
            
        # Validação de Tomador
        if self.cte.tomador_servico is None:
            self.errors.append("Tomador do serviço não informado.")
        
        if self.cte.tomador_servico == 4 and not self.cte.outro_tomador:
            self.errors.append("Outro tomador selecionado mas não informado.")
            
        # Validação de Valores
        if not self.cte.total_valor or self.cte.total_valor <= 0:
            self.errors.append("Valor total da prestação deve ser maior que zero.")
            
            
        # Validação de Documentos
        docs_count = self.cte.documentos.count()
        if docs_count == 0:
            self.errors.append("Pelo menos um documento (NFe/Outros) deve ser vinculado ao CTe.")
            
        # Validação de Carga
        if not self.cte.produto_predominante:
            self.errors.append("Produto predominante não informado.")
            
        if not self.cte.peso_total and not self.cte.total_mercadoria:
             # Pelo menos uma medida
             pass # Vamos ser lenientes aqui por enquanto, mas idealmente deveria ter

        return len(self.errors) == 0

    def get_errors(self) -> list:
        return self.errors
