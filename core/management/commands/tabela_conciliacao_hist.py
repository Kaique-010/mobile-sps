
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


def criar_tabela_conciliacao_hist(alias: str):
    with connections[alias].cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conciliacao_hist (
                id SERIAL PRIMARY KEY,

                conc_hist_nume INTEGER NOT NULL,
                conc_hist_empr INTEGER NOT NULL,
                conc_hist_fili INTEGER NOT NULL,

                conc_hist_item_extrato INTEGER NOT NULL,
                conc_hist_origem VARCHAR(10) NOT NULL,

                conc_hist_titu VARCHAR(13),
                conc_hist_enti INTEGER,
                conc_hist_seri VARCHAR(5),
                conc_hist_parc VARCHAR(4),

                conc_hist_banc INTEGER,
                conc_hist_ctrl_banc INTEGER,
                conc_hist_baixa_pagar_sequ INTEGER,
                conc_hist_baixa_receber_sequ INTEGER,

                conc_hist_valor NUMERIC(15, 2) NOT NULL,

                conc_hist_data TIMESTAMP NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT ck_conc_hist_origem
                    CHECK (
                        conc_hist_origem IN (
                            'PAGAR',
                            'RECEBER',
                            'BANCO',
                            'AVULSO',
                        )
                    )
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_conc_hist_escopo
            ON conciliacao_hist (
                conc_hist_empr,
                conc_hist_fili,
                conc_hist_nume
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_conc_hist_item_extrato
            ON conciliacao_hist (
                conc_hist_empr,
                conc_hist_fili,
                conc_hist_nume,
                conc_hist_item_extrato
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_conc_hist_origem
            ON conciliacao_hist (
                conc_hist_empr,
                conc_hist_fili,
                conc_hist_origem
            );
        """)


class Command(BaseCommand):
    help = (
        "Cria a tabela conciliacao_hist e seus índices "
        "nos bancos de licenças."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            help="Slug do tenant específico.",
        )

        parser.add_argument(
            "--tenant",
            type=str,
            help="Alias de --slug.",
        )

    def handle(self, *args, **options):
        slug = options.get("slug")
        tenant = options.get("tenant")

        if slug and tenant and slug != tenant:
            raise CommandError(
                "Use apenas --slug ou --tenant, "
                "ou informe o mesmo valor nos dois."
            )

        slug_alvo = slug or tenant
        licencas = carregar_licencas_dict()

        if not licencas:
            raise CommandError(
                "Nenhuma licença encontrada."
            )

        if slug_alvo:
            licencas = [
                lic
                for lic in licencas
                if lic.get("slug") == slug_alvo
            ]

            if not licencas:
                raise CommandError(
                    "Nenhuma licença encontrada para "
                    "slug={}".format(slug_alvo)
                )

        sucesso = 0
        falhas = 0

        for lic in licencas:
            alias = "tenant_{}".format(lic["slug"])

            connections.databases[alias] = montar_db_config(lic)

            self.stdout.write(
                self.style.WARNING(
                    "[{}] Criando conciliacao_hist...".format(alias)
                )
            )

            try:
                with connections[alias].cursor() as cursor:
                    cursor.execute("SELECT 1")

                criar_tabela_conciliacao_hist(alias)

                self.stdout.write(
                    self.style.SUCCESS(
                        "[{}] Tabela e índices verificados.".format(
                            alias
                        )
                    )
                )
                sucesso += 1

            except OperationalError as erro:
                falhas += 1
                self.stdout.write(
                    self.style.ERROR(
                        "[{}] Banco inacessível: {}".format(
                            alias,
                            erro,
                        )
                    )
                )

            except Exception as erro:
                falhas += 1
                self.stdout.write(
                    self.style.ERROR(
                        "[{}] Erro ao criar estrutura: {}".format(
                            alias,
                            erro,
                        )
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Concluído. Sucesso: {} | Falhas: {}".format(
                    sucesso,
                    falhas,
                )
            )
        )