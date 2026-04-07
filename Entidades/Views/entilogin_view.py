
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from Entidades.models import Entidades 
from django.db.models import Q
from core.registry import get_licenca_db_config
from core.licenca_context import get_licencas_login_clientes
from django.conf import settings
from django.db import connections
from decouple import config
import logging
from rest_framework.decorators import action
import jwt
from datetime import datetime, timedelta
from django.core.cache import cache


logger = logging.getLogger(__name__)

class EntidadesLoginViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, slug=None):
        data = request.data
        documento = data.get('documento')  
        usuario1 = data.get('usuario')     
        senha1 = data.get('senha')    
        usuario2 = data.get('usuario2')    
        senha2 = data.get('senha2')    

        if not documento:
            return Response({
                "erro": "Documento é obrigatório"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not (usuario1 and senha1) and not (usuario2 and senha2):
            return Response({
                "erro": "Informe usuário e senha"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar apenas nas licenças permitidas para login de clientes
        licencas = get_licencas_login_clientes()
        logger.warning(f"[LOGIN ENTIDADES] inicio documento={documento} licencas_count={len(licencas)} licencas={licencas}")
        
        documento_encontrado = False
        
        for licenca in licencas:
            try:
                banco_slug = licenca['slug']
                
                # Ignorar bancos locais em produção
                if not settings.DEBUG and licenca.get('db_host') in ['localhost', '127.0.0.1']:
                    continue

                # Configurar banco se necessário
                if banco_slug not in settings.DATABASES:
                    self._configurar_banco(licenca)
                
                # Buscar entidade
                entidade = Entidades.objects.using(banco_slug).filter(
                    Q(enti_cpf=documento) | Q(enti_cnpj=documento),
                    enti_empr=1
                ).first()

                if not entidade:
                    continue
                
                documento_encontrado = True
                
                # Verificar credenciais
                login1_ok = False
                login2_ok = False
                
                # Verifica nos campos principais (usuario/senha)
                if usuario1 and senha1:
                    # Tenta validar como usuario 1
                    if entidade.enti_mobi_usua == usuario1 and entidade.enti_mobi_senh == senha1:
                        login1_ok = True
                    # Tenta validar como usuario 2 (caso tenha passado no campo principal)
                    elif entidade.enti_usua_mobi == usuario1 and entidade.enti_senh_mobi == senha1:
                        login2_ok = True
                
                # Verifica nos campos secundários (usuario2/senha2) - caso sejam enviados explicitamente
                if not (login1_ok or login2_ok) and usuario2 and senha2:
                    if entidade.enti_usua_mobi == usuario2 and entidade.enti_senh_mobi == senha2:
                        login2_ok = True
                
                if login1_ok or login2_ok:
                    
                    logger.info(f"[LOGIN SUCCESS] Cliente {entidade.enti_nome} - Banco: {banco_slug}")
                    
                    # Determinar permissões baseadas no login efetuado
                    ver_preco = False
                    ver_foto = False
                    
                    if login1_ok:
                        ver_preco = entidade.enti_mobi_prec
                        ver_foto = entidade.enti_mobi_foto
                    elif login2_ok:
                        ver_preco = entidade.enti_usua_prec
                        ver_foto = entidade.enti_usua_foto
                    
                    # Retorno simplificado - sem tokens
                    usuario_tipo_logado = 'usuario1' if login1_ok else 'usuario2'
                    
                    print(f"[LOGIN DEBUG] cliente={entidade.enti_clie} usuario={usuario_tipo_logado} ver_preco={ver_preco} ver_foto={ver_foto}")
                    
                    resp = {
                        'success': True,
                        'cliente_id': entidade.enti_clie,
                        'cliente_nome': entidade.enti_nome,
                        'documento': entidade.enti_cpf or entidade.enti_cnpj,
                        'banco': banco_slug,
                        'session_id': f"{entidade.enti_clie}_{banco_slug}_{usuario_tipo_logado}",  # ID com usuário para sessão
                        'usuario_logado': usuario_tipo_logado,
                        'permissoes': {
                            'ver_preco': ver_preco, 
                            'ver_foto': ver_foto,
                        },
                        'permissoes_por_usuario': {
                            'usuario1': {
                                'ver_preco': entidade.enti_mobi_prec,
                                'ver_foto': entidade.enti_mobi_foto
                            },
                            'usuario2': {
                                'ver_preco': entidade.enti_usua_prec,
                                'ver_foto': entidade.enti_usua_foto
                            }
                        },
                    }
                    session_key = f"session:{resp['session_id']}:permissoes"
                    cache.set(session_key, {'ver_preco': ver_preco, 'ver_foto': ver_foto})
                    try:
                        logger.info(f"[CACHE SET][SESSION] key={session_key}")
                    except Exception:
                        pass
                    return Response(resp)
                else:
                    logger.warning(f"[LOGIN FAIL] Credenciais inválidas para {documento} no banco {banco_slug}")

            except Exception as e:
                logger.error(f"[ERRO BANCO {banco_slug}] {str(e)}")
                continue
        
        if documento_encontrado:
             logger.error(f"[LOGIN FAILED] Documento {documento} encontrado, mas credenciais inválidas")
        else:
             logger.error(f"[LOGIN FAILED] Documento {documento} não encontrado em nenhuma base")
             
        return Response({
            "erro": "Credenciais inválidas"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    def _configurar_banco(self, licenca):
        """Configura banco dinamicamente"""
        prefixo = licenca["slug"].upper()
        try:
            db_user = licenca.get("db_user") or config(f"{prefixo}_DB_USER", default=None)
            db_password = licenca.get("db_password") or config(f"{prefixo}_DB_PASSWORD", default=None)
            if not db_user or not db_password:
                raise Exception("Credenciais ausentes para a licença")
            
            settings.DATABASES[licenca["slug"]] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': licenca["db_name"],
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': licenca["db_host"],
                'PORT': licenca["db_port"],
                'OPTIONS': {
                    'options': '-c timezone=America/Araguaina'
                },
            }
            
            connections.ensure_defaults(licenca["slug"])
            
        except Exception as e:
            logger.error(f"[ERRO CONFIG BANCO] {licenca['slug']}: {str(e)}")
            raise





