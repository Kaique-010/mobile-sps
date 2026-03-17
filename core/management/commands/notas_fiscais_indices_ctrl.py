from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError

from core.licencas_loader import carregar_licencas_dict


def montar_db_config(lic):
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": lic["db_name"],
        "USER": lic["db_user"],
        "PASSWORD": lic["db_password"],
        "HOST": lic["db_host"],
        "PORT": lic["db_port"],
        "CONN_MAX_AGE": 60,
    }


def criar_indices(alias: str):
    stmts = [
        "CREATE INDEX IF NOT EXISTS nf_nota_empresa_filial_idx ON nf_nota (empresa, filial);",
        "CREATE INDEX IF NOT EXISTS nf_nota_status_idx ON nf_nota (empresa, filial, status);",
        "CREATE INDEX IF NOT EXISTS nf_nota_tipo_finalidade_idx ON nf_nota (empresa, filial, tipo_operacao, finalidade);",
        "CREATE INDEX IF NOT EXISTS nf_nota_data_emissao_idx ON nf_nota (empresa, filial, data_emissao);",
        "CREATE INDEX IF NOT EXISTS nf_nota_destinatario_idx ON nf_nota (empresa, filial, destinatario_id);",
        "CREATE INDEX IF NOT EXISTS nf_nota_emitente_idx ON nf_nota (empresa, filial, emitente_id);",
        "CREATE INDEX IF NOT EXISTS nf_nota_chave_acesso_idx ON nf_nota (chave_acesso);",
        "CREATE INDEX IF NOT EXISTS nf_nota_chave_referenciada_idx ON nf_nota (chave_referenciada) WHERE chave_referenciada IS NOT NULL;",
        "CREATE INDEX IF NOT EXISTS nf_nota_pedido_origem_idx ON nf_nota (pedido_origem) WHERE pedido_origem IS NOT NULL;",
        "CREATE INDEX IF NOT EXISTS nf_nota_item_nota_idx ON nf_nota_item (nota_id);",
        "CREATE INDEX IF NOT EXISTS nf_nota_item_produto_idx ON nf_nota_item (produto_id);",
        "CREATE INDEX IF NOT EXISTS nf_item_imposto_item_idx ON nf_item_imposto (item_id);",
        "CREATE INDEX IF NOT EXISTS nf_transporte_nota_idx ON nf_transporte (nota_id);",
        "CREATE INDEX IF NOT EXISTS nf_nota_evento_nota_tipo_idx ON nf_nota_evento (nota_id, tipo);",
    ]
    with connections[alias].cursor() as cursor:
        for sql in stmts:
            cursor.execute(sql)


class Command(BaseCommand):
    help = "Cria índices de performance das tabelas de NF em todos os bancos de licenças"

    def handle(self, *args, **options):
        licencas = carregar_licencas_dict()
        if not licencas:
            raise CommandError("Nenhuma licença encontrada")

        ok = 0
        fail = 0
        for lic in licencas:
            alias = f"tenant_{lic['slug']}"
            connections.databases[alias] = montar_db_config(lic)
            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write(self.style.ERROR(f"[{alias}] Banco indisponível. Pulando..."))
                fail += 1
                continue

            try:
                criar_indices(alias)
                self.stdout.write(self.style.SUCCESS(f"[{alias}] Índices criados/garantidos."))
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{alias}] Erro ao criar índices: {e}"))
                fail += 1

        self.stdout.write(self.style.SUCCESS(f"Concluído. OK={ok} ERROS={fail}"))

