from django.views import View
from django.http import HttpResponse, JsonResponse
from ...services.boleto_service import BoletoService
from ...services.validation_service import build_barcode_data, linha_digitavel_from_barcode


class GerarBoletoWebView(View):
    def post(self, request, pk):
        cedente = request.POST.get('cedente')
        sacado = request.POST.get('sacado')
        banco_cfg = request.POST.get('banco_cfg')
        caminho = request.POST.get('caminho') or f"media/boletos/{pk}.pdf"
        if not (cedente and sacado and banco_cfg):
            return HttpResponse("Dados insuficientes", status=400)
        titulo = type('Titulo', (), {'titu_titu': str(pk)})()
        pdf = BoletoService().gerar_pdf(titulo, cedente, sacado, banco_cfg, caminho)
        codigo = build_barcode_data(banco_cfg, titulo)
        linha = linha_digitavel_from_barcode(codigo)
        return JsonResponse({'arquivo': pdf, 'linha_digitavel': linha})
