from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import LogAcao
import json

def gerar_relatorio_atividades(data_inicio=None, data_fim=None, usuario=None, empresa=None):
    """
    Gera um relatório de atividades com estatísticas
    """
    queryset = LogAcao.objects.all()
    
    # Aplicar filtros
    if data_inicio:
        queryset = queryset.filter(data_hora__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_hora__lte=data_fim)
    if usuario:
        queryset = queryset.filter(usuario=usuario)
    if empresa:
        queryset = queryset.filter(empresa=empresa)
    
    # Estatísticas por tipo de ação
    stats_por_acao = queryset.values('tipo_acao').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Estatísticas por usuário
    stats_por_usuario = queryset.values(
        'usuario__usua_nome'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Estatísticas por modelo
    stats_por_modelo = queryset.filter(
        modelo__isnull=False
    ).values('modelo').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Atividades por hora do dia
    stats_por_hora = queryset.extra(
        select={'hora': 'EXTRACT(hour FROM data_hora)'}
    ).values('hora').annotate(
        total=Count('id')
    ).order_by('hora')
    
    return {
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim
        },
        'total_logs': queryset.count(),
        'por_acao': list(stats_por_acao),
        'por_usuario': list(stats_por_usuario),
        'por_modelo': list(stats_por_modelo),
        'por_hora': list(stats_por_hora)
    }

def buscar_alteracoes_objeto(modelo, objeto_id):
    """
    Busca todas as alterações de um objeto específico
    """
    logs = LogAcao.objects.filter(
        modelo=modelo,
        objeto_id=str(objeto_id)
    ).order_by('data_hora')
    
    historico = []
    
    for log in logs:
        entrada = {
            'data_hora': log.data_hora,
            'usuario': log.usuario.usua_nome if log.usuario else 'Sistema',
            'acao': log.get_tipo_acao_display(),
            'ip': log.ip,
            'alteracoes': []
        }
        
        if log.campos_alterados:
            for campo, detalhes in log.campos_alterados.items():
                if isinstance(detalhes, dict) and 'antes' in detalhes:
                    entrada['alteracoes'].append({
                        'campo': campo,
                        'valor_anterior': detalhes['antes'],
                        'valor_novo': detalhes['depois']
                    })
        
        # Para criação, mostrar todos os dados
        if log.tipo_acao == 'POST' and log.dados_depois:
            entrada['dados_criados'] = log.dados_depois
        
        # Para exclusão, mostrar dados excluídos
        if log.tipo_acao == 'DELETE' and log.dados_antes:
            entrada['dados_excluidos'] = log.dados_antes
        
        historico.append(entrada)
    
    return historico

def detectar_atividades_suspeitas(dias=7):
    """
    Detecta atividades potencialmente suspeitas
    """
    data_limite = timezone.now() - timedelta(days=dias)
    
    suspeitas = []
    
    # 1. Muitas exclusões por um usuário
    exclusoes_por_usuario = LogAcao.objects.filter(
        data_hora__gte=data_limite,
        tipo_acao='DELETE'
    ).values('usuario__usua_nome').annotate(
        total=Count('id')
    ).filter(total__gte=10)
    
    for item in exclusoes_por_usuario:
        suspeitas.append({
            'tipo': 'Muitas exclusões',
            'usuario': item['usuario__usua_nome'],
            'detalhes': f"{item['total']} exclusões em {dias} dias",
            'gravidade': 'alta' if item['total'] >= 50 else 'media'
        })
    
    # 2. Atividade fora do horário comercial
    atividade_noturna = LogAcao.objects.filter(
        data_hora__gte=data_limite
    ).extra(
        where=["EXTRACT(hour FROM data_hora) < 6 OR EXTRACT(hour FROM data_hora) > 22"]
    ).values('usuario__usua_nome').annotate(
        total=Count('id')
    ).filter(total__gte=5)
    
    for item in atividade_noturna:
        suspeitas.append({
            'tipo': 'Atividade fora do horário',
            'usuario': item['usuario__usua_nome'],
            'detalhes': f"{item['total']} ações fora do horário comercial",
            'gravidade': 'media'
        })
    
    # 3. Múltiplos IPs para o mesmo usuário
    usuarios_multiplos_ips = LogAcao.objects.filter(
        data_hora__gte=data_limite,
        ip__isnull=False
    ).values('usuario__usua_nome').annotate(
        ips_distintos=Count('ip', distinct=True)
    ).filter(ips_distintos__gte=3)
    
    for item in usuarios_multiplos_ips:
        suspeitas.append({
            'tipo': 'Múltiplos IPs',
            'usuario': item['usuario__usua_nome'],
            'detalhes': f"{item['ips_distintos']} IPs diferentes",
            'gravidade': 'media'
        })
    
    # 4. Alterações em massa
    alteracoes_massa = LogAcao.objects.filter(
        data_hora__gte=data_limite,
        tipo_acao__in=['PUT', 'PATCH', 'DELETE']
    ).values(
        'usuario__usua_nome',
        'modelo'
    ).annotate(
        total=Count('id')
    ).filter(total__gte=20)
    
    for item in alteracoes_massa:
        suspeitas.append({
            'tipo': 'Alterações em massa',
            'usuario': item['usuario__usua_nome'],
            'detalhes': f"{item['total']} alterações em {item['modelo']}",
            'gravidade': 'alta' if item['total'] >= 100 else 'media'
        })
    
    return suspeitas

