# agricola/management/commands/sync_parametros_agricola.py

from django.core.management.base import BaseCommand
from django.conf import settings
from ...models import ParametroAgricola
from ...registry import ParametrosAgricolasRegistry
from Licencas.models import Empresas, Filiais
from core.licencas_loader import carregar_licencas_dict
from core.connection_preloader import preload_database_connections
import json

class Command(BaseCommand):
    help = "Sincroniza parâmetros agrícolas com o registry para todas as empresas em todos os bancos"

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização de parâmetros agrícolas...")
        
        # Garante que as conexões estão carregadas
        preload_database_connections()
        
        licencas = carregar_licencas_dict()
        
        for licenca in licencas:
            slug = licenca.get('slug')
            db_name = licenca.get('db_name')
            
            if not slug or slug not in settings.DATABASES:
                # Tenta usar o default se for o caso, mas geralmente ignoramos se não estiver configurado
                if slug != 'default':
                    self.stdout.write(self.style.WARNING(f"Skipping {slug}: DB not configured in settings"))
                    continue
            
            self.stdout.write(f"Processando licença: {slug} ({db_name})")
            
            try:
                # Busca empresas no banco específico
                empresas_qs = Empresas.objects.using(slug).all()
                
                for empresa in empresas_qs:
                    empresa_id = empresa.empr_codi
                    
                    # Busca filiais desta empresa
                    # Nota: Filiais.empr_empr parece ser a FK para Empresa, apesar de estar como PK no model legacy
                    try:
                        filiais_qs = Filiais.objects.using(slug).filter(empr_empr=empresa_id)
                        
                        count_filiais = 0
                        for filial in filiais_qs:
                            filial_id = filial.empr_codi # Assumindo empr_codi como ID da filial
                            self.sync_params(slug, empresa_id, filial_id)
                            count_filiais += 1
                        
                        if count_filiais == 0:
                            self.stdout.write(f"  > Empresa {empresa_id} sem filiais encontradas.")
                            
                    except Exception as e:
                         self.stdout.write(self.style.ERROR(f"  > Erro ao buscar filiais para empresa {empresa_id}: {e}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar licença {slug}: {e}"))
                
        self.stdout.write(self.style.SUCCESS("Sync global concluído."))

    def sync_params(self, db_alias, empresa_id, filial_id):
        created_count = 0
        for chave, config in ParametrosAgricolasRegistry.PARAMS.items():
            obj, created = ParametroAgricola.objects.using(db_alias).get_or_create(
                para_empr=empresa_id,
                para_fili=filial_id,
                para_chav=chave,
                defaults={"para_valo": json.dumps(config["default"])},
            )
            if created:
                created_count += 1
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  > Emp {empresa_id}/Fil {filial_id}: {created_count} parâmetros criados."))
