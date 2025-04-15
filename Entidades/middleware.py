class EmpresaFilialMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_id = request.headers.get('X-Empresa')
        filial_id = request.headers.get('X-Filial')

        print(f'[MIDDLEWARE] X-Empresa: {empresa_id}')
        print(f'[MIDDLEWARE] X-Filial: {filial_id}')

        # Setar no request diretamente
        request.empresa_id = empresa_id
        request.filial_id = filial_id

        return self.get_response(request)
