from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError
from core.licencas_loader import carregar_licencas_dict
from transportes.models import RegraICMS

def update_cte_fields(alias: str):
    regra_table = RegraICMS._meta.db_table
    
    with connections[alias].cursor() as cursor:
        # Campos para a tabela Cte (legacy 'cte')
        sqls_cte = [
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_base_st numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_aliq_st numeric(5,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_valo_st numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_mva_st numeric(5,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_redu_st numeric(5,2);",
            
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_vbc_uf_dest numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_vicms_uf_dest numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_aliq_inte_dest numeric(5,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_aliq_inter numeric(5,2);",
            
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_cst_pis varchar(2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_aliq_pis numeric(5,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_base_pis numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_valo_pis numeric(15,2);",
            
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_cst_cofi varchar(2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_aliq_cofi numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_base_cofi numeric(15,2);",
            "ALTER TABLE cte ADD COLUMN IF NOT EXISTS cte_valo_cofi numeric(15,2);",
        ]
        
        # Campos para a tabela RegraICMS
        sqls_regra = [
            f"ALTER TABLE {regra_table} ADD COLUMN IF NOT EXISTS cfop varchar(4);",
            f"ALTER TABLE {regra_table} ADD COLUMN IF NOT EXISTS aliquota_destino numeric(5,2);",
            f"ALTER TABLE {regra_table} ADD COLUMN IF NOT EXISTS mva_st numeric(5,2) DEFAULT 0;",
            f"ALTER TABLE {regra_table} ADD COLUMN IF NOT EXISTS aliquota_st numeric(5,2) DEFAULT 0;",
            f"ALTER TABLE {regra_table} ADD COLUMN IF NOT EXISTS reducao_base_st numeric(5,2) DEFAULT 0;",
        ]

        for sql in sqls_cte:
            try:
                cursor.execute(sql)
            except Exception as e:
                print(f"Erro ao executar SQL no CTE ({alias}): {sql} - Erro: {e}")

        for sql in sqls_regra:
            try:
                cursor.execute(sql)
            except Exception as e:
                # Se a tabela não existir, pode dar erro, mas RegraICMS é managed=True, então deve existir se as migrações rodaram.
                # Se for banco legado sem tabela nova, ignoramos ou logamos.
                print(f"Erro ao executar SQL na RegraICMS ({alias}): {sql} - Erro: {e}")


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

class Command(BaseCommand):
    help = "Atualiza campos de tributação nas tabelas Cte e RegraICMS em todos os bancos de licenças"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)

            # Testar conexão antes de prosseguir
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco de dados não encontrado ou inacessível. Pulando..."))
                continue

            self.stdout.write(self.style.WARNING(f"[{alias}] Atualizando campos de tributação..."))

            try:
                update_cte_fields(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Campos atualizados com sucesso!"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao atualizar campos: {e}"))
