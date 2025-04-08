from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('ucusername')
        password = request.data.get('ucpassword')
        print(f'\n[LOGIN] Requisição recebida: {request.data}')

        # Tenta autenticar com o backend personalizado
        user = authenticate(request, username=username, password=password)

        if user:
            print(f'[LOGIN] Usuário autenticado com sucesso: {user.ucusername}')

            # Gera os tokens JWT
            refresh = RefreshToken.for_user(user)
            print(f'[LOGIN] Token JWT gerado para: {user.ucusername}')

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'username': user.ucusername,
                    
                }
            })
        else:
            print('[LOGIN] Falha na autenticação. Credenciais inválidas.')
            return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

