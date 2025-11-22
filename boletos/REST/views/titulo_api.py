from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ...services.boleto_service import BoletoService
from ...services.validation_service import validate_boleto, build_barcode_data, linha_digitavel_from_barcode, validate_caixa_config
from ...models import Titulosreceber


class GerarBoletoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        cedente = request.data.get("cedente")
        sacado = request.data.get("sacado")
        banco_cfg = request.data.get("banco_cfg")
        caminho = request.data.get("caminho") or f"media/boletos/{pk}.pdf"

        titulo = None
        try:
            titulo = Titulosreceber.objects.get(pk=pk)
        except Exception:
            titulo = type("Titulo", (), request.data.get("titulo", {}))()

        if not (cedente and banco_cfg and sacado):
            return Response({"erro": "cedente, sacado e banco_cfg são obrigatórios"}, status=status.HTTP_400_BAD_REQUEST)

        if str(banco_cfg.get('codigo_banco')) == '104':
            cx = validate_caixa_config(banco_cfg)
            if not cx['ok']:
                return Response({"erro": "configuracao_caixa_invalida", "detalhes": cx['errors']}, status=status.HTTP_400_BAD_REQUEST)
        caminho_pdf = BoletoService().gerar_pdf(titulo, cedente, sacado, banco_cfg, caminho)
        v = validate_boleto(cedente, sacado, banco_cfg, titulo)
        codigo = build_barcode_data(banco_cfg, titulo)
        linha = linha_digitavel_from_barcode(codigo)
        return Response({"arquivo": caminho_pdf, "linha_digitavel": linha, "validacao": v}, status=status.HTTP_200_OK)


class ConsultarBoletoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        try:
            titulo = Titulosreceber.objects.get(pk=pk)
            status_bol = getattr(titulo, 'titu_situ', 'pendente')
            return Response({"status": status_bol, "numero": getattr(titulo, 'titu_titu', None)}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"status": "desconhecido", "numero": str(pk)}, status=status.HTTP_200_OK)


class CancelarBoletoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            titulo = Titulosreceber.objects.get(pk=pk)
            setattr(titulo, 'titu_situ', 'cancelado')
            titulo.save()
            return Response({"ok": True, "status": "cancelado"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"ok": False, "erro": "titulo_inexistente"}, status=status.HTTP_404_NOT_FOUND)
