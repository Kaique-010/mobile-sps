from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta
from auditoria.utils import limpar_logs_antigos
from auditoria.models import LogAcao

class Command(BaseCommand):
    help = 'Remove logs de auditoria antigos para manter a performance do sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=365,
            help='Número de dias para manter os logs (padrão: 365)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra quantos logs seriam removidos sem executar a remoção'
        )
        
        parser.add_argument(
            '--licenca',
            type=str,
            help='Remove logs apenas de uma licença específica'
        )
        
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a remoção sem solicitar confirmação interativa'
        )
    
    def handle(self, *args, **options):
        dias = options['dias']
        dry_run = options['dry_run']
        licenca = options['licenca']
        confirmar = options['confirmar']
        
        data_limite = timezone.now() - timedelta(days=dias)
        
        # Construir queryset
        queryset = LogAcao.objects.filter(data_hora__lt=data_limite)
        
        if licenca:
            queryset = queryset.filter(licenca=licenca)
        
        total_logs = queryset.count()
        
        if total_logs == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Nenhum log encontrado anterior a {data_limite.strftime("%d/%m/%Y")}'
                )
            )
            return
        
        # Mostrar estatísticas
        self.stdout.write(f'\nEstatísticas dos logs a serem removidos:')
        self.stdout.write(f'- Total de logs: {total_logs:,}')
        self.stdout.write(f'- Data limite: {data_limite.strftime("%d/%m/%Y %H:%M:%S")}')
        
        if licenca:
            self.stdout.write(f'- Licença: {licenca}')
        
        # Estatísticas por tipo de ação
        stats_acao = queryset.values('tipo_acao').annotate(
            total=models.Count('id')
        ).order_by('-total')
        
        if stats_acao:
            self.stdout.write('\nPor tipo de ação:')
            for stat in stats_acao:
                self.stdout.write(f'  - {stat["tipo_acao"]}: {stat["total"]:,}')
        
        # Estatísticas por mês
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        stats_mes = queryset.annotate(
            mes=TruncMonth('data_hora')
        ).values('mes').annotate(
            total=Count('id')
        ).order_by('mes')[:12]  # Últimos 12 meses
        
        if stats_mes:
            self.stdout.write('\nPor mês (últimos 12 meses a serem removidos):')
            for stat in stats_mes:
                mes_str = stat['mes'].strftime('%m/%Y')
                self.stdout.write(f'  - {mes_str}: {stat["total"]:,}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] {total_logs:,} logs seriam removidos.'
                )
            )
            return
        
        # Solicitar confirmação
        if not confirmar:
            resposta = input(
                f'\nDeseja realmente remover {total_logs:,} logs? '
                f'Esta ação não pode ser desfeita. (s/N): '
            )
            
            if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
                self.stdout.write(
                    self.style.WARNING('Operação cancelada pelo usuário.')
                )
                return
        
        # Executar remoção em lotes para evitar sobrecarga
        self.stdout.write('\nIniciando remoção...')
        
        lote_size = 1000
        total_removidos = 0
        
        while True:
            # Buscar IDs em lotes
            ids_lote = list(
                queryset.values_list('id', flat=True)[:lote_size]
            )
            
            if not ids_lote:
                break
            
            # Remover lote
            LogAcao.objects.filter(id__in=ids_lote).delete()
            total_removidos += len(ids_lote)
            
            self.stdout.write(
                f'Removidos {total_removidos:,} de {total_logs:,} logs...',
                ending='\r'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n\nConcluído! {total_removidos:,} logs foram removidos com sucesso.'
            )
        )
        
        # Mostrar estatísticas finais
        logs_restantes = LogAcao.objects.count()
        self.stdout.write(
            f'Logs restantes no sistema: {logs_restantes:,}'
        )
        
        # Sugerir otimização se necessário
        if logs_restantes > 100000:
            self.stdout.write(
                self.style.WARNING(
                    '\nAtenção: Ainda há muitos logs no sistema. '
                    'Considere executar VACUUM na base de dados para otimizar o espaço.'
                )
            )