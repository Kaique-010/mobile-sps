from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from Licencas.models import Filiais
from Licencas.crypto import decrypt_bytes, decrypt_str
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from core.registry import get_licenca_db_config


class Command(BaseCommand):
    help = "Valida o certificado A1 de uma filial descriptografando do banco e carregando via PKCS12"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            type=int,
            required=True,
            help="Código da empresa (empr_empr) da filial",
        )
        parser.add_argument(
            "--filial",
            type=int,
            required=True,
            help="Código da filial (empr_codi)",
        )
        parser.add_argument(
            "--alias",
            type=str,
            default=None,
            help="Alias de banco de dados Django a ser usado diretamente (ex.: default).",
        )
        parser.add_argument(
            "--slug",
            type=str,
            default=None,
            help="Slug da licença para resolver o alias via loader (ex.: demonstracao, savexml839, casaa).",
        )

    def handle(self, *args, **options):
        empresa = options["empresa"]
        filial = options["filial"]
        alias = options.get("alias")
        slug = options.get("slug")

        if slug:
            alias = get_licenca_db_config(slug)
        if not alias:
            alias = "default"

        if alias not in connections:
            raise CommandError(f"Alias de banco de dados inválido: {alias}")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Verificando certificado A1: empresa={empresa} filial={filial} alias={alias} slug={slug or '-'}"
            )
        )

        filial_obj = (
            Filiais.objects.using(alias)
            .filter(empr_empr=empresa, empr_codi=filial)
            .first()
        )

        if not filial_obj:
            raise CommandError(f"Filial não encontrada (empresa={empresa}, filial={filial}) no alias {alias}")

        if not filial_obj.empr_cert_digi:
            raise CommandError("Campo empr_cert_digi vazio: filial não possui certificado digital cadastrado.")

        self.stdout.write(f"Nome certificado armazenado: {getattr(filial_obj, 'empr_cert', None)}")

        senha_token = filial_obj.empr_senh_cert
        cert_token = filial_obj.empr_cert_digi

        # Descriptografar senha
        try:
            senha = decrypt_str(senha_token)
            self.stdout.write(self.style.SUCCESS("Senha descriptografada com sucesso via decrypt_str()."))
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Falha ao descriptografar senha via decrypt_str(): {e}. Usando valor bruto.")
            )
            senha = senha_token

        # Descriptografar certificado
        try:
            cert_bytes = decrypt_bytes(cert_token)
            self.stdout.write(
                self.style.SUCCESS(f"Certificado descriptografado com sucesso via decrypt_bytes(). Tamanho={len(cert_bytes)} bytes.")
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Falha ao descriptografar certificado via decrypt_bytes(): {e}. Usando valor bruto.")
            )
            cert_bytes = cert_token
            if hasattr(cert_bytes, "tobytes"):
                cert_bytes = cert_bytes.tobytes()

        if not isinstance(cert_bytes, (bytes, bytearray)):
            raise CommandError(f"Conteúdo do certificado não é bytes. Tipo atual: {type(cert_bytes)}")

        self.stdout.write("Validando pacote PKCS12 com load_key_and_certificates()...")

        try:
            key, cert, add_certs = load_key_and_certificates(
                cert_bytes,
                senha.encode("utf-8") if isinstance(senha, str) else senha,
            )
        except Exception as e:
            raise CommandError(f"Falha ao carregar certificado digital A1 via PKCS12: {e!r}")

        if cert is None:
            raise CommandError("PKCS12 carregado, mas certificado principal veio como None.")

        subject = cert.subject.rfc4514_string() if hasattr(cert, "subject") else "<sem subject>"
        issuer = cert.issuer.rfc4514_string() if hasattr(cert, "issuer") else "<sem issuer>"

        self.stdout.write(self.style.SUCCESS("Certificado PKCS12 carregado com sucesso!"))
        self.stdout.write(f"Subject: {subject}")
        self.stdout.write(f"Issuer:  {issuer}")

