# Sistema de Auditoria Avançado

Este sistema de auditoria captura e registra todas as alterações realizadas na aplicação, tanto através da API quanto diretamente no banco de dados.

## Funcionalidades

### 1. Captura de Alterações Detalhadas

- **Dados Antes**: Estado anterior do objeto antes da alteração
- **Dados Depois**: Estado posterior do objeto após a alteração
- **Campos Alterados**: Lista específica dos campos que foram modificados
- **Comparação Automática**: Identifica automaticamente quais campos foram alterados

### 2. Tipos de Ações Rastreadas

- **Criação (POST)**: Registra quando novos objetos são criados
- **Atualização (PUT/PATCH)**: Registra alterações em objetos existentes
- **Exclusão (DELETE)**: Registra quando objetos são removidos
- **Consulta (GET)**: Registra acessos de leitura

### 3. Dupla Captura

#### Via Middleware (API)
- Captura ações realizadas através da API REST
- Inclui informações da requisição HTTP
- Rastreia IP, navegador, e dados da requisição

#### Via Signals (Banco de Dados)
- Captura alterações diretas no banco de dados
- Funciona mesmo para operações que não passam pela API
- Útil para scripts, admin do Django, etc.

## Estrutura dos Dados

### Campos do LogAcao

```python
class LogAcao(models.Model):
    # Campos básicos
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo_acao = models.CharField(max_length=10)  # GET, POST, PUT, PATCH, DELETE
    url = models.TextField()
    ip = models.GenericIPAddressField(null=True)
    navegador = models.CharField(max_length=255)
    
    # Dados da alteração
    dados = JSONField(null=True)  # Dados da requisição original
    dados_antes = JSONField(null=True)  # Estado anterior
    dados_depois = JSONField(null=True)  # Estado posterior
    campos_alterados = JSONField(null=True)  # Campos modificados
    
    # Identificação do objeto
    objeto_id = models.CharField(max_length=100, null=True)
    modelo = models.CharField(max_length=100, null=True)
    
    # Contexto
    empresa = models.CharField(max_length=100, null=True)
    licenca = models.CharField(max_length=100, null=True)
```

### Formato dos Campos Alterados

```json
{
  "nome": {
    "antes": "João Silva",
    "depois": "João Santos"
  },
  "email": {
    "antes": "joao@email.com",
    "depois": "joao.santos@email.com"
  },
  "status": {
    "antes": "ativo",
    "depois": "inativo"
  }
}
```

## Exemplos de Uso

### 1. Consultar Alterações de um Objeto Específico

```python
# Buscar todos os logs de um produto específico
logs = LogAcao.objects.filter(
    modelo='Produto',
    objeto_id='123'
).order_by('-data_hora')

for log in logs:
    print(f"{log.data_hora}: {log.tipo_acao} por {log.usuario}")
    if log.tem_alteracoes:
        print(f"Alterações: {log.resumo_alteracoes}")
```

### 2. Relatório de Alterações por Usuário

```python
# Alterações realizadas por um usuário específico
logs = LogAcao.objects.filter(
    usuario__usua_nome='admin',
    tipo_acao__in=['POST', 'PUT', 'PATCH', 'DELETE']
).order_by('-data_hora')

for log in logs:
    print(f"{log.get_objeto_info()}: {log.acao_formatada}")
```

### 3. Auditoria de Segurança

```python
# Buscar todas as exclusões realizadas
exclusoes = LogAcao.objects.filter(
    tipo_acao='DELETE'
).select_related('usuario')

for exclusao in exclusoes:
    print(f"EXCLUSÃO: {exclusao.modelo} ID {exclusao.objeto_id}")
    print(f"Por: {exclusao.usuario} em {exclusao.data_hora}")
    print(f"Dados excluídos: {exclusao.dados_antes}")
```

### 4. Rastreamento de Alterações Específicas

```python
# Buscar alterações em campos específicos
logs_com_alteracoes = LogAcao.objects.filter(
    campos_alterados__isnull=False
)

for log in logs_com_alteracoes:
    if log.campos_alterados:
        for campo, alteracao in log.campos_alterados.items():
            if campo == 'preco':  # Monitorar alterações de preço
                print(f"Preço alterado em {log.modelo} ID {log.objeto_id}")
                print(f"De {alteracao['antes']} para {alteracao['depois']}")
                print(f"Por {log.usuario} em {log.data_hora}")
```

