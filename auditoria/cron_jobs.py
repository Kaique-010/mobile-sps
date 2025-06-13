# Configurações para tarefas agendadas do sistema de auditoria
# Este arquivo pode ser usado com django-crontab ou celery beat

from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('auditoria.cron')

def limpar_logs_antigos():
    """
    Tarefa agendada para limpeza automática de logs antigos
    Recomendado: executar diariamente às 02:00
    """
    try:
        logger.info('Iniciando limpeza automática de logs antigos')
        
        # Manter logs dos últimos 365 dias (1 ano)
        call_command('limpar_logs_auditoria', '--dias=365', '--confirmar')
        
        logger.info('Limpeza de logs concluída com sucesso')
    except Exception as e:
        logger.error(f'Erro na limpeza automática de logs: {e}')

def gerar_relatorio_diario():
    """
    Gera relatório diário de atividades
    Recomendado: executar diariamente às 08:00
    """
    try:
        logger.info('Gerando relatório diário de atividades')
        
        hoje = timezone.now().date()
        arquivo_saida = f'/tmp/relatorio_auditoria_{hoje.strftime("%Y%m%d")}.json'
        
        call_command(
            'relatorio_auditoria',
            '--tipo=atividades',
            '--dias=1',
            '--formato=json',
            f'--output={arquivo_saida}'
        )
        
        logger.info(f'Relatório diário salvo em: {arquivo_saida}')
    except Exception as e:
        logger.error(f'Erro na geração do relatório diário: {e}')

def detectar_atividades_suspeitas():
    """
    Detecta e reporta atividades suspeitas
    Recomendado: executar a cada 4 horas
    """
    try:
        from auditoria.utils import detectar_atividades_suspeitas
        
        logger.info('Verificando atividades suspeitas')
        
        suspeitas = detectar_atividades_suspeitas(dias=1)
        
        if suspeitas:
            logger.warning(f'Detectadas {len(suspeitas)} atividades suspeitas:')
            
            for suspeita in suspeitas:
                if suspeita['gravidade'] == 'alta':
                    logger.error(
                        f"[ALTA] {suspeita['tipo']} - "
                        f"Usuário: {suspeita['usuario']} - "
                        f"Detalhes: {suspeita['detalhes']}"
                    )
                else:
                    logger.warning(
                        f"[MÉDIA] {suspeita['tipo']} - "
                        f"Usuário: {suspeita['usuario']} - "
                        f"Detalhes: {suspeita['detalhes']}"
                    )
            
            # Aqui você pode adicionar notificações por email, Slack, etc.
            # enviar_notificacao_suspeitas(suspeitas)
        else:
            logger.info('Nenhuma atividade suspeita detectada')
            
    except Exception as e:
        logger.error(f'Erro na detecção de atividades suspeitas: {e}')

def gerar_relatorio_semanal():
    """
    Gera relatório semanal completo
    Recomendado: executar semanalmente (domingo às 09:00)
    """
    try:
        logger.info('Gerando relatório semanal')
        
        hoje = timezone.now().date()
        arquivo_saida = f'/tmp/relatorio_semanal_{hoje.strftime("%Y%m%d")}.json'
        
        call_command(
            'relatorio_auditoria',
            '--tipo=atividades',
            '--dias=7',
            '--formato=json',
            f'--output={arquivo_saida}'
        )
        
        # Também gerar relatório de suspeitas da semana
        arquivo_suspeitas = f'/tmp/suspeitas_semanal_{hoje.strftime("%Y%m%d")}.json'
        
        call_command(
            'relatorio_auditoria',
            '--tipo=suspeitas',
            '--dias=7',
            '--formato=json',
            f'--output={arquivo_suspeitas}'
        )
        
        logger.info(f'Relatórios semanais salvos em: {arquivo_saida} e {arquivo_suspeitas}')
    except Exception as e:
        logger.error(f'Erro na geração do relatório semanal: {e}')

