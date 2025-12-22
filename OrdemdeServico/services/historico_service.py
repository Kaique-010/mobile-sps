from collections import defaultdict, Counter
from datetime import datetime, timezone

def segundos_para_hhmmss(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segundos_rest = int(segundos % 60)
    return f"{horas:02d}:{minutos:02d}:{segundos_rest:02d}"

def calcular_tempos_por_os(queryset):
    tempos_por_os = defaultdict(lambda: defaultdict(int))
    workflows = defaultdict(list)
    
    for h in queryset:
        workflows[h.hist_orde].append(h)
    
    # Processa cada OS
    for ordem, eventos in workflows.items():
        # Garante ordem cronológica
        eventos.sort(key=lambda x: x.hist_data)

        if not eventos:
            continue

        # Calcula tempo entre movimentações consecutivas
        for i in range(len(eventos) - 1):
            atual = eventos[i]
            proximo = eventos[i + 1]
            setor_atual = atual.hist_seto_dest
            
            # Ignora se não tem setor de destino definido
            if not setor_atual:
                continue

            delta = (proximo.hist_data - atual.hist_data).total_seconds()
            
            # Ignora intervalos negativos ou zero
            if delta <= 0:
                continue

            tempos_por_os[ordem][f"Setor_{setor_atual}"] += delta
        
        # Se a OS tem apenas 1 evento ou o último evento tem setor destino,
        # calcula tempo até agora (para OSs em andamento)
        ultimo_evento = eventos[-1]
        if ultimo_evento.hist_seto_dest:
            agora = datetime.now(timezone.utc)
            ultima_data = ultimo_evento.hist_data
            if ultima_data.tzinfo is None:
                agora = datetime.now()
            
            delta_ate_agora = (agora - ultima_data).total_seconds()
            
            # Só adiciona se for positivo e menor que 30 dias (evita bugs)
            if 0 < delta_ate_agora < (30 * 24 * 3600):
                setor_key = f"Setor_{ultimo_evento.hist_seto_dest}"
                tempos_por_os[ordem][setor_key] += delta_ate_agora
                
    return tempos_por_os

def formatar_resultado_historico(tempos_por_os):
    detalhe_os = []
    resumo_setor_total = Counter()
    
    for ordem, setores in tempos_por_os.items():
        if not setores:
            continue
            
        setores_dict = {s: segundos_para_hhmmss(sec) for s, sec in setores.items()}
        
        setor_mais = max(setores.items(), key=lambda x: x[1])
        setor_menos = min(setores.items(), key=lambda x: x[1])
        
        detalhe_os.append({
            "ordem": ordem,
            "tempos_por_setor": setores_dict,
            "setor_mais_tempo": {
                "setor": setor_mais[0],
                "segundos": setor_mais[1],
                "hhmmss": segundos_para_hhmmss(setor_mais[1])
            },
            "setor_menos_tempo": {
                "setor": setor_menos[0],
                "segundos": setor_menos[1],
                "hhmmss": segundos_para_hhmmss(setor_menos[1])
            },
        })
        
        for setor, segundos in setores.items():
            resumo_setor_total[setor] += segundos
    
    resumo_setor = [
        {
            "setor": setor,
            "total_segundos": total,
            "total_hhmmss": segundos_para_hhmmss(total)
        }
        for setor, total in resumo_setor_total.items()
    ]
    resumo_setor = sorted(resumo_setor, key=lambda x: x["total_segundos"], reverse=True)
    
    return detalhe_os, resumo_setor
