from django.core.management.base import BaseCommand
import csv
import os
from django.db import connections
from core.licencas_loader import carregar_licencas_dict
from Produtos.models import Produtos, UnidadeMedida, Marca

def montar_db_config(lic):
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": lic["db_host"],
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 60,
    }
    return config

def drop_field_from_model(model, field_name):
    """Remove campo do model dinamicamente para evitar erros se não existir no banco"""
    try:
        field = model._meta.get_field(field_name)
    except:
        return # Campo não existe no model
    
    # Remove da lista de campos locais
    model._meta.local_fields = [f for f in model._meta.local_fields if f.name != field_name]
    
    # Limpa caches para forçar recálculo
    model._meta._expire_cache()
    
    # Se o campo estiver em fields_map (Django < 3 ou interno), tenta remover
    if hasattr(model._meta, 'fields_map') and field_name in model._meta.fields_map:
        del model._meta.fields_map[field_name]

class Command(BaseCommand):
    help = 'Importa produtos de um arquivo CSV para o tenant demonstracao'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Caminho para o arquivo CSV')

    def handle(self, *args, **options):
        # Desabilitar signals de auditoria para evitar erros com colunas inexistentes e melhorar performance
        os.environ['DISABLE_AUDIT_SIGNALS'] = '1'
        
        csv_file_path = options['csv_file']
        target_slug = 'demonstracao'
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_file_path}'))
            return

        # Carregar licenças e encontrar o tenant alvo
        self.stdout.write(f"Buscando licença '{target_slug}'...")
        licencas = carregar_licencas_dict()
        licenca_alvo = next((l for l in licencas if l['slug'] == target_slug), None)
        
        if not licenca_alvo:
             self.stdout.write(self.style.ERROR(f'Licença "{target_slug}" não encontrada. Licenças disponíveis: {[l["slug"] for l in licencas]}'))
             return

        alias = f"tenant_{target_slug}"
        self.stdout.write(f"Configurando conexão para {alias}...")
        connections.databases[alias] = montar_db_config(licenca_alvo)

        # Testar conexão
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro de conexão com {alias}: {e}"))
            return

        # Verificar se coluna prod_gtin existe
        has_gtin = False
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("""
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'produtos' 
                    AND column_name = 'prod_gtin'
                """)
                has_gtin = cursor.fetchone() is not None
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Erro ao verificar coluna prod_gtin: {e}"))

        if not has_gtin:
            self.stdout.write(self.style.WARNING("Coluna 'prod_gtin' não encontrada no banco. Removendo do model dinamicamente."))
            drop_field_from_model(Produtos, 'prod_gtin')

        # Tentar obter uma unidade de medida padrão no banco do tenant
        try:
            unidade = UnidadeMedida.objects.using(alias).filter(unid_codi__in=['UN', 'UNID', 'PC', 'PÇ']).first()
            if not unidade:
                unidade = UnidadeMedida.objects.using(alias).first()
                if not unidade:
                     self.stdout.write(self.style.ERROR('Nenhuma Unidade de Medida encontrada no banco de dados. Cadastre pelo menos uma.'))
                     return
        except Exception as e:
             self.stdout.write(self.style.ERROR(f'Erro ao buscar Unidade de Medida: {e}'))
             return
        try:
            marca = Marca.objects.using(alias).filter(codigo__in=['10']).first()
            if not marca:
                marca = Marca.objects.using(alias).first()
                if not marca:
                     self.stdout.write(self.style.ERROR('Nenhuma Marca encontrada no banco de dados. Cadastre pelo menos uma.'))
                     return
        except Exception as e:
             self.stdout.write(self.style.ERROR(f'Erro ao buscar Marca: {e}'))
             return

        self.stdout.write(f'Usando Unidade de Medida padrão: {unidade.unid_codi}')
        self.stdout.write(f'Usando Marca padrão: {marca.codigo}')

        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            created_count = 0
            updated_count = 0
            
            for row in reader:
                prod_codi = row.get('prod_codi')
                prod_nome = row.get('prod_nome')
                prod_url = row.get('prod_url')
                
                if not prod_codi:
                    continue
                
                defaults = {
                    'prod_nome': prod_nome,
                    'prod_url': prod_url,
                    'prod_empr': '5',
                    'prod_unme': unidade,
                    'prod_coba': prod_codi,
                    'prod_marc': marca,
                }
                
                if has_gtin:
                    defaults['prod_gtin'] = 'SEM GTIN'
                
                obj, created = Produtos.objects.using(alias).update_or_create(
                    prod_codi=prod_codi,
                    defaults=defaults
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Produto criado: {prod_codi} - {prod_nome}'))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Produto atualizado: {prod_codi} - {prod_nome}'))
                
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Importação concluída para {alias}! Total: {count}. Criados: {created_count}. Atualizados: {updated_count}.'))
