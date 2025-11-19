# notas_fiscais/management/commands/migrar_notas.py

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from core.utils import get_db_from_slug
from Notas_Fiscais.legacy_migration.reader_legado import NotaLegadoReader
from Notas_Fiscais.legacy_migration.transformers import NotaTransformer
from Notas_Fiscais.legacy_migration.writer_novo import NotaWriter


def ensure_connection(alias):
    if alias in connections.databases:
        return
    get_db_from_slug(alias)

class Command(BaseCommand):
    help = "Migra notas fiscais do legado (nfevv) para o novo domínio SPS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--banco",
            type=str,
            default="default",
            help="Banco (slug) a ser usado na migração",
        )
        parser.add_argument(
            "--limite",
            type=int,
            default=100,
            help="Quantidade de notas para migrar",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Executa sem gravar no banco",
        )

    def handle(self, *args, **options):
        banco = options["banco"]
        limite = options["limite"]
        dry_run = options["dry_run"]

        self.stdout.write(self.style.NOTICE(f"🔵 Iniciando migração ({banco}) limite={limite} …"))

        # Garante que o alias de banco esteja disponível
        ensure_connection(banco)

        reader = NotaLegadoReader(banco)
        registros = reader.listar_notas(limite=limite)

        total = len(registros)
        self.stdout.write(self.style.WARNING(f"Encontradas {total} notas para migrar."))

        if total == 0:
            return self.stdout.write(self.style.SUCCESS("Nada para migrar."))

        for i, raw in enumerate(registros, start=1):
            self.stdout.write(f"\n➡ Nota {i}/{total}:")

            try:
                # -----------------------------------------------------------
                # TRANSFORM
                # -----------------------------------------------------------
                emitente_data = NotaTransformer.emitente(raw)
                destinatario_data = NotaTransformer.destinatario(raw)
                nota_data = NotaTransformer.nota(raw, emitente_data, destinatario_data)

                # -----------------------------------------------------------
                # LOOKUP emitente (Filiais) e destinatário (Entidades)
                # -----------------------------------------------------------
                emitente = NotaWriter.buscar_emitente(
                    empresa=raw["empresa"],
                    filial=raw["filial"],
                    banco=banco,
                )

                destinatario = NotaWriter.buscar_destinatario(
                    codigo_destinatario=raw["cliente"],
                    empresa=raw["empresa"],
                    banco=banco,
                )

                # -----------------------------------------------------------
                # WRITE
                # -----------------------------------------------------------
                resultado = NotaWriter.salvar_nota(
                    nota_data,
                    emitente,
                    destinatario,
                    banco=banco,
                    dry_run=dry_run,
                )

                if dry_run:
                    self.stdout.write(
                        self.style.SQL_TABLE(f"[DRY] {resultado['nota']}")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {resultado['msg']}")
                    )

                    try:
                        itens_rows = []
                        nota_id = raw.get("id")
                        if nota_id is not None:
                            itens_rows = reader.listar_itens_por_nota(nota_id)
                        if itens_rows:
                            NotaWriter.salvar_itens_e_impostos(
                                resultado["obj"],
                                itens_rows,
                                banco=banco,
                            )
                        NotaWriter.definir_transporte(
                            resultado["obj"],
                            raw,
                            banco=banco,
                        )
                        self.stdout.write(self.style.SUCCESS("✓ Itens/Impostos/Transporte migrados"))
                    except Exception as ex:
                        self.stdout.write(self.style.ERROR(f"✗ Erro itens/impostos/transporte: {str(ex)}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Erro: {str(e)}"))
                continue

        self.stdout.write(self.style.SUCCESS("🏁 Migração finalizada."))

