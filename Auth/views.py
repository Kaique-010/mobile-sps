import base64
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connections
import datetime
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from django.contrib.auth import authenticate
from core.db_config import get_dynamic_db_config
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Auth.models import Empresas, Filiais, Licencas, Usuarios  
from Auth.serializers import EmpresaSerializer, FilialSerializer


def check_legacy_hash(legacy_base64_hash, raw_password):
    try:
        decoded = base64.b64decode(legacy_base64_hash).decode('utf-8')
        return decoded == raw_password
    except Exception:
        return False


class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        docu = request.data.get('docu')

        if not docu:
            return Response({'error': 'CNPJ não informado.'}, status=status.HTTP_400_BAD_REQUEST)

        licenca = Licencas.objects.filter(lice_docu=docu).first()
        if not licenca:
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = Usuarios.objects.get(usua_nome=username.lower())
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(password):
            return Response({'error': 'Senha inválida.'}, status=status.HTTP_401_UNAUTHORIZED)

        # 🔥 Aqui é onde a mágica acontece
        refresh = RefreshToken.for_user(user)
        db_name = f'saa_{licenca.lice_id}_{licenca.lice_nome}'.lower().replace(' ', '_')

        # Custom payload
        refresh['username'] = user.usua_nome
        refresh['user_id'] = user.usua_codi
        refresh['lice_id'] = licenca.lice_id
        refresh['db_name'] = db_name

        access_token = refresh.access_token

        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': {
                'username': user.usua_nome,
                'user_id': user.usua_codi,
            },
            'licenca': {
                'lice_id': licenca.lice_id,
                'lice_nome': licenca.lice_nome,
                'banco': db_name,
            }
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  

        empresas = Empresas.objects.all()
        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)

class FiliaisPorEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')  # empresa_id é o parâmetro vindo da requisição
        if not empresa_id:
            return Response({'error': 'Empresa não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)

        # Alterando para o campo correto 'empr_empr' para filtrar pela empresa associada
        filiais = Filiais.objects.filter(empr_empr=empresa_id)  # Agora usamos 'empr_empr', que é a referência à empresa

        # Verificando se há filiais
        if not filiais:
            return Response({'error': 'Nenhuma filial encontrada para esta empresa.'}, status=status.HTTP_404_NOT_FOUND)

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

