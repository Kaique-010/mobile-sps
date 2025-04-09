# Auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.conf import settings
from rest_framework_simplejwt.settings import api_settings as jwt_settings

class LoginView(APIView):

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        print(f'\n[LOGIN] Requisição recebida: {request.data}')

        user = authenticate(request, username=username, password=password)

        if user:
            print(f'[LOGIN] Usuário autenticado com sucesso: {user.ucusername}')

            # Cria um token manualmente com o payload necessário
            refresh = RefreshToken()
            refresh['username'] = user.ucusername
            refresh['email'] = user.ucemail
            refresh['uciduser'] = user.uciduser  # ID personalizado

            access_token = refresh.access_token
            access_token.set_exp(lifetime=jwt_settings.ACCESS_TOKEN_LIFETIME)

            print(f'[LOGIN] Token JWT gerado para: {user.ucusername}')

            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
                'user': {
                    'username': user.ucusername,
                    'email': user.ucemail,
                }
            })
        else:
            print('[LOGIN] Falha na autenticação. Credenciais inválidas.')
            return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