## API Endpoints

### Listar Logs (Usuários Comuns)
```
GET /api/auditoria/logs/
```

### Listar Todos os Logs (Administradores)
```
GET /api/auditoria/logs/admin/
```

### Filtros Disponíveis

- `data_inicio`: Data de início (YYYY-MM-DD)
- `data_fim`: Data de fim (YYYY-MM-DD)
- `metodo`: Tipo de ação (GET, POST, PUT, PATCH, DELETE)
- `usuario`: Nome do usuário
- `empresa`: Nome da empresa
- `licenca`: Slug da licença
- `modelo`: Nome do modelo
- `objeto_id`: ID do objeto

### Exemplo de Requisição
```
GET /api/auditoria/logs/?data_inicio=2024-01-01&metodo=DELETE&usuario=admin
```

## Configuração

### 1. Adicionar aos Middlewares

```python
# settings.py
MIDDLEWARE = [
    # ... outros middlewares
    'auditoria.middleware.AuditoriaMiddleware',
    'auditoria.signals.AuditoriaSignalMiddleware',  # Para signals
    # ... outros middlewares
]
```

### 2. Executar Migrações

```bash
python manage.py makemigrations auditoria
python manage.py migrate
```

### 3. Configurar Permissões

Apenas usuários com perfis específicos podem acessar logs completos:
- `admin`
- `supervisor` 
- `root`

## Considerações de Performance

### Índices Criados
- `(empresa, licenca, data_hora)`
- `(usuario, data_hora)`
- `(modelo, objeto_id)`
- `(tipo_acao, data_hora)`

### Limpeza de Logs Antigos

Recomenda-se implementar uma rotina de limpeza para logs muito antigos:

```python
# Exemplo: manter apenas logs dos últimos 2 anos
from datetime import datetime, timedelta
from auditoria.models import LogAcao

data_limite = datetime.now() - timedelta(days=730)
LogAcao.objects.filter(data_hora__lt=data_limite).delete()
```

## Segurança

### Dados Sensíveis
O sistema automaticamente remove campos sensíveis dos logs:
- `password`
- `senha`
- `token`
- `api_key`
- `secret`

### Controle de Acesso
- Usuários comuns só veem logs da própria licença
- Administradores podem ver todos os logs
- Logs são somente leitura via API

## Comandos de Gerenciamento

### Limpeza de Logs Antigos

```bash
# Remover logs mais antigos que 365 dias
python manage.py limpar_logs_auditoria --dias=365

# Visualizar quantos logs seriam removidos (dry run)
python manage.py limpar_logs_auditoria --dias=365 --dry-run

# Remover logs de uma licença específica
python manage.py limpar_logs_auditoria --dias=180 --licenca=empresa123

# Confirmar automaticamente sem prompt
python manage.py limpar_logs_auditoria --dias=365 --confirmar
```

### Geração de Relatórios

```bash
# Relatório de atividades dos últimos 7 dias
python manage.py relatorio_auditoria --tipo=atividades --dias=7

# Relatório de atividades suspeitas
python manage.py relatorio_auditoria --tipo=suspeitas --dias=30

# Estatísticas rápidas
python manage.py relatorio_auditoria --tipo=estatisticas

# Exportar para CSV
python manage.py relatorio_auditoria --tipo=csv --data-inicio=2024-01-01 --data-fim=2024-01-31 --output=logs.csv

# Relatório em JSON
python manage.py relatorio_auditoria --tipo=atividades --formato=json --output=relatorio.json

# Filtrar por usuário
python manage.py relatorio_auditoria --tipo=atividades --usuario-id=123
```

## Tarefas Agendadas

O sistema inclui tarefas pré-configuradas para automação:

### Com django-crontab

Adicione ao `settings.py`:

```python
CRONJOBS = [
    ('0 2 * * *', 'auditoria.cron_jobs.limpar_logs_antigos'),  # Diário às 02:00
    ('0 8 * * *', 'auditoria.cron_jobs.gerar_relatorio_diario'),  # Diário às 08:00
    ('0 */4 * * *', 'auditoria.cron_jobs.detectar_atividades_suspeitas'),  # A cada 4h
    ('0 9 * * 0', 'auditoria.cron_jobs.gerar_relatorio_semanal'),  # Domingo às 09:00
    ('0 3 1 * *', 'auditoria.cron_jobs.backup_logs_importantes'),  # 1º do mês às 03:00
]
```

