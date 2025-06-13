# App Contas a Receber

## Visão Geral

O app **contas_a_receber** é responsável pela gestão completa do contas a receber da empresa, controlando títulos, recebimentos, cobrança e toda a movimentação financeira relacionada aos valores a receber de clientes. Este módulo oferece funcionalidades avançadas para controle de vencimentos, descontos, juros, multas e diferentes formas de recebimento.

## Funcionalidades Principais

- **Gestão de Títulos a Receber**: Controle completo de duplicatas, cheques, promissórias e outros títulos
- **Controle de Recebimentos**: Registro e gestão de baixas de títulos
- **Cobrança Eletrônica**: Integração com bancos para cobrança automática
- **Gestão de Descontos e Juros**: Controle de descontos por pontualidade e juros por atraso
- **Múltiplas Formas de Recebimento**: Suporte a diversas modalidades de pagamento
- **Relatórios Financeiros**: Análises e relatórios de recebimentos
- **Integração Bancária**: Controle de boletos, PIX e outras modalidades
- **Auditoria Completa**: Rastreabilidade de todas as operações

## Modelos

### Titulosreceber

Modelo principal que representa um título a receber.

```python
class Titulosreceber(models.Model):
    titu_empr = models.IntegerField()                    # Código da empresa
    titu_fili = models.IntegerField()                    # Código da filial
    titu_clie = models.IntegerField()                    # Código do cliente
    titu_titu = models.CharField(max_length=13, primary_key=True)  # Número do título
    titu_seri = models.CharField(max_length=5)           # Série do título
    titu_parc = models.CharField(max_length=3)           # Parcela
    titu_emis = models.DateField()                       # Data de emissão
    titu_venc = models.DateField()                       # Data de vencimento
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2)  # Valor do título
    titu_hist = models.TextField()                       # Histórico
    titu_aber = models.CharField(max_length=1, default='A')  # Status (A=Aberto, B=Baixado)
    
    # Campos de desconto
    titu_desc_ao_dia = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto ao dia
    titu_desc_pont = models.DecimalField(max_digits=15, decimal_places=2)    # Desconto pontualidade
    
    # Campos de juros e multa
    titu_mult = models.DecimalField(max_digits=15, decimal_places=2)  # Multa
    titu_juro = models.DecimalField(max_digits=15, decimal_places=3)  # Juros
    
    # Forma de recebimento
    titu_form_reci = models.CharField(max_length=2, choices=FORMA_RECEBIMENTO)
    
    # Campos de cobrança
    titu_noss_nume = models.CharField(max_length=30)     # Nosso número
    titu_cobr_banc = models.IntegerField()               # Banco de cobrança
    
    # Campos PIX
    titu_url_pix = models.TextField()                    # URL do PIX
    titu_txid_pix = models.CharField(max_length=144)     # TXID do PIX
    titu_emv_pix = models.CharField(max_length=255)      # EMV do PIX
```

#### Formas de Recebimento:
- **00**: DUPLICATA
- **01**: CHEQUE
- **02**: PROMISSÓRIA
- **03**: RECIBO
- **50**: CHEQUE PRÉ
- **51**: CARTÃO DE CRÉDITO
- **52**: CARTÃO DE DÉBITO
- **53**: BOLETO BANCÁRIO
- **54**: DINHEIRO
- **55**: DEPÓSITO EM CONTA
- **56**: VENDA À VISTA
- **60**: PIX

### Baretitulos

Modelo que representa as baixas/recebimentos dos títulos.

```python
class Baretitulos(models.Model):
    bare_sequ = models.IntegerField(primary_key=True)    # Sequencial da baixa
    bare_titu = models.ForeignKey('Titulosreceber')      # Título relacionado
    bare_dpag = models.DateField()                       # Data do pagamento
    bare_apag = models.DecimalField(max_digits=15, decimal_places=2)  # Valor a pagar
    bare_vmul = models.DecimalField(max_digits=15, decimal_places=2)  # Valor da multa
    bare_vjur = models.DecimalField(max_digits=15, decimal_places=2)  # Valor dos juros
    bare_vdes = models.DecimalField(max_digits=15, decimal_places=2)  # Valor do desconto
    bare_pago = models.DecimalField(max_digits=15, decimal_places=2)  # Valor pago
    bare_hist = models.TextField()                       # Histórico da baixa
    bare_banc = models.IntegerField()                    # Banco
    bare_cheq = models.IntegerField()                    # Número do cheque
    bare_usua_baix = models.IntegerField()               # Usuário que fez a baixa
    bare_data_baix = models.DateField()                  # Data da baixa
```

