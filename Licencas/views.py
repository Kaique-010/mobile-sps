from Licencas.utils import atualizar_senha
from pprint import pprint
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from Licencas.models import Empresas, Filiais, Licencas, Usuarios
from licencas_web.models import LicencaWeb
from Licencas.crypto import encrypt_bytes, encrypt_str
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from Licencas.serializers import EmpresaSerializer, FilialSerializer, UsuarioSerializer, EmpresaDetailSerializer, FilialDetailSerializer
from parametros_admin.models import PermissaoModulo, Modulo
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django.contrib.auth.hashers import check_password
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config, get_modulos_por_docu
from parametros_admin.utils import  get_modulos_globais, get_codigos_modulos_liberados
from Licencas.permissions import UsuariosPermission
import time
import logging
import uuid
from django.utils import timezone
import re
from django.db.models import Q
from core.cache_service import build_cache_key, cache_get_or_set

logger = logging.getLogger(__name__)
SETOR_OBRIGATORIO_SLUGS = {"savexml144", "saveweb144"}


def get_banco_por_docu(docu):
    from core.licenca_context import get_licencas_map
    docu_digits = re.sub(r"\D", "", str(docu or ""))
    match = next((x for x in get_licencas_map() if re.sub(r"\D", "", str(x.get('cnpj') or "")) == docu_digits), None)
    return match['slug'] if match else None


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _save_session_with_retry(self, request, request_id):
        for attempt in (1, 2):
            try:
                request.session.save()
                logger.info("[LOGIN][%s] sessão salva com sucesso (tentativa=%s)", request_id, attempt)
                return True
            except Exception as exc:
                logger.exception("[LOGIN][%s] falha ao salvar sessão (tentativa=%s): %s", request_id, attempt, exc)
                try:
                    request.session.cycle_key()
                except Exception:
                    logger.exception("[LOGIN][%s] cycle_key falhou durante retry de sessão", request_id)
        return False
    
    def post(self, request, slug=None):  
        start_time = time.time()
        request_id = uuid.uuid4().hex[:10]
        logger.info("[LOGIN][%s] início slug_param=%s", request_id, slug)
        
        data = request.data
        username = data.get("username")
        password = data.get("password")
        docu = data.get("docu")
        empresa_id = data.get("empresa_id", 1)  
        filial_id = data.get("filial_id", 1)    
        
        if not docu:
            return Response({'error': 'CPF/CNPJ não informado. Deve ser obrigatoriamente informado.'}, status=status.HTTP_400_BAD_REQUEST)

        docu_digits = re.sub(r"\D", "", str(docu))
        if len(docu_digits) not in (11, 14):
            return Response({'error': 'CPF/CNPJ inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        slug_key = build_cache_key("licencas_login", "slug_por_docu", docu_digits)
        slug_from_docu, slug_hit = cache_get_or_set(
            key=slug_key,
            timeout=600,
            factory=lambda: get_banco_por_docu(docu_digits),
            logger_instance=logger,
        )
        logger.info("[LOGIN][%s] slug_resolvido=%s cache_hit=%s", request_id, slug_from_docu, slug_hit)
        if not slug_from_docu:
            return Response({'error': 'CPF/CNPJ inválido ou licença não encontrada.'}, status=404)

        # Log: Buscar configuração do banco
        db_start = time.time()
        try:
            banco = get_licenca_db_config(slug_from_docu)
        except Exception as e:
            logger.error(f"[LOGIN][{request_id}] Erro ao obter config do banco: {e}")
            return Response({'error': f'Erro na configuração da licença: {str(e)}'}, status=500)
            
        db_time = (time.time() - db_start) * 1000
        logger.debug(f"[LOGIN][{request_id}] get_licenca_db_config: {db_time:.2f}ms")
        
        if not banco:
            return Response({'error': 'CPF/CNPJ inválido ou licença não encontrada.'}, status=404)

        # Log: Buscar licença
        licenca_start = time.time()
        try:
            licenca_key = build_cache_key("licencas_login", banco, "licenca_docu", docu_digits)
            licenca_payload, licenca_hit = cache_get_or_set(
                key=licenca_key,
                timeout=300,
                factory=lambda: (
                    Licencas.objects.using(banco)
                    .filter(lice_docu=docu_digits)
                    .values('lice_id', 'lice_nome')
                    .first()
                ),
                logger_instance=logger,
            )
            logger.info("[LOGIN][%s] licenca_lookup cache_hit=%s encontrado=%s", request_id, licenca_hit, bool(licenca_payload))
            licenca = licenca_payload
        except Exception:
            licenca = None
            
        # LicencaWeb fica no banco default (gerenciador)
        licenca_web = LicencaWeb.objects.using('default').select_related('plano').filter(Q(cnpj=docu_digits) | Q(cnpj=str(docu))).first()
        
        if licenca_web:
            try:
                plano = licenca_web.plano
            except Exception:
                plano = None
                logger.warning(f"[LOGIN] plano órfão ou deletado para licença {licenca_web.slug} — bloqueio ignorado")

            if plano and plano.plan_trial:
                if plano.plan_ativ and plano.plan_data_expi:
                    if timezone.now() > plano.plan_data_expi:
                        plano.plan_ativ = False
                        plano.save(update_fields=['plan_ativ'])
                        logger.warning(f"[LOGIN] Trial expirado on-the-fly — licença {licenca_web.slug}")

                if not plano.plan_ativ:
                    logger.warning(f"[LOGIN] Trial desativado — licença {licenca_web.slug}, deseja prosseguir com o contrato?")
                    
                    return Response(
                        {
                            'error': 'Seu período de trial expirou. Entre em contato com o suporte.',
                            'plan_data_expi': plano.plan_data_expi,
                            'code': 'trial_expirado',
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                    
            
        licenca_time = (time.time() - licenca_start) * 1000
        logger.debug(f"[LOGIN][{request_id}] Buscar licença: {licenca_time:.2f}ms")
        
        if not licenca and not licenca_web:
            return Response({'error': 'CPF/CNPJ inválido ou licença bloqueada.'}, status=403)

        # Log: Buscar usuário
        user_start = time.time()
        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome__iexact=username)
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=404)
        except Exception as e:
            logger.error(f"[LOGIN][{request_id}] Erro ao buscar usuário no banco {banco}: {e}")
            return Response({'error': f'Erro ao conectar no banco da empresa: {str(e)}'}, status=500)
        
        user_time = (time.time() - user_start) * 1000
        logger.debug(f"[LOGIN][{request_id}] Buscar usuário: {user_time:.2f}ms")

        # Log: Validar senha
        password_start = time.time()
        if not usuario.check_password(password):
            return Response({'error': 'Senha incorreta.'}, status=401)
        password_time = (time.time() - password_start) * 1000
        logger.debug(f"[LOGIN][{request_id}] Validar senha: {password_time:.2f}ms")

        # REMOVIDO: Query desnecessária de módulos globais
        # modulos_globais = list(get_modulos_globais(banco))
        
        # Para o login, retornamos apenas uma lista vazia
        # Os módulos reais serão carregados após seleção da empresa/filial
        modulos_login = []  # Não retornar módulos no login

        try:
            empresa_id_int = int(str(empresa_id).strip())
        except Exception:
            empresa_id_int = 1
        try:
            filial_id_int = int(str(filial_id).strip())
        except Exception:
            filial_id_int = 1

        setor_claim = getattr(usuario, "usua_seto", None)
        if setor_claim in ("", 0):
            setor_claim = None
        if slug_from_docu in SETOR_OBRIGATORIO_SLUGS and setor_claim is None:
            logger.warning("[LOGIN][%s] bloqueado: usuário sem setor em slug obrigatório (%s)", request_id, slug_from_docu)
            return Response(
                {'error': 'Usuário sem setor vinculado para esta licença.', 'request_id': request_id},
                status=status.HTTP_403_FORBIDDEN,
            )
        if setor_claim is None:
            setor_claim = 0

        jwt_start = time.time()
        refresh = RefreshToken.for_user(usuario)
        refresh['username'] = usuario.usua_nome
        refresh['usuario_id'] = usuario.usua_codi
        refresh['setor'] = setor_claim
        
        if licenca:
            refresh['lice_id'] = licenca.get('lice_id')
            refresh['lice_nome'] = licenca.get('lice_nome')
        elif licenca_web:
            refresh['lice_id'] = licenca_web.id
            refresh['lice_nome'] = licenca_web.slug
            
        refresh['empresa_id'] = empresa_id_int
        refresh['filial_id'] = filial_id_int
        refresh['lice_slug'] = slug_from_docu
        access = refresh.access_token
        access['lice_slug'] = slug_from_docu
        try:
            request.session.cycle_key()
        except Exception:
             logger.exception("[LOGIN][%s] cycle_key falhou", request_id)
        request.session["usua_codi"] = usuario.usua_codi
        request.session["docu"] = docu_digits
        request.session["slug"] = slug_from_docu if slug_from_docu else request.session.get('slug')
        request.session["empresa_id"] = empresa_id_int
        request.session["filial_id"] = filial_id_int
        request.session.modified = True
        session_ok = self._save_session_with_retry(request, request_id)
        logger.info(
            "[LOGIN][%s] sessão=%s snapshot=%s",
            request_id,
            "OK" if session_ok else "FALHA",
            {k: request.session.get(k) for k in ['usua_codi', 'docu', 'slug', 'empresa_id', 'filial_id']},
        )
        if not session_ok:
            logger.error("[LOGIN][%s] abortado: sessão não persistiu após retries", request_id)
            return Response(
                {
                    'error': 'Falha ao persistir sessão. Tente novamente.',
                    'request_id': request_id,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        access['username'] = usuario.usua_nome
        access['usuario_id'] = usuario.usua_codi
        access['setor'] = setor_claim
        
        if licenca:
            access['lice_id'] = licenca.get('lice_id')
            access['lice_nome'] = licenca.get('lice_nome')
        elif licenca_web:
            access['lice_id'] = licenca_web.id
            access['lice_nome'] = licenca_web.slug

        access['empresa_id'] = empresa_id_int
        access['filial_id'] = filial_id_int
        logger.debug(f"[LOGIN][{request_id}] Token claims: setor refresh={refresh.get('setor')} access={access.get('setor')}")
        jwt_time = (time.time() - jwt_start) * 1000
        logger.debug(f"[LOGIN][{request_id}] Gerar JWT: {jwt_time:.2f}ms")

        total_time = (time.time() - start_time) * 1000
        logger.info(f"[LOGIN][{request_id}] TOTAL: {total_time:.2f}ms para usuário {username}")
        try:
            logger.debug("[TRACE][LOGIN][%s] slug=%s banco=%s empresa=%s filial=%s user_id=%s", request_id, slug_from_docu, banco, empresa_id, filial_id, usuario.usua_codi)
        except Exception:
            pass

        return Response({
            'request_id': request_id,
            'access': str(access),
            'refresh': str(refresh),
                'usuario': {
                    'username': usuario.usua_nome,
                    'usuario_id': usuario.usua_codi,
                    'setor': setor_claim,
                    'empresa_id': empresa_id_int,
                    'filial_id': filial_id_int,
                },
            'licenca': {
                'lice_id': licenca.get('lice_id') if licenca else (licenca_web.id if licenca_web else None),
                'lice_nome': licenca.get('lice_nome') if licenca else (licenca_web.slug if licenca_web else None),
            },
            'modulos': modulos_login,
        })
        

class TokenRefreshCustomView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        try:
            raw_refresh = request.data.get('refresh')
            if not raw_refresh:
                return Response({'error': 'refresh ausente'}, status=400)
            rt = RefreshToken(raw_refresh)
            acc = rt.access_token
            for k in ['username','usuario_id','setor','lice_id','lice_nome','empresa_id','filial_id','lice_slug']:
                try:
                    acc[k] = rt.get(k)
                except Exception:
                    pass
            return Response({
                'access': str(acc),
                'usuario': {
                    'username': rt.get('username', None),
                    'usuario_id': rt.get('usuario_id', None),
                    'setor': rt.get('setor', None),
                },
                'licenca': {
                    'lice_id': rt.get('lice_id', None),
                    'lice_nome': rt.get('lice_nome', None),
                },
                'contexto': {
                    'empresa_id': rt.get('empresa_id', None),
                    'filial_id': rt.get('filial_id', None),
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class EmpresaUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()
        from core.licenca_context import get_licencas_map
        licenca_info = next((item for item in get_licencas_map() if item['slug'] == slug), None)

        if not licenca_info:
            return Response({"error": "Licença não encontrada."}, status=404)

        # Garantir que estamos consultando no mesmo banco da licença selecionada
        banco = get_licenca_db_config(request)
        empresas = Empresas.objects.using(banco).all().order_by('empr_codi')
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

        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        logger.info(f"empresa_id: {empresa_id}")

        try:
            empresa_id_int = int((empresa_id or '').strip())
        except (TypeError, ValueError):
            return Response({'error': 'empresa_id inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        filiais_qs = Filiais.objects.using(banco).filter(empr_empr=empresa_id_int).order_by('empr_codi')
        serializer = FilialSerializer(filiais_qs, many=True)
        return Response(serializer.data)

class UploadCertificadoA1View(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug=None):
        banco = get_licenca_db_config(request)
        empresa_id = request.data.get('empresa_id')
        filial_id = request.data.get('filial_id')
        senha = request.data.get('senha')
        arquivo = request.FILES.get('certificado')
        if not all([empresa_id, filial_id, senha, arquivo]):
            return Response({'error': 'empresa_id, filial_id, senha e certificado são obrigatórios.'}, status=400)
        try:
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
        except Exception:
            return Response({'error': 'IDs inválidos.'}, status=400)
        filial = Filiais.objects.using(banco).filter(empr_empr=empresa_id, empr_codi=filial_id).first()
        logger.info(f"filial: {filial}")
        if not filial:
            return Response({'error': 'Filial não encontrada.'}, status=404)
        nome_arquivo = getattr(arquivo, 'name', 'certificado.p12')
        logger.info(f"nome_arquivo: {nome_arquivo}")
        conteudo = arquivo.read()
        logger.info(f"tamanho do arquivo: {len(conteudo)}")
        try:
            load_key_and_certificates(conteudo, senha.encode('utf-8'))
        except Exception:
            return Response({'error': 'Certificado inválido ou senha incorreta.'}, status=400)
        filial.empr_cert = nome_arquivo
        filial.empr_senh_cert = encrypt_str(senha)
        filial.empr_cert_digi = conteudo    # salva original
        filial.save(using=banco)
        logger.info(f"certificado salvo: {filial.empr_cert}")
        return Response({'message': 'Certificado salvo com sucesso.'})

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
    try:
        from core.licenca_context import get_licencas_map
        return Response(get_licencas_map())
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e), 'trace': traceback.format_exc()}, status=200)


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

class EmpresasViewSet(viewsets.ModelViewSet):
    serializer_class = EmpresaDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return Empresas.objects.using(banco).all()

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        serializer = EmpresaDetailSerializer(data=request.data)
        if serializer.is_valid():
            obj = Empresas.objects.using(banco).create(**serializer.validated_data)
            return Response(EmpresaDetailSerializer(obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        serializer = EmpresaDetailSerializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            for attr, val in serializer.validated_data.items():
                setattr(instance, attr, val)
            instance.save(using=banco)
            return Response(EmpresaDetailSerializer(instance).data)
        return Response(serializer.errors, status=400)

class FiliaisViewSet(viewsets.ModelViewSet):
    serializer_class = FilialDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        qs = Filiais.objects.using(banco).all()
        empresa_id = self.request.query_params.get('empresa_id')
        if empresa_id:
            qs = qs.filter(empr_codi=int(empresa_id))
        return qs

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        serializer = FilialDetailSerializer(data=request.data)
        if serializer.is_valid():
            obj = Filiais.objects.using(banco).create(**serializer.validated_data)
            return Response(FilialDetailSerializer(obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=400)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        data = request.data.copy()
        senha = data.get('empr_senh_cert')
        arquivo = request.FILES.get('certificado')
        serializer = FilialDetailSerializer(instance, data=data, partial=False)
        if serializer.is_valid():
            for attr, val in serializer.validated_data.items():
                setattr(instance, attr, val)
            if senha and senha != '********':
                from Licencas.crypto import encrypt_str
                instance.empr_senh_cert = encrypt_str(senha)
            if arquivo:
                from Licencas.crypto import encrypt_bytes
                from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
                content = arquivo.read()
                load_key_and_certificates(content, (senha or '').encode('utf-8'))
                instance.empr_cert = getattr(arquivo, 'name', 'certificado.p12')
                instance.empr_cert_digi = encrypt_bytes(content)
            instance.save(using=banco)
            return Response(FilialDetailSerializer(instance).data)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['get'])
    def certificado(self, request, pk=None):
        banco = get_licenca_db_config(request)
        filial = self.get_object()

        if not filial.empr_cert_digi:
            return Response({'error': 'Sem certificado'}, status=404)

        from django.http import HttpResponse
        data = bytes(filial.empr_cert_digi)

        resp = HttpResponse(data, content_type='application/x-pkcs12')
        resp['Content-Disposition'] = f'attachment; filename="{filial.empr_cert or "certificado.p12"}"'
        return resp
