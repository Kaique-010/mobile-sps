from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Auth.models import Empresas, Filiais, Licencas
from Auth.serializers import EmpresaSerializer, FilialSerializer


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        docu = request.data.get('docu')  # CNPJ

        # Verifica licença válida
        licenca = Licencas.objects.filter(lice_docu=docu, lice_bloq=False).first()
        if not licenca:
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=status.HTTP_404_NOT_FOUND)

        # Autenticação
        user = authenticate(request, username=username.lower(), password=password)
        if not user:
            return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Checa se o usuário está vinculado à licença
        if user.lice_id != licenca.lice_id:
            return Response({'error': 'Usuário não pertence a essa licença.'}, status=status.HTTP_403_FORBIDDEN)

        # Tokens
        refresh = RefreshToken()
        refresh['username'] = user.ucusername
        refresh['email'] = user.ucemail
        refresh['uciduser'] = user.uciduser
        refresh['lice_id'] = user.lice_id
        refresh['empresa_id'] = user.empr_codi
        refresh['filial_id'] = user.fili_codi
        refresh['db_name'] = f'saa_{user.lice_id}_{licenca.lice_nome}'.lower().replace(' ', '_')

        access_token = refresh.access_token
        access_token.set_exp(lifetime=api_settings.ACCESS_TOKEN_LIFETIME)

        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': {
                'username': user.ucusername,
                'email': user.ucemail,
                'uciduser': user.uciduser
            },
            'licenca': {
                'lice_id': licenca.lice_id,
                'lice_nome': licenca.lice_nome,
                'banco': refresh['db_name'],
            },
            'empresa': user.empr_codi,
            'filial': user.fili_codi,
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresa = Empresas.objects.filter(empr_codi=user.empr_codi).first()
        if not empresa:
            return Response({'error': 'Empresa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmpresaSerializer(empresa)
        return Response(serializer.data)


class FiliaisUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        filiais = Filiais.objects.filter(empr_codi=user.empr_codi)
        serializer = FilialSerializer(filiais, many=True)
        return Response(serializer.data)


class SetEmpresaFilialView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        empresa_id = request.data.get('empresa')
        filial_id = request.data.get('filial')

        if not empresa_id or not filial_id:
            return Response({'error': 'Empresa ou Filial não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)

        # Atualiza direto no user
        user.empr_codi = empresa_id
        user.fili_codi = filial_id
        user.save()

        return Response({'message': 'Empresa e filial atualizadas com sucesso!'})