## Exemplos de Uso

### Criar Título a Receber

```python
from contas_a_receber.models import Titulosreceber
from datetime import date, timedelta

# Criar novo título
titulo = Titulosreceber.objects.create(
    titu_empr=1,
    titu_fili=1,
    titu_clie=123,
    titu_titu='2024000001',
    titu_seri='001',
    titu_parc='001',
    titu_emis=date.today(),
    titu_venc=date.today() + timedelta(days=30),
    titu_valo=1500.00,
    titu_hist='Venda de produtos',
    titu_form_reci='53',  # Boleto bancário
    titu_desc_pont=50.00,  # Desconto de R$ 50 para pagamento pontual
    titu_juro=2.5,  # Juros de 2,5% ao mês
    titu_mult=10.0  # Multa de 10%
)
```

### Criar Título Parcelado

```python
def criar_titulo_parcelado(cliente_id, valor_total, num_parcelas, vencimento_primeira):
    titulos = []
    valor_parcela = valor_total / num_parcelas
    
    for i in range(num_parcelas):
        vencimento = vencimento_primeira + timedelta(days=30 * i)
        
        titulo = Titulosreceber.objects.create(
            titu_empr=1,
            titu_fili=1,
            titu_clie=cliente_id,
            titu_titu=f'2024{str(i+1).zfill(6)}',
            titu_seri='001',
            titu_parc=str(i+1).zfill(3),
            titu_emis=date.today(),
            titu_venc=vencimento,
            titu_valo=valor_parcela,
            titu_hist=f'Parcela {i+1}/{num_parcelas}',
            titu_form_reci='53'
        )
        titulos.append(titulo)
    
    return titulos
```

### Baixar Título (Recebimento)

```python
from contas_a_receber.models import Baretitulos
from decimal import Decimal

def baixar_titulo(titulo_numero, valor_pago, data_pagamento, forma_pagamento='54'):
    titulo = Titulosreceber.objects.get(titu_titu=titulo_numero)
    
    # Calcular juros e multa se houver atraso
    dias_atraso = (data_pagamento - titulo.titu_venc).days
    valor_juros = Decimal('0.00')
    valor_multa = Decimal('0.00')
    valor_desconto = Decimal('0.00')
    
    if dias_atraso > 0:
        # Aplicar juros e multa
        if titulo.titu_juro:
            valor_juros = titulo.titu_valo * (titulo.titu_juro / 100) * (dias_atraso / 30)
        if titulo.titu_mult:
            valor_multa = titulo.titu_valo * (titulo.titu_mult / 100)
    elif dias_atraso <= 0 and titulo.titu_desc_pont:
        # Aplicar desconto por pontualidade
        valor_desconto = titulo.titu_desc_pont
    
    # Criar baixa
    baixa = Baretitulos.objects.create(
        bare_titu=titulo,
        bare_dpag=data_pagamento,
        bare_apag=titulo.titu_valo,
        bare_vmul=valor_multa,
        bare_vjur=valor_juros,
        bare_vdes=valor_desconto,
        bare_pago=valor_pago,
        bare_hist=f'Recebimento via {forma_pagamento}',
        bare_usua_baix=1,
        bare_data_baix=date.today()
    )
    
    # Marcar título como baixado
    titulo.titu_aber = 'B'
    titulo.save()
    
    return baixa
```

### Consultas e Relatórios

