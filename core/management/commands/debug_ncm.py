from django.core.management.base import BaseCommand
from django.db import connections
from core.licencas_loader import carregar_licencas_dict
from Produtos.models import Produtos, Ncm, NcmAliquota
# Tentar importar NcmFiscalPadrao, pode estar em CFOP ou Produtos
try:
    from CFOP.models import NcmFiscalPadrao
except ImportError:
    try:
        from Produtos.models import NcmFiscalPadrao
    except ImportError:
        NcmFiscalPadrao = None

class Command(BaseCommand):
    help = 'Debug NCM lookup and taxation V3'

    def handle(self, *args, **options):
        self.stdout.write("--- Iniciando Debug NCM V3 ---")
        
        target_slug = "saveweb001"
        licencas = carregar_licencas_dict()
        licenca = next((l for l in licencas if l['slug'] == target_slug), None)
        
        if not licenca:
            self.stdout.write(self.style.ERROR(f"Licença '{target_slug}' não encontrada."))
            return

        self.stdout.write(f"Licença: {licenca['db_name']} @ {licenca['db_host']}")
        
        alias = "debug_saveweb001"
        connections.databases[alias] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": licenca["db_name"],
            "USER": licenca["db_user"],
            "PASSWORD": licenca["db_password"],
            "HOST": licenca["db_host"],
            "PORT": licenca["db_port"],
        }

        # 1. Contagem Ncm
        count_ncm = Ncm.objects.using(alias).count()
        self.stdout.write(f"\nTotal NCMs na tabela 'ncm': {count_ncm}")

        # 2. Contagem NcmAliquota
        count_aliq = NcmAliquota.objects.using(alias).count()
        self.stdout.write(f"Total NcmAliquota na tabela 'ncm_aliquotas_ibpt': {count_aliq}")

        # 3. Contagem NcmFiscalPadrao
        if NcmFiscalPadrao:
            count_fiscal = NcmFiscalPadrao.objects.using(alias).count()
            self.stdout.write(f"Total NcmFiscalPadrao: {count_fiscal}")
            
            if count_fiscal > 0:
                first = NcmFiscalPadrao.objects.using(alias).first()
                self.stdout.write(f"Exemplo NcmFiscalPadrao: {first} (NCM ID: {first.nfiscalpadrao_ncm_id})")
        else:
             self.stdout.write("Modelo NcmFiscalPadrao não encontrado.")

        # 4. Verificar Produto 3 novamente
        try:
            prod = Produtos.objects.using(alias).get(prod_codi=3)
            prod_ncm = prod.prod_ncm
            self.stdout.write(f"\nProduto 3 NCM: '{prod_ncm}'")
            
            # Tentar buscar esse NCM especificamente
            ncm_obj = Ncm.objects.using(alias).filter(ncm_codi=prod_ncm).first()
            if ncm_obj:
                 self.stdout.write(f" -> Encontrado em Ncm: {ncm_obj}")
            else:
                 self.stdout.write(f" -> NÃO encontrado em Ncm (direto).")
                 
            # Tentar dotted
            if len(prod_ncm) == 8:
                 dotted = f"{prod_ncm[:4]}.{prod_ncm[4:6]}.{prod_ncm[6:]}"
                 ncm_dotted = Ncm.objects.using(alias).filter(ncm_codi=dotted).first()
                 if ncm_dotted:
                     self.stdout.write(f" -> Encontrado em Ncm (dotted {dotted}): {ncm_dotted}")
                 else:
                     self.stdout.write(f" -> NÃO encontrado em Ncm (dotted {dotted}).")
            
        except Produtos.DoesNotExist:
            self.stdout.write("Produto 3 não encontrado.")
