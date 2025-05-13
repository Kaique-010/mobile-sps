import base64
import logging
from Licencas.utils import atualizar_senha
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Licencas.models import Empresas, Filiais, Licencas, Usuarios
from Licencas.serializers import EmpresaSerializer, FilialSerializer
from django.contrib.auth.hashers import check_password
from core.middleware import get_licenca_slug
from core.registry import LICENCAS_MAP, get_licenca_db_config


def get_banco_por_docu(docu):
    from core.registry import LICENCAS_MAP
    match = next((x for x in LICENCAS_MAP if x['cnpj'] == docu), None)
    return match['slug'] if match else None


class LoginView(APIView):
    def post(self, request, slug=None):  
        data = request.data
        username = data.get("username")
        password = data.get("password")
        docu = data.get("docu")

        if not docu:
            return Response({'error': 'CNPJ não informado.'}, status=status.HTTP_400_BAD_REQUEST)

        banco = get_licenca_db_config()
        if not banco:
            return Response({'error': 'CNPJ inválido ou licença não encontrada.'}, status=404)

        licenca = Licencas.objects.using(banco).filter(lice_docu=docu).first()
        if not licenca or licenca.lice_bloq:
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=403)

        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome=username)
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=404)

        if usuario.password == password:
            return Response({'login': 'Login Ok.'}, status=200)

        refresh = RefreshToken.for_user(usuario)
        refresh['username'] = usuario.usua_nome
        refresh['usuario_id'] = usuario.usua_codi
        refresh['lice_id'] = licenca.lice_id
        refresh['lice_nome'] = licenca.lice_nome

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'username': usuario.usua_nome,
                'usuario_id': usuario.usua_codi,
            },
            'licenca': {
                'lice_id': licenca.lice_id,
                'lice_nome': licenca.lice_nome,
            }
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()  # Aqui você obtém o slug do contexto
        licenca_info = next((item for item in LICENCAS_MAP if item['slug'] == slug), None)

        if licenca_info:
            cnpj = licenca_info['cnpj']
            empresas = Empresas.objects.filter(empr_docu=cnpj)  # Busca empresas usando o CNPJ
            if empresas.exists():
                # Aqui você usa o serializer corretamente, com .data para pegar os dados serializados
                serializer = EmpresaSerializer(empresas, many=True)
                return Response(serializer.data)
            else:
                return Response({"error": "Nenhuma empresa encontrada para este CNPJ."}, status=404)
        else:
            return Response({"error": "Licença não encontrada."}, status=404)




class FiliaisPorEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Verificar se o 'empresa_id' foi passado na query string
        empresa_id = request.query_params.get('empresa_id')

        if not empresa_id:
            return Response({'error': 'Empresa não fornecida.'}, status=status.HTTP_400_BAD_REQUEST)

        # Aqui, vamos buscar filiais usando o campo correto, por exemplo 'empr_empr'
        filiais = Filiais.objects.filter(empr_empr=empresa_id)

        if not filiais:
            return Response({'error': 'Nenhuma filial encontrada para esta empresa.'}, status=status.HTTP_404_NOT_FOUND)

        # Serializar e retornar os dados das filiais
        serializer = FilialSerializer(filiais, many=True)
        return Response(serializer.data)


class AlterarSenhaView(APIView):
    permission_classes = [IsAuthenticated]  # Ou outra permissão que precisar

    def post(self, request):
        usuarioname = request.data.get('usuarioname')
        nova_senha = request.data.get('nova_senha')

        if not usuarioname or not nova_senha:
            return Response({"error": "usuarioname e nova senha são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Chama a função de utilitário para alterar a senha
            atualizar_senha(usuarioname, nova_senha)
            return Response({"message": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@api_view(['GET'])
def licencas_mapa(request, slug=None):
    
    
    # Retorna as licenças públicas sem depender de slug
    from core.licenca_context import LICENCAS_MAP
    return Response(LICENCAS_MAP)