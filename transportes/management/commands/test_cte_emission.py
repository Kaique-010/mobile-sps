from django.core.management.base import BaseCommand
from core.utils import get_db_from_slug
from transportes.services.rascunho_service import RascunhoService
from transportes.services.emissao_service import EmissaoService
from transportes.models import Cte, CteDocumento
from Entidades.models import Entidades
from Licencas.models import Filiais, Empresas, Usuarios
from django.utils import timezone
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Teste de emissão de CTe'

    def add_arguments(self, parser):
        parser.add_argument('--slug', type=str, default='saveweb001')

    def handle(self, *args, **options):
        slug = options['slug']
        self.stdout.write(self.style.SUCCESS(f"Configurando banco para {slug}..."))
        
        try:
            # Configura conexão
            get_db_from_slug(slug)
            
            # Obtém objetos necessários
            filial = Filiais.objects.using(slug).first()
            if not filial:
                self.stdout.write(self.style.ERROR("Nenhuma filial encontrada."))
                return

            empresa = Empresas.objects.using(slug).first()
            if not empresa:
                # Se não tiver tabela empresas (alguns legados), tenta pegar info da filial
                pass

            usuario = Usuarios.objects.using(slug).first()
            if not usuario:
                self.stdout.write(self.style.ERROR("Nenhum usuário encontrado."))
                return

            remetente = Entidades.objects.using(slug).filter(enti_tipo_enti__in=['CL', 'AM']).first()
            destinatario = Entidades.objects.using(slug).filter(enti_tipo_enti__in=['CL', 'AM']).exclude(pk=remetente.pk if remetente else None).first()

            if not remetente or not destinatario:
                 self.stdout.write(self.style.ERROR("Remetente ou Destinatário não encontrados (precisa de 2 entidades)."))
                 # Tenta pegar qualquer entidade
                 entidades = list(Entidades.objects.using(slug).all()[:2])
                 if len(entidades) < 2:
                     return
                 remetente = entidades[0]
                 destinatario = entidades[1]

            self.stdout.write(f"Filial: {filial.empr_nome}")
            self.stdout.write(f"Remetente: {remetente.enti_nome}")
            self.stdout.write(f"Destinatário: {destinatario.enti_nome}")

            # 1. Criar Rascunho
            self.stdout.write("Criando rascunho...")
            service = RascunhoService(usuario, empresa, filial, slug=slug)
            dados_iniciais = {
                'remetente': remetente,
                'destinatario': destinatario,
                'tipo_servico': '0', # Normal
                'tipo_cte': '0', # Normal
                'observacoes': 'Teste de emissão automatizado via script',
            }
            cte = service.criar_rascunho(dados_iniciais)
            self.stdout.write(self.style.SUCCESS(f"Rascunho criado: ID {cte.id}"))

            # 2. Preencher dados obrigatórios (Simulação de preenchimento de abas)
            cte.natureza_operacao = "TRANSPORTE INTERMUNICIPAL"
            cte.cfop = 5352  # IntegerField
            cte.modelo = "57"
            cte.serie = "1"
            cte.tomador_servico = 0  # 0=Remetente (conforme validação)
            
            # Rota
            cte.uf_inicio = filial.empr_esta or 'PR'
            cte.municipio_inicio = filial.empr_cida or 'CURITIBA'
            cte.uf_fim = destinatario.enti_esta or 'SP'
            cte.municipio_fim = destinatario.enti_cida or 'SAO PAULO'
            
            # Carga
            cte.produto_predominante = "DIVERSOS"
            cte.valor_carga = Decimal("1000.00")
            cte.peso_bruto = Decimal("500.00")
            cte.peso_cubado = Decimal("100.00")
            cte.qtd_volumes = 10
            cte.especie_volumes = "CX"
            
            # Tributação
            cte.cst_icms = "00"
            cte.total_valor = Decimal("100.00") # Campo correto do model
            cte.liquido_a_receber = Decimal("100.00")
            cte.base_icms = Decimal("100.00")
            cte.aliq_icms = Decimal("12.00")
            cte.valor_icms = Decimal("12.00")
            
            # Componentes Valor
            cte.componente_nome = "FRETE VALOR"
            cte.frete_valor = Decimal("100.00") # Campo correto
            
            cte.save(using=slug)
            self.stdout.write("Dados complementares salvos.")

            # Adicionar documento (NFe)
            self.stdout.write("Adicionando documento NFe...")
            try:
                doc = CteDocumento(
                    cte=cte,
                    chave_nfe='35230912345678901234550010000000011000000001',
                    tipo_doc='00'
                )
                doc.save(using=slug)
                self.stdout.write("Documento NFe adicionado.")
                
                # Debug documentos
                docs_count = CteDocumento.objects.using(slug).filter(cte_id=cte.pk).count()
                self.stdout.write(f"Documentos vinculados: {docs_count}")
                if docs_count == 0:
                     # Tenta forçar refresh
                     cte.refresh_from_db(using=slug)
                     self.stdout.write(f"Documentos após refresh: {CteDocumento.objects.using(slug).filter(cte_id=cte.pk).count()}")

            except Exception as e:
                 self.stdout.write(self.style.WARNING(f"Não foi possível adicionar documento (tabela existe?): {e}"))

            # 3. Emitir
            self.stdout.write("Iniciando emissão...")
            emissao_service = EmissaoService(cte, slug=slug)
            
            # Mock de certificado se necessário será tratado internamente pelo service/gateway 
            # (já implementamos fallback no gateway)
            
            resultado = emissao_service.emitir()
            
            self.stdout.write(self.style.SUCCESS(f"Resultado da emissão: {resultado}"))
            
            # Recarregar CTe
            cte.refresh_from_db(using=slug)
            self.stdout.write(f"Status Final: {cte.status}")
            self.stdout.write(f"Chave Acesso: {cte.chave_de_acesso}")
            self.stdout.write(f"Protocolo: {cte.protocolo}")
            if cte.observacoes_fiscais:
                self.stdout.write(f"Msg Fiscal: {cte.observacoes_fiscais}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro durante o teste: {e}"))
            import traceback
            traceback.print_exc()
