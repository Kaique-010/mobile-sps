# App Contas a Receber

## Visão Geral

O app **contas_a_receber** é responsável pela gestão completa do contas a receber da empresa, controlando títulos, recebimentos, cobrança e toda a movimentação financeira relacionada aos valores a receber de clientes.

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

contas_a_receber

GET
/api/{slug}/contas_a_receber/titulos-receber/

POST
/api/{slug}/contas_a_receber/titulos-receber/

GET
/api/{slug}/contas_a_receber/titulos-receber/{id}/

PUT
/api/{slug}/contas_a_receber/titulos-receber/{id}/

PATCH
/api/{slug}/contas_a_receber/titulos-receber/{id}/

DELETE
/api/{slug}/contas_a_receber/titulos-receber/{id}/

POST
/api/{slug}/contas_a_receber/titulos-receber/{id}/baixar_titulo/

DELETE
/api/{slug}/contas_a_receber/titulos-receber/{id}/excluir_baixa/

GET
/api/{slug}/contas_a_receber/titulos-receber/{id}/get_titulo_for_historico/

GET
/api/{slug}/contas_a_receber/titulos-receber/{id}/historico_baixas/

GET
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/

PUT
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/

PATCH
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/

DELETE
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/

POST
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/baixar/

DELETE
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/excluir_baixa/

GET
/api/{slug}/contas_a_receber/titulos-receber/{titu_empr}/{titu_fili}/{titu_clie}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/historico_baixas/
