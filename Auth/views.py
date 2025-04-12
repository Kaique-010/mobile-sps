from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Auth.models import Empresas, Filiais, UserEmpresaFilial
from Auth.serializers import EmpresaSerializer, FilialSerializer

# View de Login
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        print(f'\n[LOGIN] Requisição recebida: {request.data}')

        user = authenticate(request, username=username.lower(), password=password)

        if user:
            print(f'[LOGIN] Usuário autenticado com sucesso: {user.ucusername}')

            # Cria um token manualmente com o payload necessário
            refresh = RefreshToken()
            refresh['username'] = user.ucusername
            refresh['email'] = user.ucemail
            refresh['uciduser'] = user.uciduser  # ID personalizado

            access_token = refresh.access_token
            access_token.set_exp(lifetime=api_settings.ACCESS_TOKEN_LIFETIME) 

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


# View de Lista de Empresas (para admin)
class EmpresaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresas = Empresas.objects.all()
        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)


# View de Lista de Filiais (para admin)
class FilialListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa_id = request.query_params.get('empresa', None)
        user = request.user  # Usuário autenticado
        
        if empresa_id:
            # Filtrando as filiais que o usuário tem acesso, através da tabela auxiliar
            user_empresa_filiais = UserEmpresaFilial.objects.filter(user=user, empresa_id=empresa_id)
            
            # Filtra as filiais corretas com base no campo 'empr_codi'
            filiais = Filiais.objects.filter(empr_codi__in=[uef.filial_id for uef in user_empresa_filiais])
            
            serializer = FilialSerializer(filiais, many=True)
            return Response(serializer.data)
        
        return Response({"error": "Empresa não fornecida."}, status=status.HTTP_400_BAD_REQUEST)


# View de Empresas Associadas ao Usuário Logado
class EmpresasDoUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresas = Empresas.objects.filter(
            usuarios_empresas__user=user
        ).distinct()
        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)


# View de Filiais de uma Empresa para o Usuário Logado
class FiliaisDaEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa_id = request.query_params.get('empresa', None)
        user = request.user  # Usuário autenticado
        
        if empresa_id:
            # Filtrando as filiais que o usuário tem acesso, através da tabela auxiliar
            user_empresa_filiais = UserEmpresaFilial.objects.filter(user=user, empresa_id=empresa_id)
            filiais = Filiais.objects.filter(id__in=[uef.filial_id for uef in user_empresa_filiais])
            serializer = FilialSerializer(filiais, many=True)
            return Response(serializer.data)
        
        return Response({"error": "Empresa não fornecida."}, status=status.HTTP_400_BAD_REQUEST)


# View para Associar o Usuário à Empresa e Filial
class SetEmpresaFilialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        empresa_id = request.data.get('empresa')
        filial_id = request.data.get('filial')

        if not empresa_id or not filial_id:
            return Response({'error': 'Empresa ou Filial não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar se o usuário já está associado à empresa e filial
        if UserEmpresaFilial.objects.filter(user=user, empresa_id=empresa_id, filial_id=filial_id).exists():
            return Response({'error': 'Usuário já está associado a essa empresa e filial.'}, status=status.HTTP_400_BAD_REQUEST)

        # Criar a associação
        UserEmpresaFilial.objects.create(user=user, empresa_id=empresa_id, filial_id=filial_id)
        return Response({'message': 'Associação criada com sucesso!'}, status=status.HTTP_201_CREATED)
