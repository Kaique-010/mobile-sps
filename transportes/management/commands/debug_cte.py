from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.utils import get_db_from_slug
from transportes.builders.cte_xml_builder import CteXmlBuilder
from transportes.models import Cte, CteDocumento
from transportes.services.rascunho_service import RascunhoService
from Entidades.models import Entidades
from Licencas.models import Filiais, Empresas, Usuarios


class Command(BaseCommand):
    help = "Gera XML do CTe e salva um arquivo na raiz do projeto"

    def add_arguments(self, parser):
        parser.add_argument("--slug", type=str, default="saveweb001")
        parser.add_argument("--cte-id", type=str, default=None)
        parser.add_argument("--arquivo", type=str, default=None)
        parser.add_argument("--usar-salvo", action="store_true", default=False)
        parser.add_argument("--nao-salvar-db", action="store_true", default=False)

    def handle(self, *args, **options):
        slug = options["slug"]
        cte_id = options["cte_id"]
        arquivo = options["arquivo"]
        usar_salvo = bool(options["usar_salvo"])
        nao_salvar_db = bool(options["nao_salvar_db"])

        self.stdout.write(self.style.SUCCESS(f"Configurando banco para {slug}..."))
        get_db_from_slug(slug)

        if cte_id:
            cte = Cte.objects.using(slug).filter(pk=cte_id).first()
            if not cte:
                raise Exception(f"CTe não encontrado: {cte_id}")
        else:
            filial = Filiais.objects.using(slug).first()
            if not filial:
                raise Exception("Nenhuma filial encontrada.")

            empresa = Empresas.objects.using(slug).first()
            usuario = Usuarios.objects.using(slug).first()
            if not usuario:
                raise Exception("Nenhum usuário encontrado.")

            remetente = Entidades.objects.using(slug).filter(enti_tipo_enti__in=["CL", "AM"]).first()
            destinatario = (
                Entidades.objects.using(slug)
                .filter(enti_tipo_enti__in=["CL", "AM"])
                .exclude(pk=remetente.pk if remetente else None)
                .first()
            )

            if not remetente or not destinatario:
                entidades = list(Entidades.objects.using(slug).all()[:2])
                if len(entidades) < 2:
                    raise Exception("Precisa de pelo menos 2 entidades para Remetente/Destinatário.")
                remetente = entidades[0]
                destinatario = entidades[1]

            self.stdout.write(f"Filial: {filial.empr_nome}")
            self.stdout.write(f"Remetente: {remetente.enti_nome}")
            self.stdout.write(f"Destinatário: {destinatario.enti_nome}")

            self.stdout.write("Criando rascunho...")
            service = RascunhoService(usuario, empresa, filial, slug=slug)
            cte = service.criar_rascunho(
                {
                    "remetente": remetente,
                    "destinatario": destinatario,
                    "tipo_servico": "0",
                    "tipo_cte": "0",
                    "observacoes": "Debug XML via script",
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Rascunho criado: ID {cte.id}"))

            cte.natureza_operacao = "PRESTACAO DE SERVICO"
            cte.cfop = 5352
            cte.modelo = "57"
            cte.serie = "1"
            cte.tomador_servico = 0

            try:
                cte.cidade_coleta = int(getattr(filial, "empr_codi_cida", None) or 0)
            except Exception:
                cte.cidade_coleta = 0
            try:
                cte.cidade_entrega = int(getattr(destinatario, "enti_cida_codi", None) or 0)
            except Exception:
                cte.cidade_entrega = 0

            cte.produto_predominante = "DIVERSOS"
            cte.total_mercadoria = Decimal("1000.00")
            cte.peso_total = Decimal("500.000")

            cte.cst_icms = "00"
            cte.total_valor = Decimal("100.00")
            cte.liquido_a_receber = Decimal("100.00")
            cte.base_icms = Decimal("100.00")
            cte.aliq_icms = Decimal("12.00")
            cte.valor_icms = Decimal("12.00")

            cte.save(using=slug)

            doc = CteDocumento(cte=cte, chave_nfe="35230912345678901234550010000000011000000001", tipo_doc="00")
            doc.save(using=slug)

        if usar_salvo and (cte.xml_cte or "").strip():
            xml = str(cte.xml_cte).strip()
        else:
            xml = CteXmlBuilder(cte).build()

        if not nao_salvar_db:
            cte.xml_cte = xml
            cte.save(using=slug, update_fields=["xml_cte", "chave_de_acesso"])

        chave = (getattr(cte, "chave_de_acesso", None) or "").strip()
        base_nome = chave or str(cte.pk)
        nome_arquivo = arquivo or f"CTe_{base_nome}.xml"
        path = Path.cwd() / nome_arquivo
        path.write_text(xml, encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"XML gerado e salvo em: {path}"))
        self.stdout.write(f"CTe ID: {cte.pk}")
        if chave:
            self.stdout.write(f"Chave: {chave}")
