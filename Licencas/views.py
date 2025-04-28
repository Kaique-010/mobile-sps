import base64
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import connections
from rest_framework import status
from django.contrib.auth import authenticate
from core.db_config import get_dynamic_db_config
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Licencas.models import Empresas, Filiais, Licencas, Usuarios
from Licencas.serializers import EmpresaSerializer, FilialSerializer

# Logger
logger = logging.getLogger(__name__)

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
            logger.warning(f"Login falhou: CNPJ não informado. Username tentado: {username}")
            return Response({'error': 'CNPJ não informado.'}, status=status.HTTP_400_BAD_REQUEST)

        licenca = Licencas.objects.filter(lice_docu=docu).first()
        if not licenca:
            logger.warning(f"Login falhou: CNPJ inválido ({docu}). Username tentado: {username}")
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=status.HTTP_404_NOT_FOUND)

        lice_nome = f'saa_{licenca.lice_id}_{licenca.lice_nome}'.lower().replace(' ', '_')
        db_config = get_dynamic_db_config(docu)
        db_alias = f'db_{lice_nome}'

        connections.databases[db_alias] = db_config
        connections[db_alias].connect()

        try:
            with connections[db_alias].cursor() as cursor:
                user = Usuarios.objects.using(db_alias).get(usua_nome=username.lower())
        except Usuarios.DoesNotExist:
            logger.warning(f"Login falhou: Usuário não encontrado ({username}) no banco {db_alias}.")
            return Response({'error': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(password):
            logger.warning(f"Login falhou: Senha inválida para usuário {username} no banco {db_alias}.")
            return Response({'error': 'Senha inválida.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Gerar o refresh token
        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.usua_nome
        refresh['user_id'] = user.usua_codi
        refresh['lice_id'] = licenca.lice_id
        refresh['lice_nome'] = lice_nome

        # Gerar o access token
        access_token = refresh.access_token

        logger.info(f"Login bem-sucedido: Usuário {username} autenticado no banco {db_alias}.")

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
                'banco': lice_nome,
            }
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresas = Empresas.objects.all()
        logger.info(f"Listagem de empresas solicitada por usuário {user}.")
        serializer = EmpresaSerializer(empresas, many=True)
        return Response(serializer.data)


class FiliaisPorEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            logger.warning(f"Consulta de filiais falhou: Empresa não fornecida. Usuário: {request.user}")
            return Response({'error': 'Empresa não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)

        filiais = Filiais.objects.filter(empr_empr=empresa_id)

        if not filiais:
            logger.warning(f"Nenhuma filial encontrada para empresa {empresa_id}. Usuário: {request.user}")
            return Response({'error': 'Nenhuma filial encontrada para esta empresa.'}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Listagem de filiais da empresa {empresa_id} solicitada por usuário {request.user}.")
        serializer = FilialSerializer(filiais, many=True)
        return Response(serializer.data)


