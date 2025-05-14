class BancoContextMixin:
    def get_banco(self):
        banco = self.context.get('banco') if hasattr(self, 'context') else None
        if not banco:
            raise Exception("Banco não definido no contexto.")
        return banco