```python
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta

# Títulos em aberto
titulos_abertos = Titulosreceber.objects.filter(
    titu_aber='A'
).order_by('titu_venc')

# Títulos vencidos
titulos_vencidos = Titulosreceber.objects.filter(
    titu_aber='A',
    titu_venc__lt=date.today()
)

# Recebimentos do mês
recebimentos_mes = Baretitulos.objects.filter(
    bare_dpag__month=datetime.now().month,
    bare_dpag__year=datetime.now().year
).aggregate(
    total_recebido=Sum('bare_pago'),
    quantidade=Count('bare_sequ')
)

# Títulos por cliente
def relatorio_cliente(cliente_id):
    return {
        'abertos': Titulosreceber.objects.filter(
            titu_clie=cliente_id,
            titu_aber='A'
        ).aggregate(total=Sum('titu_valo'))['total'] or 0,
        
        'vencidos': Titulosreceber.objects.filter(
            titu_clie=cliente_id,
            titu_aber='A',
            titu_venc__lt=date.today()
        ).count(),
        
        'recebido_mes': Baretitulos.objects.filter(
            bare_titu__titu_clie=cliente_id,
            bare_dpag__month=datetime.now().month
        ).aggregate(total=Sum('bare_pago'))['total'] or 0
    }
```

### Funções de Cobrança

```python
# Gerar relatório de cobrança
def relatorio_cobranca(dias_vencimento=5):
    data_limite = date.today() + timedelta(days=dias_vencimento)
    
    return Titulosreceber.objects.filter(
        titu_aber='A',
        titu_venc__lte=data_limite
    ).select_related('cliente').order_by('titu_venc')

# Calcular valor com juros e multa
def calcular_valor_atualizado(titulo, data_calculo=None):
    if not data_calculo:
        data_calculo = date.today()
    
    dias_atraso = (data_calculo - titulo.titu_venc).days
    valor_final = titulo.titu_valo
    
    if dias_atraso > 0:
        # Aplicar multa
        if titulo.titu_mult:
            valor_final += titulo.titu_valo * (titulo.titu_mult / 100)
        
        # Aplicar juros
        if titulo.titu_juro:
            valor_final += titulo.titu_valo * (titulo.titu_juro / 100) * (dias_atraso / 30)
    
    return valor_final
```

## Endpoints da API

### Listar Títulos
```http
GET /api/titulos-receber/
GET /api/titulos-receber/?titu_aber=A
GET /api/titulos-receber/?titu_clie=123
GET /api/titulos-receber/?titu_venc__lte=2024-01-31
```

### Criar Título
```http
POST /api/titulos-receber/
Content-Type: application/json

{
    "titu_empr": 1,
    "titu_fili": 1,
    "titu_clie": 123,
    "titu_titu": "2024000001",
    "titu_seri": "001",
    "titu_parc": "001",
    "titu_emis": "2024-01-15",
    "titu_venc": "2024-02-15",
    "titu_valo": 1500.00,
    "titu_hist": "Venda de produtos",
    "titu_form_reci": "53"
}
```

### Baixar Título
```http
POST /api/titulos-receber/{numero}/baixar/
Content-Type: application/json

{
    "bare_dpag": "2024-02-10",
    "bare_pago": 1450.00,
    "bare_vdes": 50.00,
    "bare_hist": "Recebimento com desconto pontualidade"
}
```

### Relatórios
```http
# Títulos vencidos
GET /api/titulos-receber/vencidos/

# Recebimentos por período
GET /api/recebimentos/?data_inicio=2024-01-01&data_fim=2024-01-31

# Posição do cliente
GET /api/titulos-receber/posicao-cliente/{cliente_id}/

# Relatório de cobrança
GET /api/titulos-receber/cobranca/?dias=5
```

### Filtros Avançados
```http
# Títulos por forma de recebimento
GET /api/titulos-receber/?titu_form_reci=53

# Títulos com valor acima de um limite
GET /api/titulos-receber/?titu_valo__gte=1000.00

# Títulos por período de vencimento
GET /api/titulos-receber/?titu_venc__range=2024-01-01,2024-01-31

# Títulos com cobrança bancária
GET /api/titulos-receber/?titu_cobr_banc__isnull=false
```

## Considerações Técnicas

### Banco de Dados
- **Tabelas**: `titulosreceber`, `baretitulos`
- **Chave Primária**: `titu_titu` (número do título)
- **Índices Recomendados**:
  - `(titu_empr, titu_fili, titu_clie, titu_titu, titu_seri, titu_parc)` - Unique constraint
  - `titu_venc` - Para consultas por vencimento
  - `titu_clie` - Para consultas por cliente
  - `titu_aber` - Para filtrar títulos abertos/baixados
  - `titu_form_reci` - Para relatórios por forma de recebimento

