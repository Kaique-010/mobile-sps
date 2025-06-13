from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from auditoria.utils import (
    gerar_relatorio_atividades,
    detectar_atividades_suspeitas,
    obter_estatisticas_rapidas,
    exportar_logs_csv
)
from auditoria.models import LogAcao
import json
import os

class Command(BaseCommand):
    help = 'Gera relatórios de auditoria em diferentes formatos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            choices=['atividades', 'suspeitas', 'estatisticas', 'csv'],
            required=True,
            help='Tipo de relatório a gerar'
        )
        
        parser.add_argument(
            '--data-inicio',
            type=str,
            help='Data de início (formato: YYYY-MM-DD)'
        )
        
        parser.add_argument(
            '--data-fim',
            type=str,
            help='Data de fim (formato: YYYY-MM-DD)'
        )
        
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de dias para análise (padrão: 30)'
        )
        
        parser.add_argument(
            '--usuario-id',
            type=int,
            help='ID do usuário para filtrar'
        )
        
        parser.add_argument(
            '--licenca',
            type=str,
            help='Licença para filtrar'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Arquivo de saída (padrão: stdout)'
        )
        
        parser.add_argument(
            '--formato',
            choices=['json', 'texto'],
            default='texto',
            help='Formato de saída (padrão: texto)'
        )
    
    def handle(self, *args, **options):
        tipo = options['tipo']
        data_inicio = options['data_inicio']
        data_fim = options['data_fim']
        dias = options['dias']
        usuario_id = options['usuario_id']
        licenca = options['licenca']
        output_file = options['output']
        formato = options['formato']
        
        # Processar datas
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            except ValueError:
                self.stderr.write(
                    self.style.ERROR('Formato de data_inicio inválido. Use YYYY-MM-DD')
                )
                return
        
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                data_fim = data_fim.replace(hour=23, minute=59, second=59)
            except ValueError:
                self.stderr.write(
                    self.style.ERROR('Formato de data_fim inválido. Use YYYY-MM-DD')
                )
                return
        
        # Se não especificou datas, usar os últimos N dias
        if not data_inicio and not data_fim:
            data_fim = timezone.now()
            data_inicio = data_fim - timedelta(days=dias)
        
        # Buscar usuário se especificado
        usuario = None
        if usuario_id:
            try:
                from core.models import Usuario
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f'Usuário com ID {usuario_id} não encontrado')
                )
                return
        
        # Gerar relatório baseado no tipo
        if tipo == 'atividades':
            resultado = self.gerar_relatorio_atividades(
                data_inicio, data_fim, usuario, licenca
            )
        elif tipo == 'suspeitas':
            resultado = self.gerar_relatorio_suspeitas(dias)
        elif tipo == 'estatisticas':
            resultado = self.gerar_estatisticas(licenca)
        elif tipo == 'csv':
            resultado = self.gerar_csv(
                data_inicio, data_fim, usuario_id, licenca
            )
            formato = 'csv'  # Forçar formato CSV
        
        # Formatar saída
        if formato == 'json':
            output = json.dumps(resultado, indent=2, default=str, ensure_ascii=False)
        elif formato == 'csv':
            output = resultado  # Já está em formato CSV
        else:
            output = self.formatar_texto(resultado, tipo)
        
        # Escrever saída
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output)
                self.stdout.write(
                    self.style.SUCCESS(f'Relatório salvo em: {output_file}')
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'Erro ao salvar arquivo: {e}')
                )
        else:
            self.stdout.write(output)
    
    def gerar_relatorio_atividades(self, data_inicio, data_fim, usuario, licenca):
        return gerar_relatorio_atividades(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuario=usuario,
            empresa=licenca
        )
    
    def gerar_relatorio_suspeitas(self, dias):
        suspeitas = detectar_atividades_suspeitas(dias=dias)
        return {
            'periodo_analisado': f'{dias} dias',
            'total_suspeitas': len(suspeitas),
            'suspeitas': suspeitas
        }
    
    def gerar_estatisticas(self, licenca):
        return obter_estatisticas_rapidas(licenca=licenca)
    
    def gerar_csv(self, data_inicio, data_fim, usuario_id, licenca):
        queryset = LogAcao.objects.all()
        
        if data_inicio:
            queryset = queryset.filter(data_hora__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_hora__lte=data_fim)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        if licenca:
            queryset = queryset.filter(licenca=licenca)
        
        return exportar_logs_csv(queryset)
    
    def formatar_texto(self, dados, tipo):
        if tipo == 'atividades':
            return self.formatar_atividades(dados)
        elif tipo == 'suspeitas':
            return self.formatar_suspeitas(dados)
        elif tipo == 'estatisticas':
            return self.formatar_estatisticas(dados)
        
        return str(dados)
    
    def formatar_atividades(self, dados):
        output = []
        output.append('=== RELATÓRIO DE ATIVIDADES ===')
        output.append('')
        
        periodo = dados.get('periodo', {})
        if periodo.get('inicio'):
            output.append(f"Período: {periodo['inicio']} até {periodo['fim']}")
        
        output.append(f"Total de logs: {dados.get('total_logs', 0):,}")
        output.append('')
        
        # Por ação
        output.append('--- Atividades por Tipo de Ação ---')
        for item in dados.get('por_acao', []):
            output.append(f"{item['tipo_acao']}: {item['total']:,}")
        output.append('')
        
        # Por usuário
        output.append('--- Top 10 Usuários Mais Ativos ---')
        for item in dados.get('por_usuario', []):
            nome = item['usuario__usua_nome'] or 'Sistema'
            output.append(f"{nome}: {item['total']:,}")
        output.append('')
        
        # Por modelo
        output.append('--- Top 10 Modelos Mais Alterados ---')
        for item in dados.get('por_modelo', []):
            output.append(f"{item['modelo']}: {item['total']:,}")
        output.append('')
        
        # Por hora
        output.append('--- Atividade por Hora do Dia ---')
        for item in dados.get('por_hora', []):
            hora = int(item['hora'])
            output.append(f"{hora:02d}:00 - {item['total']:,}")
        
        return '\n'.join(output)
    
    def formatar_suspeitas(self, dados):
        output = []
        output.append('=== RELATÓRIO DE ATIVIDADES SUSPEITAS ===')
        output.append('')
        output.append(f"Período analisado: {dados['periodo_analisado']}")
        output.append(f"Total de suspeitas: {dados['total_suspeitas']}")
        output.append('')
        
        if dados['total_suspeitas'] == 0:
            output.append('Nenhuma atividade suspeita detectada.')
        else:
            for suspeita in dados['suspeitas']:
                gravidade = suspeita['gravidade'].upper()
                output.append(f"[{gravidade}] {suspeita['tipo']}")
                output.append(f"  Usuário: {suspeita['usuario']}")
                output.append(f"  Detalhes: {suspeita['detalhes']}")
                output.append('')
        
        return '\n'.join(output)
    
    def formatar_estatisticas(self, dados):
        output = []
        output.append('=== ESTATÍSTICAS RÁPIDAS ===')
        output.append('')
        output.append(f"Total de logs: {dados.get('total_logs', 0):,}")
        output.append(f"Logs hoje: {dados.get('logs_hoje', 0):,}")
        output.append(f"Logs ontem: {dados.get('logs_ontem', 0):,}")
        output.append(f"Logs última semana: {dados.get('logs_semana', 0):,}")
        output.append(f"Logs último mês: {dados.get('logs_mes', 0):,}")
        output.append('')
        output.append(f"Usuários ativos hoje: {dados.get('usuarios_ativos_hoje', 0)}")
        output.append(f"Criações hoje: {dados.get('acoes_criacao_hoje', 0):,}")
        output.append(f"Exclusões hoje: {dados.get('acoes_exclusao_hoje', 0):,}")
        
        return '\n'.join(output)