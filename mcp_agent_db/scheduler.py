from apscheduler.schedulers.background import BackgroundScheduler
from tools.relatorios_agendados import (
    relatorio_estoque_baixo,
    contas_a_pagar_semana,
    sugestao_compras_estoque,
)

def start_scheduler():
    scheduler = BackgroundScheduler()

    # Slugs dos clientes a serem monitorados
    slugs = ["casaa", "spartacus"]

    for slug in slugs:
        scheduler.add_job(lambda s=slug: print(relatorio_estoque_baixo(s)), 'cron', hour=7)
        scheduler.add_job(lambda s=slug: print(contas_a_pagar_semana(s)), 'cron', hour=8)
        scheduler.add_job(lambda s=slug: print(sugestao_compras_estoque(s)), 'cron', hour=9)

    scheduler.start()
    print("✅ Scheduler iniciado!")

# Em main.py
# from scheduler import start_scheduler
# start_scheduler()
