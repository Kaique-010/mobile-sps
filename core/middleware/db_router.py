from django.utils.deprecation import MiddlewareMixin

class DynamicDBMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """
        Extrai o CNPJ (docu) do header ou JWT e coloca no request para que possa ser usado no settings.
        """
        docu = request.META.get('HTTP_CNPJ', None)  # O CNPJ pode estar no header como "CNPJ"
        
        if not docu:
            # Se não encontrar, pode lançar erro ou usar um valor padrão
            docu = 'SAVEXML'  # Ou qualquer outro valor padrão que você queira

        # Coloca o 'docu' no request para ser acessado no settings.py
        request.docu = docu
