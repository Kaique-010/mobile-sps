from django.views import View
from django.http import JsonResponse, HttpResponse
from ...services.cnab_service import CNABService
from ...services.retorno_service import RetornoService


class GerarRemessaWebView(View):
    def post(self, request, pk):
        layout = request.POST.get('layout') or '240'
        banco_cfg = request.POST.get('banco_cfg')
        cedente = request.POST.get('cedente')
        titulos = request.POST.get('titulos') or []
        if not (banco_cfg and cedente and titulos):
            return HttpResponse('Dados insuficientes', status=400)
        def _to_titulo(d):
            return type('Titulo', (), d)()
        conteudo = CNABService().gerar_remessa(layout, banco_cfg, cedente, [_to_titulo(d) for d in titulos])
        return JsonResponse({'layout': layout, 'remessa': conteudo})


class ProcessarRetornoWebView(View):
    def post(self, request):
        caminho = request.POST.get('caminho')
        if not caminho:
            return HttpResponse('Caminho obrigatório', status=400)
        dados = RetornoService().processar(caminho)
        return JsonResponse({'retorno': dados})
