# Auth/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        print(f'\n[LOGIN] Requisição recebida: {request.data}')

        user = authenticate(request, username=username, password=password)

        if user:
            print(f'[LOGIN] Usuário autenticado com sucesso: {user.ucusername}')

            refresh = RefreshToken.for_user(user)  # ← isso só funciona se user for um User válido
            print(f'[LOGIN] Token JWT gerado para: {user.ucusername}')

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'username': user.ucusername,
                    'email': user.ucemail,
                }
            })
        else:
            print('[LOGIN] Falha na autenticação. Credenciais inválidas.')
            return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
