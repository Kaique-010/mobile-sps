from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from Licencas.utils import get_licenca_slug
from .utils import enviar_whatsapp
  

class EnviarWhatsapp(APIView):
    def post(self, request, slug = None ):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        cliente_id = request.data.get('cliente_id')
        dados = request.data.get('dados')
        
        if not cliente_id or not dados:
            return Response({'erro': 'ID do Cliente e dados são obrigatórios'}, status= 400)
        
        enviado, mensagem = enviar_whatsapp(cliente_id, dados)
        
        if enviado:
            return Response({'mensagem': mensagem})
        
        # Se falhou, retorna 400 ou 404 dependendo da mensagem, mas vamos simplificar com 400
        # ou 404 se não encontrado
        status_code = status.HTTP_404_NOT_FOUND if "não encontrado" in mensagem else status.HTTP_400_BAD_REQUEST
        return Response({'erro': mensagem}, status=status_code)