def backup_logs_importantes():
    """
    Faz backup de logs importantes antes da limpeza
    Recomendado: executar mensalmente
    """
    try:
        logger.info('Iniciando backup de logs importantes')
        
        hoje = timezone.now().date()
        mes_passado = hoje - timedelta(days=30)
        
        # Backup de logs de exclusão (DELETE)
        arquivo_exclusoes = f'/backup/logs_exclusoes_{mes_passado.strftime("%Y%m")}.csv'
        
        call_command(
            'relatorio_auditoria',
            '--tipo=csv',
            f'--data-inicio={mes_passado}',
            f'--data-fim={hoje}',
            f'--output={arquivo_exclusoes}'
        )
        
        # Backup de atividades suspeitas
        arquivo_suspeitas = f'/backup/suspeitas_{mes_passado.strftime("%Y%m")}.json'
        
        call_command(
            'relatorio_auditoria',
            '--tipo=suspeitas',
            '--dias=30',
            '--formato=json',
            f'--output={arquivo_suspeitas}'
        )
        
        logger.info(f'Backup concluído: {arquivo_exclusoes}, {arquivo_suspeitas}')
    except Exception as e:
        logger.error(f'Erro no backup de logs: {e}')

# Configuração para django-crontab
# Adicione ao settings.py:
# CRONJOBS = [
#     ('0 2 * * *', 'auditoria.cron_jobs.limpar_logs_antigos'),  # Diário às 02:00
#     ('0 8 * * *', 'auditoria.cron_jobs.gerar_relatorio_diario'),  # Diário às 08:00
#     ('0 */4 * * *', 'auditoria.cron_jobs.detectar_atividades_suspeitas'),  # A cada 4h
#     ('0 9 * * 0', 'auditoria.cron_jobs.gerar_relatorio_semanal'),  # Domingo às 09:00
#     ('0 3 1 * *', 'auditoria.cron_jobs.backup_logs_importantes'),  # 1º do mês às 03:00
# ]

# Configuração para Celery Beat
# Adicione ao settings.py:
# CELERY_BEAT_SCHEDULE = {
#     'limpar-logs-antigos': {
#         'task': 'auditoria.cron_jobs.limpar_logs_antigos',
#         'schedule': crontab(hour=2, minute=0),  # Diário às 02:00
#     },
#     'relatorio-diario': {
#         'task': 'auditoria.cron_jobs.gerar_relatorio_diario',
#         'schedule': crontab(hour=8, minute=0),  # Diário às 08:00
#     },
#     'detectar-suspeitas': {
#         'task': 'auditoria.cron_jobs.detectar_atividades_suspeitas',
#         'schedule': crontab(minute=0, hour='*/4'),  # A cada 4 horas
#     },
#     'relatorio-semanal': {
#         'task': 'auditoria.cron_jobs.gerar_relatorio_semanal',
#         'schedule': crontab(hour=9, minute=0, day_of_week=0),  # Domingo às 09:00
#     },
#     'backup-logs': {
#         'task': 'auditoria.cron_jobs.backup_logs_importantes',
#         'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 1º do mês às 03:00
#     },
# }

def enviar_notificacao_suspeitas(suspeitas):
    """
    Função para enviar notificações sobre atividades suspeitas
    Implemente conforme sua necessidade (email, Slack, etc.)
    """
    # Exemplo de implementação com email
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        if not hasattr(settings, 'AUDITORIA_EMAIL_ALERTAS'):
            return
        
        destinatarios = settings.AUDITORIA_EMAIL_ALERTAS
        
        assunto = f'[ALERTA] {len(suspeitas)} atividades suspeitas detectadas'
        
        mensagem = 'Atividades suspeitas detectadas no sistema:\n\n'
        
        for suspeita in suspeitas:
            mensagem += f"[{suspeita['gravidade'].upper()}] {suspeita['tipo']}\n"
            mensagem += f"Usuário: {suspeita['usuario']}\n"
            mensagem += f"Detalhes: {suspeita['detalhes']}\n\n"
        
        mensagem += 'Verifique o sistema de auditoria para mais detalhes.'
        
        send_mail(
            assunto,
            mensagem,
            settings.DEFAULT_FROM_EMAIL,
            destinatarios,
            fail_silently=False,
        )
        
        logger.info(f'Notificação de suspeitas enviada para {len(destinatarios)} destinatários')
        
    except Exception as e:
        logger.error(f'Erro ao enviar notificação de suspeitas: {e}')