def exportar_logs_csv(queryset, campos=None):
    """
    Exporta logs para formato CSV
    """
    import csv
    from io import StringIO
    
    if campos is None:
        campos = [
            'data_hora', 'usuario__usua_nome', 'tipo_acao', 
            'modelo', 'objeto_id', 'empresa', 'ip'
        ]
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    headers = []
    for campo in campos:
        if campo == 'usuario__usua_nome':
            headers.append('Usuario')
        elif campo == 'tipo_acao':
            headers.append('Acao')
        elif campo == 'data_hora':
            headers.append('Data/Hora')
        elif campo == 'objeto_id':
            headers.append('Objeto ID')
        else:
            headers.append(campo.replace('_', ' ').title())
    
    writer.writerow(headers)
    
    # Dados
    for log in queryset:
        row = []
        for campo in campos:
            if campo == 'usuario__usua_nome':
                valor = log.usuario.usua_nome if log.usuario else ''
            elif campo == 'data_hora':
                valor = log.data_hora.strftime('%d/%m/%Y %H:%M:%S')
            elif campo == 'tipo_acao':
                valor = log.get_tipo_acao_display()
            else:
                valor = getattr(log, campo, '')
            
            row.append(str(valor) if valor is not None else '')
        
        writer.writerow(row)
    
    return output.getvalue()

def limpar_logs_antigos(dias=365):
    """
    Remove logs mais antigos que o número especificado de dias
    """
    data_limite = timezone.now() - timedelta(days=dias)
    
    logs_antigos = LogAcao.objects.filter(data_hora__lt=data_limite)
    total = logs_antigos.count()
    
    if total > 0:
        logs_antigos.delete()
        return f"Removidos {total} logs anteriores a {data_limite.strftime('%d/%m/%Y')}"
    
    return "Nenhum log antigo encontrado para remoção"

def obter_estatisticas_rapidas(licenca=None):
    """
    Obtém estatísticas rápidas para dashboard
    """
    queryset = LogAcao.objects.all()
    
    if licenca:
        queryset = queryset.filter(licenca=licenca)
    
    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)
    semana_passada = hoje - timedelta(days=7)
    mes_passado = hoje - timedelta(days=30)
    
    return {
        'total_logs': queryset.count(),
        'logs_hoje': queryset.filter(data_hora__date=hoje).count(),
        'logs_ontem': queryset.filter(data_hora__date=ontem).count(),
        'logs_semana': queryset.filter(data_hora__date__gte=semana_passada).count(),
        'logs_mes': queryset.filter(data_hora__date__gte=mes_passado).count(),
        'usuarios_ativos_hoje': queryset.filter(
            data_hora__date=hoje
        ).values('usuario').distinct().count(),
        'acoes_criacao_hoje': queryset.filter(
            data_hora__date=hoje,
            tipo_acao='POST'
        ).count(),
        'acoes_exclusao_hoje': queryset.filter(
            data_hora__date=hoje,
            tipo_acao='DELETE'
        ).count(),
    }

def comparar_objetos_detalhado(modelo, objeto_id, data_inicio, data_fim):
    """
    Compara o estado de um objeto entre duas datas
    """
    logs = LogAcao.objects.filter(
        modelo=modelo,
        objeto_id=str(objeto_id),
        data_hora__range=[data_inicio, data_fim]
    ).order_by('data_hora')
    
    if not logs.exists():
        return None
    
    primeiro_log = logs.first()
    ultimo_log = logs.last()
    
    estado_inicial = primeiro_log.dados_antes or primeiro_log.dados_depois
    estado_final = ultimo_log.dados_depois or ultimo_log.dados_antes
    
    if not estado_inicial or not estado_final:
        return None
    
    diferencas = []
    
    # Comparar todos os campos
    todos_campos = set(estado_inicial.keys()) | set(estado_final.keys())
    
    for campo in todos_campos:
        valor_inicial = estado_inicial.get(campo)
        valor_final = estado_final.get(campo)
        
        if str(valor_inicial) != str(valor_final):
            diferencas.append({
                'campo': campo,
                'valor_inicial': valor_inicial,
                'valor_final': valor_final,
                'alterado': True
            })
        else:
            diferencas.append({
                'campo': campo,
                'valor_inicial': valor_inicial,
                'valor_final': valor_final,
                'alterado': False
            })
    
    return {
        'modelo': modelo,
        'objeto_id': objeto_id,
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim
        },
        'total_alteracoes': logs.count(),
        'campos_comparados': len(diferencas),
        'campos_alterados': len([d for d in diferencas if d['alterado']]),
        'diferencas': diferencas
    }