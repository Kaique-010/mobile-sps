from Licencas.utils import atualizar_senha
from pprint import pprint
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login as django_login
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
from core.middleware import set_licenca_slug
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
from django.core.cache import cache

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

        username_norm = (username or "").strip().lower()
        login_lock_key = build_cache_key("licencas_login", "lock", docu_digits, username_norm or "anon")
        lock_acquired = cache.add(login_lock_key, request_id, timeout=8)
        if not lock_acquired:
            logger.warning(
                "[LOGIN][%s] bloqueado por corrida: login já em processamento key=%s",
                request_id,
                login_lock_key,
            )
            return Response(
                {'error': 'Login já está em processamento. Aguarde 2 segundos e tente novamente.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        db_start = time.time()
        try:
            banco = get_licenca_db_config(slug_from_docu)
        except Exception as e:
            logger.error("[LOGIN][%s] Erro ao obter config do banco: %s", request_id, e)
            return Response({'error': f'Erro na configuração da licença: {str(e)}'}, status=500)

        db_time = (time.time() - db_start) * 1000
        logger.debug("[LOGIN][%s] get_licenca_db_config: %.2fms", request_id, db_time)

        if not banco:
            return Response({'error': 'CPF/CNPJ inválido ou licença não encontrada.'}, status=404)

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

        licenca_web = LicencaWeb.objects.using('default').select_related('plano').filter(
            Q(cnpj=docu_digits) | Q(cnpj=str(docu))
        ).first()

        if licenca_web:
            try:
                plano = licenca_web.plano
            except Exception:
                plano = None
                logger.warning("[LOGIN] plano órfão ou deletado para licença %s", licenca_web.slug)

            if plano and plano.plan_trial:
                if plano.plan_ativ and plano.plan_data_expi:
                    if timezone.now() > plano.plan_data_expi:
                        plano.plan_ativ = False
                        plano.save(update_fields=['plan_ativ'])
                        logger.warning("[LOGIN] Trial expirado on-the-fly — licença %s", licenca_web.slug)

                if not plano.plan_ativ:
                    return Response(
                        {
                            'error': 'Seu período de trial expirou. Entre em contato com o suporte.',
                            'plan_data_expi': plano.plan_data_expi,
                            'code': 'trial_expirado',
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        licenca_time = (time.time() - licenca_start) * 1000
        logger.debug("[LOGIN][%s] Buscar licença: %.2fms", request_id, licenca_time)

        # Em ambiente multi-db/multi-slug existem bases onde a tabela "licencas"
        # local pode não refletir o cadastro central imediatamente.
        # Não bloqueamos o login aqui para evitar falso-negativo intermitente:
        # a validação real continua sendo docu->slug válido + usuário/senha no banco alvo.
        if not licenca and not licenca_web:
            logger.warning(
                "[LOGIN][%s] licença não encontrada nas tabelas locais/central para docu=%s slug=%s; "
                "prosseguindo com autenticação pelo banco resolvido",
                request_id,
                docu_digits,
                slug_from_docu,
            )

        user_start = time.time()
        try:
            usuario = Usuarios.objects.using(banco).get(usua_nome__iexact=username)
        except Usuarios.DoesNotExist:
            return Response({'error': 'Usuário não encontrado.'}, status=404)
        except Exception as e:
            logger.error("[LOGIN][%s] Erro ao buscar usuário no banco %s: %s", request_id, banco, e)
            return Response({'error': f'Erro ao conectar no banco da empresa: {str(e)}'}, status=500)

        user_time = (time.time() - user_start) * 1000
        logger.debug("[LOGIN][%s] Buscar usuário: %.2fms", request_id, user_time)

        password_start = time.time()
        if not usuario.check_password(password):
            logger.warning(
                "[LOGIN][%s] senha inválida para usuário=%s slug=%s",
                request_id,
                username,
                slug_from_docu,
            )
            return Response({'error': 'Senha incorreta.'}, status=401)
        password_time = (time.time() - password_start) * 1000
        logger.debug("[LOGIN][%s] Validar senha: %.2fms", request_id, password_time)

        modulos_login = []

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

        # ----------------------------------------------------------------
        # SESSÃO (anti-race): usa login() nativo do Django para gravar
        # SESSION_KEY/BACKEND/HASH de forma consistente e com rotação segura.
        # Depois grava os metadados adicionais usados pelo projeto.
        # ----------------------------------------------------------------
        try:
            django_login(request, usuario, backend='Licencas.backends.UserBackend')
        except Exception as e:
            logger.exception("[LOGIN][%s] falha no django_login: %s", request_id, e)
            return Response(
                {
                    'error': 'Falha ao iniciar sessão. Tente novamente.',
                    'request_id': request_id,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        request.session["usua_codi"] = usuario.usua_codi
        request.session["docu"] = docu_digits
        request.session["slug"] = slug_from_docu
        request.session["empresa_id"] = empresa_id_int
        request.session["filial_id"] = filial_id_int
        request.session.modified = True

        # Garante contexto da licença no thread local durante esta request.
        set_licenca_slug(slug_from_docu)

        logger.info(
            "[LOGIN][%s] sessão preparada snapshot=%s",
            request_id,
            {k: request.session.get(k) for k in ['usua_codi', 'docu', 'slug', 'empresa_id', 'filial_id']},
        )

        # ----------------------------------------------------------------
        # JWT
        # ----------------------------------------------------------------
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

        jwt_time = (time.time() - jwt_start) * 1000
        logger.debug("[LOGIN][%s] Gerar JWT: %.2fms", request_id, jwt_time)

        total_time = (time.time() - start_time) * 1000
        logger.info("[LOGIN][%s] TOTAL: %.2fms para usuário %s", request_id, total_time, username)
        logger.debug(
            "[TRACE][LOGIN][%s] slug=%s banco=%s empresa=%s filial=%s user_id=%s",
            request_id, slug_from_docu, banco, empresa_id, filial_id, usuario.usua_codi
        )

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

        try:
            banco = get_licenca_db_config(request)
        except Exception:
            return Response(
                {
                    "error": "Sessão inválida ou licença indisponível.",
                    "code": "SESSION_INVALID",
                    "next": "/web/selecionar-empresa/",
                },
                status=401,
            )
        try:
            empresas = Empresas.objects.using(banco).all().order_by('empr_codi')
            if empresas.exists():
                serializer = EmpresaSerializer(empresas, many=True)
                return Response(serializer.data)
            else:
                return Response({"error": "Nenhuma empresa encontrada."}, status=404)
        except Exception:
            return Response(
                {
                    "error": "Falha ao consultar empresas.",
                    "code": "DB_ERROR",
                },
                status=500,
            )




class FiliaisPorEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            banco = get_licenca_db_config(request)
        except Exception:
            return Response(
                {
                    "error": "Sessão inválida ou licença indisponível.",
                    "code": "SESSION_INVALID",
                    "next": "/web/selecionar-empresa/",
                },
                status=401,
            )

        empresa_id = request.query_params.get('empresa_id')
        if not empresa_id:
            empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        logger.info(f"empresa_id: {empresa_id}")

        try:
            empresa_id_int = int((empresa_id or '').strip())
        except (TypeError, ValueError):
            return Response({'error': 'empresa_id inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            filiais_qs = Filiais.objects.using(banco).filter(empr_empr=empresa_id_int).order_by('empr_codi')
            serializer = FilialSerializer(filiais_qs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response(
                {
                    "error": "Falha ao consultar filiais.",
                    "code": "DB_ERROR",
                },
                status=500,
            )

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
        try:
            banco = get_licenca_db_config(request)
        except Exception:
            return Response(
                {
                    'error': 'Sessão inválida ou licença indisponível.',
                    'code': 'SESSION_INVALID',
                    'next': '/web/selecionar-empresa/',
                },
                status=401,
            )
        empresa_id = request.query_params.get('empresa_id')
        filial_id = request.query_params.get('filial_id')

        if not empresa_id or not filial_id:
            return Response({'error': 'Empresa e filial obrigatórias'}, status=400)

        try:
            modulos_ids = get_codigos_modulos_liberados(banco, empresa_id, filial_id)
        except Exception:
            return Response(
                {'error': 'Falha ao consultar módulos.'},
                status=500,
            )

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
