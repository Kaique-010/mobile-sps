from Licencas.utils import atualizar_senha
from pprint import pprint
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from Licencas.models import Empresas, Filiais, Licencas, Usuarios
from Licencas.serializers import EmpresaSerializer, FilialSerializer, UsuarioSerializer
from parametros_admin.models import PermissaoModulo, Modulo
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django.contrib.auth.hashers import check_password
from core.middleware import get_licenca_slug
from core.registry import LICENCAS_MAP, get_licenca_db_config, get_modulos_por_docu
from parametros_admin.utils import  get_modulos_globais, get_codigos_modulos_liberados
from Licencas.permissions import UsuariosPermission
import time
import logging

logger = logging.getLogger(__name__)


def get_banco_por_docu(docu):
    from core.registry import LICENCAS_MAP
    match = next((x for x in LICENCAS_MAP if x['cnpj'] == docu), None)
    return match['slug'] if match else None


class LoginView(APIView):
    
    def post(self, request, slug=None):  
        start_time = time.time()
        logger.info(f"[LOGIN] Iniciando login para slug: {slug}")
        
        data = request.data
        username = data.get("username")
        password = data.get("password")
        docu = data.get("docu")
        empresa_id = data.get("empresa_id", 1)  
        filial_id = data.get("filial_id", 1)    
        
        if not docu:
            return Response({'error': 'CNPJ não informado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Log: Buscar configuração do banco
        db_start = time.time()
        banco = get_licenca_db_config(request)
        db_time = (time.time() - db_start) * 1000
        logger.info(f"[LOGIN] get_licenca_db_config: {db_time:.2f}ms")
        
        if not banco:
            return Response({'error': 'CNPJ inválido ou licença não encontrada.'}, status=404)

        # Log: Buscar licença
        licenca_start = time.time()
        licenca = Licencas.objects.using(banco).filter(lice_docu=docu).first()
        licenca_time = (time.time() - licenca_start) * 1000
        logger.info(f"[LOGIN] Buscar licença: {licenca_time:.2f}ms")
        
        if not licenca :
            return Response({'error': 'CNPJ inválido ou licença bloqueada.'}, status=403)

        # Log: Buscar usuário
        user_start = time.time()
        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome__iexact=username)
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=404)
        user_time = (time.time() - user_start) * 1000
        logger.info(f"[LOGIN] Buscar usuário: {user_time:.2f}ms")

        # Log: Validar senha
        password_start = time.time()
        if not usuario.check_password(password):
            return Response({'error': 'Senha incorreta.'}, status=401)
        password_time = (time.time() - password_start) * 1000
        logger.info(f"[LOGIN] Validar senha: {password_time:.2f}ms")

        # REMOVIDO: Query desnecessária de módulos globais
        # modulos_globais = list(get_modulos_globais(banco))
        
        # Para o login, retornamos apenas uma lista vazia
        # Os módulos reais serão carregados após seleção da empresa/filial
        modulos_login = []  # Não retornar módulos no login

        # Log: Gerar token JWT
        jwt_start = time.time()
        refresh = RefreshToken.for_user(usuario)
        refresh['username'] = usuario.usua_nome
        refresh['usuario_id'] = usuario.usua_codi
        refresh['setor'] = usuario.usua_seto  # Adicionar setor do usuário
        refresh['lice_id'] = licenca.lice_id
        refresh['lice_nome'] = licenca.lice_nome
        refresh['empresa_id'] = empresa_id
        refresh['filial_id'] = filial_id
        jwt_time = (time.time() - jwt_start) * 1000
        logger.info(f"[LOGIN] Gerar JWT: {jwt_time:.2f}ms")

        total_time = (time.time() - start_time) * 1000
        logger.info(f"[LOGIN] TOTAL: {total_time:.2f}ms para usuário {username}")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'username': usuario.usua_nome,
                'usuario_id': usuario.usua_codi,
                'setor': usuario.usua_seto,  # Adicionar setor na resposta
                'empresa_id': empresa_id,
                'filial_id': filial_id,
            },
            'licenca': {
                'lice_id': licenca.lice_id,
                'lice_nome': licenca.lice_nome,
            },
            'modulos': modulos_login,
        })


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()
        licenca_info = next((item for item in LICENCAS_MAP if item['slug'] == slug), None)

        if not licenca_info:
            return Response({"error": "Licença não encontrada."}, status=404)

        # Garantir que estamos consultando no mesmo banco da licença selecionada
        banco = get_licenca_db_config(request)
        empresas = Empresas.objects.using(banco).all()
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

        banco = get_licenca_db_config(request)

        # Aceitar CNPJ (empr_docu) ou empresa_id. Prioridade para empr_docu.
        empr_docu = request.query_params.get('empr_docu')
        empresa_id = request.query_params.get('empresa_id')

        if not empr_docu and not empresa_id:
            return Response({'error': 'Informe empr_docu (CNPJ) ou empresa_id.'}, status=status.HTTP_400_BAD_REQUEST)

        # Se CNPJ fornecido, usar para localizar empresa e suas filiais
        if empr_docu:
            docu_sanit = ''.join(ch for ch in str(empr_docu) if ch.isdigit())
            empresa = Empresas.objects.using(banco).filter(empr_docu=docu_sanit).first()
            if not empresa:
                return Response({'error': 'Empresa com CNPJ não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            empresa_codi = empresa.empr_codi
            origem_id = 'cnpj'
        else:
            # Fallback: empresa_id (código numérico)
            try:
                empresa_id_int = int(empresa_id)
            except (TypeError, ValueError):
                return Response({'error': 'empresa_id inválido.'}, status=status.HTTP_400_BAD_REQUEST)

            # Primeiro, considerar que empresa_id é o código da empresa (Empresas.empr_codi)
            empresa_existe = Empresas.objects.using(banco).filter(empr_codi=empresa_id_int).exists()

            # Se não existir, tentar interpretar empresa_id como código de filial (Filiais.empr_empr)
            if empresa_existe:
                empresa_codi = empresa_id_int
                origem_id = 'empresa'
            else:
                filial = Filiais.objects.using(banco).filter(empr_empr=empresa_id_int).first()
                if filial:
                    empresa_codi = filial.empr_codi_id
                    origem_id = 'filial->empresa'
                else:
                    return Response({'error': 'Empresa/filial não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        filiais = Filiais.objects.using(banco).filter(empr_codi_id=empresa_codi).order_by('empr_empr')
        logger.info(f"[FILIAIS] Origem={origem_id} empresa_codi={empresa_codi} total={filiais.count()}")

        # Serializar e retornar os dados das filiais
        serializer = FilialSerializer(filiais, many=True)
        return Response(serializer.data)

class ModulosLiberadosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(request)
        empresa_id = request.query_params.get('empresa_id')
        filial_id = request.query_params.get('filial_id')

        if not empresa_id or not filial_id:
            return Response({'error': 'Empresa e filial obrigatórias'}, status=400)

        modulos_ids = get_codigos_modulos_liberados(banco, empresa_id, filial_id)
        pprint(modulos_ids)

        return Response({'modulos_liberados': modulos_ids})


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


class UsuariosViewSet(viewsets.ModelViewSet):
    queryset = Usuarios.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, UsuariosPermission]
    ordering_fields = ['usua_codi']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return Usuarios.objects.using(banco).all().order_by('usua_codi')
    
    def create(self, request, slug=None):
        banco = get_licenca_db_config(request)
        serializer = UsuarioSerializer(data=request.data, context={'banco': banco})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
