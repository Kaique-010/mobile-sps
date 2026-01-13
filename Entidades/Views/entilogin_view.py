
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


logger = logging.getLogger(__name__)

class EntidadesLoginViewSet(viewsets.ViewSet):
    def create(self, request, slug=None):
        data = request.data
        documento = data.get('documento')  
        usuario = data.get('usuario')     
        senha = data.get('senha')        

        if not documento or not usuario or not senha:
            return Response({
                "erro": "Documento, usuário e senha são obrigatórios"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar apenas nas licenças permitidas para login de clientes
        licencas = get_licencas_login_clientes()
        logger.warning(f"[LOGIN ENTIDADES] inicio documento={documento} licencas_count={len(licencas)} licencas={licencas}")
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
                    Q(enti_cpf=documento) | Q(enti_cnpj=documento)
                ).first()

                if not entidade:
                    continue
                
                # Verificar credenciais
                if entidade.enti_mobi_usua == usuario and entidade.enti_mobi_senh == senha:
                    logger.info(f"[LOGIN SUCCESS] Cliente {entidade.enti_nome} - Banco: {banco_slug}")
                    
                    # Retorno simplificado - sem tokens
                    return Response({
                        'success': True,
                        'cliente_id': entidade.enti_clie,
                        'cliente_nome': entidade.enti_nome,
                        'documento': entidade.enti_cpf or entidade.enti_cnpj,
                        'banco': banco_slug,
                        'session_id': f"{entidade.enti_clie}_{banco_slug}"  # ID simples para sessão
                    })
                    
            except Entidades.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"[ERRO BANCO {banco_slug}] {str(e)}")
                continue
        
        logger.error(f"[LOGIN FAILED] Documento {documento} não encontrado")
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





