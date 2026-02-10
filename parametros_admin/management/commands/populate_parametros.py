from django.core.management.base import BaseCommand
from parametros_admin.populate_parametros import PopulateParametros


class Command(BaseCommand):
    help = 'Popular parâmetros do sistema automaticamente'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID da empresa específica'
        )
        parser.add_argument(
            '--filial',
            type=int,
            help='ID da filial específica'
        )
        parser.add_argument(
            '--database',
            default='default',
            help='Alias do banco de dados a ser usado (padrão: default)'
        )
        parser.add_argument(
            '--listar',
            action='store_true',
            help='Listar parâmetros existentes'
        )
    
    def handle(self, *args, **options):
        db_alias = options.get('database', 'default')
        populate = PopulateParametros(db_alias=db_alias)
        
        if options['listar']:
            populate.listar_parametros_existentes()
        elif options['empresa'] and options['filial']:
            populate.criar_modulos()
            populate.popular_empresa_filial_especifica(
                options['empresa'], 
                options['filial']
            )
        else:
            populate.executar_populacao_completa()