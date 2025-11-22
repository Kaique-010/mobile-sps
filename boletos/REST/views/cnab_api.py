from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ...services.cnab_service import CNABService
from ...services.retorno_service import RetornoService


class GerarRemessaAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        layout = str(request.data.get("layout", "240"))
        banco_cfg = request.data.get("banco_cfg")
        cedente = request.data.get("cedente")
        titulos_data = request.data.get("titulos", [])

        if not (banco_cfg and cedente and titulos_data):
            return Response({"erro": "banco_cfg, cedente e titulos são obrigatórios"}, status=status.HTTP_400_BAD_REQUEST)

        def _to_titulo(d):
            return type("Titulo", (), d)()

        titulos = [_to_titulo(d) for d in titulos_data]
        conteudo = CNABService().gerar_remessa(layout, banco_cfg, cedente, titulos)
        return Response({"layout": layout, "remessa": conteudo}, status=status.HTTP_200_OK)


class ProcessarRetornoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        caminho = request.data.get("caminho")
        if not caminho:
            return Response({"erro": "caminho do arquivo de retorno é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        dados = RetornoService().processar(caminho)
        return Response({"retorno": dados}, status=status.HTTP_200_OK)
