from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from Licencas.utils import get_licenca_slug
from dashboards.utils import enviar_email



class EnviarEmail(APIView):
    def post(self, request, slug = None ):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        email = request.data.get('email')
        dados = request.data.get('dados')
        
        if not email or not dados:
            return Response({'erro': 'Email e dados são obrigatórios'}, status= 400)
        
        enviado = enviar_email(email, dados)
        
        if enviado:
            return Response({'mensagem': 'E-mail enviado com sucesso'})
        return Response({'erro': 'Falha ao enviar o e-mail.'}, status=500)