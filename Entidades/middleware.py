class EmpresaFilialMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_id = request.headers.get('X-Empresa')
        filial_id = request.headers.get('X-Filial')

        print(f'[MIDDLEWARE] X-Empresa: {empresa_id}')
        print(f'[MIDDLEWARE] X-Filial: {filial_id}')

        try:
            request.empresa_id = int(empresa_id) if empresa_id is not None else None
            request.filial_id = int(filial_id) if filial_id is not None else None
        except ValueError:
            request.empresa_id = None
            request.filial_id = None

        return self.get_response(request)