### Com Celery Beat

Adicione ao `settings.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'limpar-logs-antigos': {
        'task': 'auditoria.cron_jobs.limpar_logs_antigos',
        'schedule': crontab(hour=2, minute=0),
    },
    'detectar-suspeitas': {
        'task': 'auditoria.cron_jobs.detectar_atividades_suspeitas',
        'schedule': crontab(minute=0, hour='*/4'),
    },
    # ... outras tarefas
}
```

## Notificações de Segurança

Para receber alertas sobre atividades suspeitas, configure:

```python
# settings.py
AUDITORIA_EMAIL_ALERTAS = [
    'admin@empresa.com',
    'seguranca@empresa.com',
]
```

## Funções Utilitárias

O módulo `auditoria.utils` fornece funções para análise avançada:

```python
from auditoria.utils import (
    gerar_relatorio_atividades,
    buscar_alteracoes_objeto,
    detectar_atividades_suspeitas,
    obter_estatisticas_rapidas,
    comparar_objetos_detalhado
)

# Gerar relatório personalizado
relatorio = gerar_relatorio_atividades(
    data_inicio=datetime(2024, 1, 1),
    data_fim=datetime(2024, 1, 31),
    usuario=usuario_obj,
    empresa='empresa123'
)

# Buscar histórico de um objeto
historico = buscar_alteracoes_objeto('Usuario', 123)

# Detectar atividades suspeitas
suspeitas = detectar_atividades_suspeitas(dias=7)

# Comparar estado de objeto entre datas
comparacao = comparar_objetos_detalhado(
    'Usuario', 123,
    datetime(2024, 1, 1),
    datetime(2024, 1, 31)
)
```

## Troubleshooting

### Problemas Comuns

1. **Logs não estão sendo criados**
   - Verifique se o middleware está configurado
   - Confirme se as migrações foram aplicadas
   - Verifique as permissões do usuário
   - Confirme que os signals estão sendo importados

2. **Performance lenta**
   - Execute as migrações para criar os índices
   - Use o comando de limpeza regularmente
   - Monitore o tamanho da tabela de logs
   - Configure tarefas agendadas para limpeza automática

3. **Dados sensíveis nos logs**
   - Verifique a lista `CAMPOS_SENSIVEIS` no serializer
   - Adicione novos campos sensíveis conforme necessário
   - Revise os dados capturados nos signals

4. **Signals não funcionando**
   - Confirme que `auditoria` está em `INSTALLED_APPS`
   - Verifique se o método `ready()` está sendo chamado
   - Confirme que os signals estão sendo importados
   - Verifique se o middleware de signals está ativo

5. **Muitos logs sendo gerados**
   - Configure filtros no middleware para excluir endpoints desnecessários
   - Use o comando de limpeza com frequência maior
   - Considere arquivar logs antigos antes de removê-los

6. **Relatórios lentos**
   - Use filtros de data para limitar o escopo
   - Execute limpeza de logs antigos
   - Considere usar índices adicionais se necessário

### Logs de Debug

Para debug, configure logging específico:

```python
# settings.py
LOGGING = {
    'loggers': {
        'auditoria': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'auditoria.cron': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

CREATE TABLE auditoria_logacao (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(usua_codi) ON DELETE SET NULL,
    data_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tipo_acao VARCHAR(10) NOT NULL,
    url TEXT NOT NULL,
    ip INET,
    navegador VARCHAR(255) NOT NULL,
    dados JSONB,
    dados_antes JSONB,
    dados_depois JSONB,
    campos_alterados JSONB,
    objeto_id VARCHAR(100),
    modelo VARCHAR(100),
    empresa VARCHAR(100),
    licenca VARCHAR(100)
);

CREATE INDEX idx_auditoria_empresa_licenca_datahora ON auditoria_logacao (empresa, licenca, data_hora);
CREATE INDEX idx_auditoria_usuario_datahora ON auditoria_logacao (usuario_id, data_hora);
CREATE INDEX idx_auditoria_modelo_objeto ON auditoria_logacao (modelo, objeto_id);
CREATE INDEX idx_auditoria_tipoacao_datahora ON auditoria_logacao (tipo_acao, data_hora);
