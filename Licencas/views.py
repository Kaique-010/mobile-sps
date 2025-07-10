from Licencas.utils import atualizar_senha
from pprint import pprint
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Licencas.models import Empresas, Filiais, Licencas, Usuarios
from Licencas.serializers import EmpresaSerializer, FilialSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django.contrib.auth.hashers import check_password
from core.middleware import get_licenca_slug
from core.registry import LICENCAS_MAP, get_licenca_db_config, get_modulos_por_docu
from parametros_admin.utils import  get_modulos_liberados


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
        empresa_id = data.get("empresa_id", 1)  
        filial_id = data.get("filial_id", 1)    
        if not docu:
            return Response({'error': 'CNPJ não informado.'}, status=status.HTTP_400_BAD_REQUEST)

        banco = get_licenca_db_config(request)
        if not banco:
            return Response({'error': 'CNPJ inválido ou licença não encontrada.'}, status=404)

        licenca = Licencas.objects.using(banco).filter(lice_docu=docu).first()
        if not licenca :
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=403)

        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome=username)
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=404)

        if not usuario.check_password(password):
            return Response({'error': 'Senha incorreta.'}, status=401)

        # Buscar módulos liberados da tabela de permissões
        modulos_liberados = get_modulos_liberados(banco, empresa_id, filial_id)
        pprint({'Módulos Liberados': modulos_liberados})
        
        # Se não há módulos liberados na tabela, usar os da licença (fallback)
        if not modulos_liberados:
            modulos_liberados = [mod.lower().replace("_", "") for mod in get_modulos_por_docu(docu)]

        refresh = RefreshToken.for_user(usuario)
        refresh['username'] = usuario.usua_nome
        refresh['usuario_id'] = usuario.usua_codi
        refresh['lice_id'] = licenca.lice_id
        refresh['lice_nome'] = licenca.lice_nome
        refresh['empresa_id'] = empresa_id
        refresh['filial_id'] = filial_id

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'username': usuario.usua_nome,
                'usuario_id': usuario.usua_codi,
                'empresa_id': empresa_id,
                'filial_id': filial_id,
            },
            'licenca': {
                'lice_id': licenca.lice_id,
                'lice_nome': licenca.lice_nome,
            },
            'modulos': modulos_liberados,
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()
        licenca_info = next((item for item in LICENCAS_MAP if item['slug'] == slug), None)

        if not licenca_info:
            return Response({"error": "Licença não encontrada."}, status=404)

        empresas = Empresas.objects.all()
        if empresas.exists():
            serializer = EmpresaSerializer(empresas, many=True)
            return Response(serializer.data)
        else:
            return Response({"error": "Nenhuma empresa encontrada."}, status=404)




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
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        usuarioname = request.data.get('usuarioname')
        nova_senha = request.data.get('nova_senha')
        senha_atual = request.data.get('senha_atual')  # Para validação adicional

        if not usuarioname or not nova_senha:
            return Response({"error": "usuarioname e nova senha são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        # Validação básica da nova senha
        if len(nova_senha) < 4:
            return Response({"error": "A nova senha deve ter pelo menos 4 caracteres."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verificar se o usuário existe e se a senha atual está correta (se fornecida)
            banco = get_licenca_db_config(request)
            if banco:
                try:
                    usuario = Usuarios.objects.using(banco).get(usua_nome=usuarioname)
                    
                    # Se senha atual foi fornecida, validar
                    if senha_atual and not usuario.check_password(senha_atual):
                        return Response({"error": "Senha atual incorreta."}, status=status.HTTP_400_BAD_REQUEST)
                        
                except Usuarios.DoesNotExist:
                    return Response({"error": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)

            # Chama a função de utilitário para alterar a senha
            atualizar_senha(usuarioname, nova_senha, request)
            return Response({"message": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@api_view(['GET'])
def licencas_mapa(request, slug=None):
    
    
    # Retorna as licenças públicas sem depender de slug
    from core.licenca_context import LICENCAS_MAP
    return Response(LICENCAS_MAP)