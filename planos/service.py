from .models import Plano
from licencas_web.models import LicencaWeb
from Licencas.models import Empresas, Filiais, Usuarios
from django.db import transaction, connections
from datetime import datetime, timedelta
from django.utils.text import slugify
from core.utils import get_db_from_slug
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

class PlanoService:
    @staticmethod
    @transaction.atomic
    def criar_plano(plan_nome, plan_prec, plan_desc, plan_trial, plan_trial_dias, db_alias='default'):
        plano = Plano.objects.using(db_alias).create(
            plan_nome=plan_nome,
            plan_prec=plan_prec,
            plan_desc=plan_desc,
            plan_trial=plan_trial,
            plan_trial_dias=plan_trial_dias,
            plan_data_ativ=datetime.now(),
            plan_data_expi=datetime.now() + timedelta(days=plan_trial_dias),
            plan_ativ=True
        )
        return plano
    
    @staticmethod
    @transaction.atomic
    def ativar_plano(plano_id, db_alias='default'):
        plano = Plano.objects.using(db_alias).get(id=plano_id)
        plano.plan_ativ = True
        plano.plan_data_ativ = datetime.now()
        plano.plan_data_expi = datetime.now() + timedelta(days=plano.plan_trial_dias)
        plano.save(using=db_alias)
        return plano
    
    @staticmethod
    @transaction.atomic
    def desativar_plano(plano_id, db_alias='default'):
        plano = Plano.objects.using(db_alias).get(id=plano_id)
        plano.plan_ativ = False
        plano.plan_data_ativ = None
        plano.plan_data_expi = None
        plano.save(using=db_alias)
        return plano
    
    @staticmethod
    @transaction.atomic
    def verificar_plano(plano_id, db_alias='default'):
        plano = Plano.objects.using(db_alias).get(id=plano_id)
        if plano.plan_ativ:
            if datetime.now() > plano.plan_data_expi:
                plano.plan_ativ = False
                plano.plan_data_ativ = None
                plano.plan_data_expi = None
                plano.save(using=db_alias)
        return plano
    
    @staticmethod
    @transaction.atomic
    def ativar_e_criar_licenca(plano_id, licenca_id, empresa_id, filial_id):
        # Este metodo parece obsoleto ou para uso interno específico, mantendo compatibilidade mas ajustando
        plano = Plano.objects.using('default').get(id=plano_id, plan_ativ=True)
        licenca = LicencaWeb.objects.using('default').get(id=licenca_id)
        
        # Conecta no banco da licença para buscar empresa/filial
        db_alias = get_db_from_slug(licenca.slug)
        
        empresa = Empresas.objects.using(db_alias).get(empr_codi=empresa_id) 
        filial = Filiais.objects.using(db_alias).get(empr_codi=filial_id) 
        
        usuario = Usuarios.objects.using(db_alias).create(
            usua_nome='web',
            usua_seto=1
        )
        usuario.set_password('123mudar')
        usuario.save(using=db_alias)
        
        # Vincula plano à licença
        licenca.plano = plano
        licenca.save(using='default')
        return licenca

    @staticmethod
    def criar_ambiente_trial(dados_cliente, modulos_liberados=None):
        """
        Cria todo o ambiente para um novo cliente trial:
        1. Cria LicencaWeb e Plano no default (save1)
        2. Cria banco de dados (usando template se disponivel)
        3. Popula dados iniciais (Empresa, Filial, Usuario)
        """
        nome_empresa = dados_cliente.get('nome_empresa')
        cnpj = dados_cliente.get('cnpj')
        
        if not nome_empresa or not cnpj:
            raise ValueError("Nome da empresa e CNPJ são obrigatórios")

        # 1. Preparar Slug e Nome do Banco
        # Padrão: saveweb001, saveweb002, ...
        
        # Busca todas as licenças que começam com 'saveweb'
        licencas = list(LicencaWeb.objects.filter(slug__startswith='saveweb').values_list('slug', flat=True))
        
        max_num = 0
        for s in licencas:
            # Tenta extrair o número do final (savewebXXX)
            if s.startswith('saveweb'):
                try:
                    num_part = s[7:] # Pega depois de 'saveweb'
                    if num_part.isdigit():
                        num = int(num_part)
                        if num > max_num:
                            max_num = num
                except:
                    pass
        
        next_num = max_num + 1
        base_slug = f"saveweb{next_num:03d}"
        
        # 2. Criar Plano e LicencaWeb
        # Nota: Não usamos transaction.atomic aqui para todo o método porque CREATE DATABASE não roda em transação
        
        plano = PlanoService.criar_plano(
            plan_nome=f"Trial 15 Dias - {nome_empresa}",
            plan_prec=0.0,
            plan_desc="Plano Trial de 15 dias",
            plan_trial=True,
            plan_trial_dias=15,
            db_alias='default'
        )

        licenca = LicencaWeb.objects.using('default').create(
            slug=base_slug,
            cnpj=cnpj,
            db_name=base_slug,
            db_host='64.181.163.190',
            db_port='5432',
            db_user='postgres', 
            db_password='@spartacus201@',
            plano=plano
        )
        
        # 3. Criar Banco de Dados Remoto
        try:
            conn = psycopg2.connect(
                dbname='postgres',
                user='postgres',
                password='@spartacus201@',
                host='64.181.163.190',
                port='5432'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Verifica se já existe
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (base_slug,))
            if not cur.fetchone():
                logger.info(f"Criando banco de dados {base_slug} a partir de base_modelo...")
                cur.execute(f'CREATE DATABASE "{base_slug}" TEMPLATE "base_modelo"')
            else:
                logger.warning(f"Banco de dados {base_slug} já existe. Ignorando criação.")
                
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro ao criar banco de dados: {e}")
            # Rollback manual das meta-informações
            licenca.delete()
            plano.delete()
            raise Exception(f"Falha na criação do banco de dados: {str(e)}")

        # 4. Popular Dados Iniciais
        try:
            # Registra a conexão no settings manualmente para garantir
            from django.conf import settings
            
            settings.DATABASES[base_slug] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': base_slug,
                'USER': 'postgres',
                'PASSWORD': '@spartacus201@',
                'HOST': '64.181.163.190',
                'PORT': '5432',
                'OPTIONS': {
                    'options': '-c timezone=America/Araguaina',
                    'connect_timeout': 30,
                    'application_name': 'mobile_sps_trial_creation',
                },
                'CONN_MAX_AGE': 0,
            }
            connections.ensure_defaults(base_slug)
            
            db_alias = base_slug
            
            # Cria Empresa
            empresa = Empresas.objects.using(db_alias).create(
                empr_codi=1,
                empr_nome=nome_empresa,
                empr_fant=dados_cliente.get('nome_fantasia') or nome_empresa,
                empr_docu=cnpj,
                empr_emai=dados_cliente.get('email'),
                empr_fone=dados_cliente.get('telefone'),
                empr_ende=dados_cliente.get('endereco'),
                empr_cida=dados_cliente.get('cidade'),
                empr_esta=dados_cliente.get('uf')
            )
            
            # Cria Filial
            nome_filial = dados_cliente.get('nome_filial') or f"FILIAL 01 - {nome_empresa}"
            filial = Filiais.objects.using(db_alias).create(
                empr_empr=empresa.empr_codi,
                empr_codi=1,
                empr_nome=nome_filial,
                empr_docu=cnpj,
                empr_emai=dados_cliente.get('email'),
                empr_fone=dados_cliente.get('telefone'),
                empr_ende=dados_cliente.get('endereco'),
                empr_cida=dados_cliente.get('cidade'),
                empr_esta=dados_cliente.get('uf')
            )
            
            # Cria Usuário
            # Usamos usua_codi=1 pois o campo não é auto-incremento no banco legado
            usuario = Usuarios.objects.using(db_alias).create(
                usua_codi=1,
                usua_nome='web',
                password='123mudar', # Mapeado para usua_senh_mobi no model
                usua_seto=1
            )
            
            usuario_admin = Usuarios.objects.using(db_alias).create(
                usua_codi=2,
                usua_nome='admin',
                password='roma3030@',
                usua_seto=1
            )
            
            # 5. Liberar Módulos
            try:
                from parametros_admin.models import Modulo, PermissaoModulo
                
                # Sincroniza tabela de módulos com os apps instalados
                # Importante: force=True para garantir que novos apps sejam registrados
                Modulo.sync_installed_apps(alias=db_alias, force=True)
                
                # Definição dos módulos a serem liberados
                if modulos_liberados:
                    # Se uma lista específica foi passada, usa apenas ela
                    modulos_qs = Modulo.objects.using(db_alias).filter(modu_nome__in=modulos_liberados)
                else:
                    # Se não, exclui módulos de sistema para criar licencça padrão
                    EXCLUDED_APPS = [
                        'admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles', 
                        'core', 'planos', 'licencas_web', 'auditoria', 'Agricola','OrdemdeServico',
                        'controledevisitas','contratos','controledePonto','Pisos','osexterna',
                        'drf_spectacular', 'rest_framework_simplejwt', 'mcp_agent_db', 'listacasamento',
                        'corsheaders', 'debug_toolbar', 'channels'
                    ]
                    modulos_qs = Modulo.objects.using(db_alias).exclude(modu_nome__in=EXCLUDED_APPS)
                
                # Itera sobre os módulos para garantir permissão (create or update)
                count_created = 0
                count_updated = 0
                
                for mod in modulos_qs:
                    # Garante que o módulo está ativo globalmente
                    if not mod.modu_ativ:
                        mod.modu_ativ = True
                        mod.save(using=db_alias)

                    perm, created = PermissaoModulo.objects.using(db_alias).get_or_create(
                        perm_empr=1,
                        perm_fili=1,
                        perm_modu=mod,
                        defaults={
                            'perm_ativ': True, 
                            'perm_usua_libe': 1 # Usuário web criado acima
                        }
                    )
                    
                    if created:
                        count_created += 1
                    else:
                        # Se já existe, garante que está ativo
                        if not perm.perm_ativ:
                            perm.perm_ativ = True
                            perm.perm_usua_libe = 1
                            perm.save(using=db_alias)
                            count_updated += 1
                
                # Atualiza a lista de módulos na LicencaWeb (apenas os nomes dos módulos ativos)
                modulos_ativos_nomes = list(PermissaoModulo.objects.using(db_alias).filter(
                    perm_empr=1, 
                    perm_fili=1, 
                    perm_ativ=True
                ).values_list('perm_modu__modu_nome', flat=True))
                
                licenca.modulos = json.dumps(modulos_ativos_nomes)
                licenca.save(using='default')
                
                logger.info(f"Liberados {len(modulos_ativos_nomes)} módulos para o trial {base_slug} (Criados: {count_created}, Atualizados: {count_updated})")
                
            except Exception as e:
                logger.error(f"Erro ao liberar módulos: {e}")
                # Não falha o processo todo por isso, mas loga
                import traceback
                logger.error(traceback.format_exc())

            return {
                'plano': plano,
                'licenca': licenca,
                'usuario': usuario,
                'usuario_admin': usuario_admin,
                'empresa': empresa,
                'filial': filial
            }
            
        except Exception as e:
            logger.error(f"Erro ao popular dados iniciais: {e}")
            # Em caso de erro aqui, o banco foi criado mas está vazio/incompleto.
            # Idealmente deveríamos dropar o banco ou marcar para revisão.
            raise Exception(f"Ambiente criado, mas falha ao popular dados: {str(e)}")



