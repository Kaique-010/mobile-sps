from django.core.management.base import BaseCommand
from parametros_admin.models import Modulo, PermissaoModulo
from django.db import transaction
import json
from pathlib import Path

class Command(BaseCommand):
    help = 'Popula a tabela de módulos com os módulos do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--popular-permissoes',
            action='store_true',
            help='Popular permissões baseadas no licencas.json',
        )
        parser.add_argument(
            '--banco',
            type=str,
            help='Nome do banco de dados para popular permissões',
        )

    def handle(self, *args, **options):
        modulos_sistema = [
            {
                'modu_nome': 'dashboards',
                'modu_desc': 'Dashboards e relatórios gerenciais',
                'modu_icone': 'dashboard',
                'modu_ordem': 1
            },
            {
                'modu_nome': 'dash',
                'modu_desc': 'Dashboard principal',
                'modu_icone': 'dashboard',
                'modu_ordem': 2
            },
            {
                'modu_nome': 'Produtos',
                'modu_desc': 'Gestão de produtos e serviços',
                'modu_icone': 'inventory',
                'modu_ordem': 3
            },
            {
                'modu_nome': 'Pedidos',
                'modu_desc': 'Gestão de pedidos de venda',
                'modu_icone': 'shopping_cart',
                'modu_ordem': 4
            },
            {
                'modu_nome': 'Entradas_Estoque',
                'modu_desc': 'Controle de entradas no estoque',
                'modu_icone': 'input',
                'modu_ordem': 5
            },
            {
                'modu_nome': 'Saidas_Estoque',
                'modu_desc': 'Controle de saídas do estoque',
                'modu_icone': 'output',
                'modu_ordem': 6
            },
            {
                'modu_nome': 'listacasamento',
                'modu_desc': 'Lista de casamento',
                'modu_icone': 'list',
                'modu_ordem': 7
            },
            {
                'modu_nome': 'Entidades',
                'modu_desc': 'Gestão de clientes e fornecedores',
                'modu_icone': 'people',
                'modu_ordem': 8
            },
            {
                'modu_nome': 'Orcamentos',
                'modu_desc': 'Gestão de orçamentos',
                'modu_icone': 'description',
                'modu_ordem': 9
            },
            {
                'modu_nome': 'contratos',
                'modu_desc': 'Gestão de contratos',
                'modu_icone': 'assignment',
                'modu_ordem': 10
            },
            {
                'modu_nome': 'implantacao',
                'modu_desc': 'Gestão de implantações',
                'modu_icone': 'build',
                'modu_ordem': 11
            },
            {
                'modu_nome': 'Financeiro',
                'modu_desc': 'Gestão financeira',
                'modu_icone': 'account_balance',
                'modu_ordem': 12
            },
            {
                'modu_nome': 'OrdemdeServico',
                'modu_desc': 'Gestão de ordens de serviço',
                'modu_icone': 'work',
                'modu_ordem': 13
            },
            {
                'modu_nome': 'O_S',
                'modu_desc': 'Ordens de serviço',
                'modu_icone': 'work',
                'modu_ordem': 14
            },
            {
                'modu_nome': 'SpsComissoes',
                'modu_desc': 'Gestão de comissões',
                'modu_icone': 'monetization_on',
                'modu_ordem': 15
            },
            {
                'modu_nome': 'OrdemProducao',
                'modu_desc': 'Gestão de ordens de produção',
                'modu_icone': 'factory',
                'modu_ordem': 16
            },
            {
                'modu_nome': 'parametros_admin',
                'modu_desc': 'Administração de parâmetros do sistema',
                'modu_icone': 'settings',
                'modu_ordem': 17
            },
            {
                'modu_nome': 'CaixaDiario',
                'modu_desc': 'Controle de caixa diário',
                'modu_icone': 'account_balance_wallet',
                'modu_ordem': 18
            },
            {
                'modu_nome': 'contas_a_pagar',
                'modu_desc': 'Gestão de contas a pagar',
                'modu_icone': 'payment',
                'modu_ordem': 19
            },
            {
                'modu_nome': 'contas_a_receber',
                'modu_desc': 'Gestão de contas a receber',
                'modu_icone': 'receipt',
                'modu_ordem': 20
            },
            {
                'modu_nome': 'Gerencial',
                'modu_desc': 'Relatórios gerenciais',
                'modu_icone': 'analytics',
                'modu_ordem': 21
            },
            {
                'modu_nome': 'DRE',
                'modu_desc': 'Demonstração do resultado do exercício',
                'modu_icone': 'assessment',
                'modu_ordem': 22
            },
            {
                'modu_nome': 'EnvioCobranca',
                'modu_desc': 'Envio de cobrança',
                'modu_icone': 'email',
                'modu_ordem': 23
            },
            {
                'modu_nome': 'Sdk_recebimentos',
                'modu_desc': 'SDK de recebimentos',
                'modu_icone': 'account_balance',
                'modu_ordem': 24
            },
            {
                'modu_nome': 'auditoria',
                'modu_desc': 'Sistema de auditoria',
                'modu_icone': 'security',
                'modu_ordem': 25
            },
            {
                'modu_nome': 'notificacoes',
                'modu_desc': 'Sistema de notificações',
                'modu_icone': 'notifications',
                'modu_ordem': 26
            },
            {
                'modu_nome': 'planocontas',
                'modu_desc': 'Plano de contas',
                'modu_icone': 'account_tree',
                'modu_ordem': 27
            }
        ]

        with transaction.atomic():
            criados = 0
            atualizados = 0
            
            for modulo_data in modulos_sistema:
                modulo, created = Modulo.objects.get_or_create(
                    modu_nome=modulo_data['modu_nome'],
                    defaults=modulo_data
                )
                
                if created:
                    criados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Módulo criado: {modulo.modu_nome}')
                    )
                else:
                    # Atualizar dados existentes
                    for key, value in modulo_data.items():
                        setattr(modulo, key, value)
                    modulo.save()
                    atualizados += 1
                    self.stdout.write(
                        self.style.WARNING(f'Módulo atualizado: {modulo.modu_nome}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Processo concluído! Criados: {criados}, Atualizados: {atualizados}'
            )
        )
        
        # Popular permissões se solicitado
        if options['popular_permissoes']:
            self.popular_permissoes(options['banco'])
    
    def popular_permissoes(self, banco):
        """Popula permissões baseadas no licencas.json"""
        try:
            # Carregar licencas.json
            json_path = Path(__file__).resolve().parent.parent.parent.parent / 'core' / 'licencas.json'
            with open(json_path, 'r') as f:
                licencas = json.load(f)
            
            if not banco:
                self.stdout.write(
                    self.style.ERROR('Banco de dados não especificado. Use --banco <nome_do_banco>')
                )
                return
            
            permissoes_criadas = 0
            
            for licenca in licencas:
                slug = licenca.get('slug')
                modulos = licenca.get('modulos', [])
                
                if slug == banco:
                    self.stdout.write(f'Populando permissões para licença: {slug}')
                    
                    # Para cada módulo da licença, criar permissão
                    for nome_modulo in modulos:
                        try:
                            modulo = Modulo.objects.get(modu_nome=nome_modulo, modu_ativ=True)
                            
                            # Criar permissão para empresa 1, filial 1 (padrão)
                            permissao, created = PermissaoModulo.objects.using(banco).get_or_create(
                                perm_empr=1,
                                perm_fili=1,
                                perm_modu=modulo,
                                defaults={
                                    'perm_ativ': True,
                                    'perm_usua_libe': 'sistema'
                                }
                            )
                            
                            if created:
                                permissoes_criadas += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Permissão criada: {nome_modulo}')
                                )
                            else:
                                self.stdout.write(
                                    self.style.WARNING(f'Permissão já existe: {nome_modulo}')
                                )
                                
                        except Modulo.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(f'Módulo não encontrado: {nome_modulo}')
                            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Permissões populadas: {permissoes_criadas}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao popular permissões: {e}')
            ) 