### Validações
- Valor do título deve ser maior que zero
- Data de vencimento não pode ser anterior à emissão
- Cliente deve existir no cadastro
- Número do título deve ser único por empresa/filial
- Validação de percentuais de juros e multas
- Controle de status do título (aberto/baixado)

### Triggers e Procedures
- Cálculo automático de juros e multas
- Atualização de status dos títulos
- Controle de numeração sequencial
- Logs de auditoria para rastreabilidade
- Validações de integridade referencial
- Procedures para relatórios otimizados

### Performance
- Índices otimizados para consultas frequentes
- Particionamento por data para tabelas grandes
- Cache para cálculos de posição de clientes
- Agregações pré-calculadas para dashboards

## Integração com Outros Apps

### Entidades
- Validação de clientes
- Dados para cobrança e comunicação
- Histórico de relacionamento comercial

### Pedidos
- Geração automática de títulos por vendas
- Vinculação de títulos com pedidos
- Controle de faturamento

### CaixaDiario
- Registro de recebimentos no caixa
- Conciliação de valores
- Controle de formas de pagamento

### Auditoria
- Log de todas as operações
- Rastreabilidade de alterações
- Controle de usuários e permissões

### Bancos/Cobrança
- Geração de arquivos de remessa
- Processamento de arquivos de retorno
- Controle de boletos e PIX

## Troubleshooting

### Problemas Comuns

1. **Erro de Título Duplicado**
   ```python
   # Verificar se título já existe
   titulo_existe = Titulosreceber.objects.filter(
       titu_empr=1,
       titu_fili=1,
       titu_titu='2024000001'
   ).exists()
   ```

2. **Problemas de Cálculo de Juros**
   ```python
   # Verificar configuração de juros
   def verificar_calculo_juros(titulo):
       if titulo.titu_juro_perc:
           # Juros em percentual
           return titulo.titu_valo * (titulo.titu_juro / 100)
       else:
           # Juros em valor fixo
           return titulo.titu_juro
   ```

3. **Inconsistências em Baixas**
   ```python
   # Verificar títulos com baixas inconsistentes
   titulos_inconsistentes = Titulosreceber.objects.filter(
       titu_aber='A'
   ).exclude(
       baretitulos__isnull=True
   )
   ```

### Logs de Debug
```python
import logging
logger = logging.getLogger('contas_receber')

# Log de título criado
logger.info(f'Título criado: {titulo.titu_titu} - Cliente: {titulo.titu_clie} - Valor: {titulo.titu_valo}')

# Log de recebimento
logger.info(f'Recebimento registrado: Título {baixa.bare_titu.titu_titu} - Valor: {baixa.bare_pago}')

# Log de erro
logger.error(f'Erro ao processar título: {str(e)}')
```

### Comandos de Manutenção
```bash
# Verificar integridade dos dados
python manage.py shell -c "from contas_a_receber.models import Titulosreceber; print(Titulosreceber.objects.count())"

# Recalcular juros e multas
python manage.py recalcular_juros_multas

# Processar arquivo de retorno bancário
python manage.py processar_retorno_bancario arquivo.ret

# Gerar relatório de inadimplência
python manage.py relatorio_inadimplencia

# Backup de títulos
python manage.py dumpdata contas_a_receber > backup_contas_receber.json
```

### Monitoramento
```python
# Alertas de títulos vencidos
def verificar_titulos_vencidos():
    vencidos = Titulosreceber.objects.filter(
        titu_aber='A',
        titu_venc__lt=date.today()
    ).count()
    
    if vencidos > 0:
        logger.warning(f'{vencidos} títulos vencidos encontrados')
    
    return vencidos

# Monitorar performance de recebimentos
def performance_recebimentos():
    hoje = date.today()
    mes_atual = Baretitulos.objects.filter(
        bare_dpag__month=hoje.month,
        bare_dpag__year=hoje.year
    ).aggregate(total=Sum('bare_pago'))['total'] or 0
    
    return mes_atual
```

## Conclusão

O app **contas_a_receber** é fundamental para a gestão financeira da empresa, oferecendo controle completo sobre títulos a receber, recebimentos, cobrança e análises financeiras. Sua integração com outros módulos garante a consistência dos dados e permite uma gestão eficiente do fluxo de caixa e relacionamento com clientes.