import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Entidades
from django.db import connections
from core.registry import LICENCAS_MAP
from decouple import config
import logging

logger = logging.getLogger(__name__)

class EntidadeJWTAuthentication(BaseAuthentication):
    """
    Autenticação JWT customizada para entidades (clientes)
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        # Log para debug
        logger.info(f"[AUTH DEBUG] Header: {auth_header}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.info(f"[AUTH DEBUG] Header inválido ou ausente")
            return None
            
        token = auth_header.split(' ')[1]
        
        # Log do token
        logger.info(f"[AUTH DEBUG] Token extraído: {token[:20]}...")
        
        if token == 'undefined':
            logger.error(f"[AUTH DEBUG] Token é 'undefined' - problema no frontend")
            return None
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Verificar se é token de entidade
            if payload.get('tipo') != 'cliente':
                logger.info(f"[AUTH DEBUG] Não é token de cliente: {payload.get('tipo')}")
                return None
                
            cliente_id = payload.get('cliente_id')
            banco = payload.get('banco')
            
            if not cliente_id or not banco:
                raise AuthenticationFailed('Token inválido')
            
            # Configurar banco se necessário
            self._configurar_banco_se_necessario(banco)
            
            # Buscar entidade
            try:
                entidade = Entidades.objects.using(banco).get(enti_clie=cliente_id)
                
                # Criar objeto user-like para compatibilidade com DRF
                entidade.is_authenticated = True
                entidade.is_active = True
                entidade.pk = cliente_id
                entidade.banco_atual = banco
                
                return (entidade, token)
                
            except Entidades.DoesNotExist:
                raise AuthenticationFailed('Cliente não encontrado')
                
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Token inválido')
        except Exception as e:
            logger.error(f"[ERRO AUTENTICAÇÃO] {str(e)}")
            raise AuthenticationFailed('Erro na autenticação')
    
    def _configurar_banco_se_necessario(self, banco_slug):
        """Configura banco dinamicamente se não existir"""
        if banco_slug in settings.DATABASES:
            return
            
        licenca = next((lic for lic in LICENCAS_MAP if lic["slug"] == banco_slug), None)
        if not licenca:
            raise AuthenticationFailed(f"Licença {banco_slug} não encontrada")
        
        prefixo = banco_slug.upper()
        try:
            db_user = config(f"{prefixo}_DB_USER")
            db_password = config(f"{prefixo}_DB_PASSWORD")
            
            settings.DATABASES[banco_slug] = {
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
            
            connections.ensure_defaults(banco_slug)
            
        except Exception as e:
            logger.error(f"[ERRO CONFIGURAÇÃO BANCO] {banco_slug}: {str(e)}")
            raise AuthenticationFailed("Erro na configuração do banco")