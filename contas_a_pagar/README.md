# App Contas a Pagar

Este app gerencia o sistema de contas a pagar, controlando títulos, fornecedores, vencimentos e pagamentos da empresa.

## Funcionalidades

### 1. Gestão de Títulos a Pagar

### 2. Controle de Pagamentos

### 3. Gestão Financeira

```python
class Titulospagar(models.Model):
    # Identificação
    titu_empr = models.IntegerField()  # Empresa
    titu_fili = models.IntegerField()  # Filial
    titu_forn = models.IntegerField()  # Fornecedor
    titu_titu = models.CharField(max_length=13, primary_key=True)  # Número do título
    titu_seri = models.CharField(max_length=5)  # Série
    titu_parc = models.CharField(max_length=4)  # Parcela

    # Datas e Valores
    titu_emis = models.DateField()  # Data de emissão
    titu_venc = models.DateField()  # Data de vencimento
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2)  # Valor

    # Classificação Contábil
    titu_cont = models.IntegerField()  # Conta contábil
    titu_cecu = models.IntegerField()  # Centro de custo
    titu_even = models.IntegerField()  # Evento contábil

    # Controles
    titu_prov = models.BooleanField()  # Provisão
    titu_hist = models.TextField()  # Histórico
    titu_aber = models.CharField(max_length=1, default='A')  # Status (A/B/C)
    titu_lote = models.CharField(max_length=10)  # Lote
    titu_ctrl = models.IntegerField()  # Controle

    # Descontos
    titu_desc_ao_dia = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto à vista
    titu_desc_ao_dia_perc = models.BooleanField()  # Desconto em percentual
    titu_desc_pont = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto pontualidade

    # Encargos
    titu_mult = models.DecimalField(max_digits=15, decimal_places=2)  # Multa
    titu_mult_perc = models.BooleanField()  # Multa em percentual
    titu_juro = models.DecimalField(max_digits=17, decimal_places=4)  # Juros
    titu_juro_perc = models.BooleanField()  # Juros em percentual
    titu_juro_mes = models.DecimalField(max_digits=17, decimal_places=4)  # Juros mensais

    # Pagamento Eletrônico
    titu_pag_for = models.BooleanField()  # Pagamento fornecedor
    titu_tipo_pag_for = models.IntegerField()  # Tipo pagamento
    titu_banc_pag_for = models.CharField(max_length=3)  # Banco
    titu_agen_pag_for = models.CharField(max_length=11)  # Agência
    titu_cont_pag_for = models.CharField(max_length=11)  # Conta

    # DDA e Aprovação
    titu_apro_dda = models.BooleanField()  # Aprovação DDA
    titu_nume_apro = models.IntegerField()  # Número aprovação
    titu_nume_dda = models.IntegerField()  # Número DDA

    # Auditoria
    titu_audi = models.BooleanField()  # Auditado
    titu_audi_data = models.DateField()  # Data auditoria
    titu_audi_por = models.IntegerField()  # Auditado por
    _log_data = models.DateField()  # Log data
    _log_time = models.TimeField()  # Log hora
```

### Modelo Bapatitulos (Baixas/Pagamentos)

```python
class Bapatitulos(models.Model):
    # Identificação
    bapa_ctrl = models.IntegerField()  # Controle da baixa
    bapa_empr = models.IntegerField()  # Empresa
    bapa_fili = models.IntegerField()  # Filial
    bapa_forn = models.IntegerField()  # Fornecedor
    bapa_titu = models.ForeignKey('Titulospagar')  # Título
    bapa_seri = models.CharField(max_length=5)  # Série
    bapa_parc = models.CharField(max_length=4)  # Parcela

    # Dados do Pagamento
    bapa_dpag = models.DateField()  # Data do pagamento
    bapa_apag = models.DecimalField(max_digits=15, decimal_places=2)  # Valor a pagar
    bapa_pago = models.DecimalField(max_digits=15, decimal_places=2)  # Valor pago
    bapa_valo_pago = models.DecimalField(max_digits=15, decimal_places=2)  # Total pago

    # Encargos e Descontos
    bapa_vmul = models.DecimalField(max_digits=15, decimal_places=2)  # Valor multa
    bapa_vjur = models.DecimalField(max_digits=15, decimal_places=2)  # Valor juros
    bapa_vdes = models.DecimalField(max_digits=15, decimal_places=2)  # Valor desconto
    bapa_pjur = models.DecimalField(max_digits=7, decimal_places=4)  # % Juros
    bapa_pmul = models.DecimalField(max_digits=6, decimal_places=2)  # % Multa
    bapa_pdes = models.DecimalField(max_digits=6, decimal_places=2)  # % Desconto

    # Forma de Pagamento
    bapa_topa = models.CharField(max_length=1)  # Tipo pagamento
    bapa_form = models.CharField(max_length=1)  # Forma
    bapa_banc = models.IntegerField()  # Banco
    bapa_cheq = models.IntegerField()  # Cheque
    bapa_bpar = models.DateField()  # Bom para

    # Controles Contábeis
    bapa_lote_valo = models.CharField(max_length=10)  # Lote valor
    bapa_ctrl_valo = models.IntegerField()  # Controle valor
    bapa_lote_cont = models.CharField(max_length=10)  # Lote contábil
    bapa_lanc_cont_long = models.IntegerField()  # Lançamento contábil

    # Auditoria
    bapa_audi = models.BooleanField()  # Auditado
    bapa_audi_data = models.DateField()  # Data auditoria
    bapa_audi_por = models.IntegerField()  # Auditado por
    _log_data = models.DateField()  # Log data
    _log_time = models.TimeField()  # Log hora
```

## Exemplos de Uso

### 1. Cadastrar Título a Pagar

```python
from contas_a_pagar.models import Titulospagar, Bapatitulos
from decimal import Decimal
from datetime import date, timedelta

# Criar título simples
titulo = Titulospagar.objects.create(
    titu_empr=1,
    titu_fili=1,
    titu_forn=1001,  # Fornecedor
    titu_titu='2024000001',  # Número do título
    titu_seri='NF',
    titu_parc='001',
    titu_emis=date.today(),
    titu_venc=date.today() + timedelta(days=30),  # Vencimento em 30 dias
    titu_valo=Decimal('1500.00'),
    titu_cont=2010001,  # Conta contábil fornecedores
    titu_cecu=1,  # Centro de custo
    titu_hist='Compra de materiais - NF 12345',
    titu_aber='A',  # Aberto
    titu_prov=True,  # É provisão
    titu_lote='LOT001'
)

print(f"Título {titulo.titu_titu} cadastrado")
```

### 2. Cadastrar Título Parcelado

```python
# Criar título parcelado (3x)
valor_total = Decimal('3000.00')
valor_parcela = valor_total / 3
base_titulo = '2024000002'

for i in range(1, 4):
    parcela = Titulospagar.objects.create(
        titu_empr=1,
        titu_fili=1,
        titu_forn=1002,
        titu_titu=base_titulo,
        titu_seri='NF',
        titu_parc=f'{i:03d}',  # 001, 002, 003
        titu_emis=date.today(),
        titu_venc=date.today() + timedelta(days=30*i),  # 30, 60, 90 dias
        titu_valo=valor_parcela,
        titu_cont=2010001,
        titu_cecu=1,
        titu_hist=f'Compra parcelada - Parcela {i}/3',
        titu_aber='A',
        titu_prov=True,
        titu_gera_parc=True,  # Gerado por parcelamento
        titu_lote='LOT002'
    )

    print(f"Parcela {i}: R$ {valor_parcela} - Venc: {parcela.titu_venc}")
```

### 3. Configurar Descontos e Juros

```python
# Título com desconto à vista e juros por atraso
titulo_desconto = Titulospagar.objects.create(
    titu_empr=1,
    titu_fili=1,
    titu_forn=1003,
    titu_titu='2024000003',
    titu_seri='NF',
    titu_parc='001',
    titu_emis=date.today(),
    titu_venc=date.today() + timedelta(days=30),
    titu_valo=Decimal('2000.00'),
    titu_cont=2010001,
    titu_hist='Compra com condições especiais',
    titu_aber='A',

    # Desconto à vista (5%)
    titu_desc_ao_dia=Decimal('5.00'),
    titu_desc_ao_dia_perc=True,  # Em percentual

    # Desconto por pontualidade (2%)
    titu_desc_pont=Decimal('2.00'),
    titu_desc_pont_perc=True,

    # Multa por atraso (2%)
    titu_mult=Decimal('2.00'),
    titu_mult_perc=True,

    # Juros mensais (1%)
    titu_juro_mes=Decimal('1.00'),
    titu_juro_mes_perc=True,

    titu_lote='LOT003'
)
```

### 4. Realizar Pagamento

```python
# Pagar título à vista com desconto
titulo_pagar = Titulospagar.objects.get(titu_titu='2024000001')

# Calcular desconto à vista
valor_original = titulo_pagar.titu_valo
desconto = valor_original * (titulo_pagar.titu_desc_ao_dia / 100) if titulo_pagar.titu_desc_ao_dia_perc else titulo_pagar.titu_desc_ao_dia or Decimal('0.00')
valor_pago = valor_original - desconto

# Registrar pagamento
pagamento = Bapatitulos.objects.create(
    bapa_empr=titulo_pagar.titu_empr,
    bapa_fili=titulo_pagar.titu_fili,
    bapa_forn=titulo_pagar.titu_forn,
    bapa_titu=titulo_pagar,
    bapa_seri=titulo_pagar.titu_seri,
    bapa_parc=titulo_pagar.titu_parc,
    bapa_dpag=date.today(),
    bapa_apag=valor_original,  # Valor a pagar
    bapa_pago=valor_pago,  # Valor efetivamente pago
    bapa_valo_pago=valor_pago,
    bapa_vdes=desconto,  # Desconto aplicado
    bapa_pdes=titulo_pagar.titu_desc_ao_dia,  # % Desconto
    bapa_topa='V',  # Tipo: À vista
    bapa_form='D',  # Forma: Dinheiro
    bapa_hist=f'Pagamento à vista com desconto de R$ {desconto}',
    bapa_emis=titulo_pagar.titu_emis,
    bapa_venc=titulo_pagar.titu_venc,
    bapa_cont=titulo_pagar.titu_cont,
    bapa_cecu=titulo_pagar.titu_cecu,
    bapa_lote_valo='PAG001'
)

# Atualizar status do título
titulo_pagar.titu_aber = 'P'
titulo_pagar.save()

print(f"Pagamento realizado: R$ {valor_pago} (desconto: R$ {desconto})")
```

### 5. Pagamento com Atraso (Juros e Multa)

```python
# Simular pagamento em atraso
titulo_atrasado = Titulospagar.objects.get(titu_titu='2024000003')
data_pagamento = titulo_atrasado.titu_venc + timedelta(days=15)  # 15 dias de atraso
dias_atraso = (data_pagamento - titulo_atrasado.titu_venc).days

# Calcular encargos
valor_original = titulo_atrasado.titu_valo
multa = valor_original * (titulo_atrasado.titu_mult / 100) if titulo_atrasado.titu_mult_perc else titulo_atrasado.titu_mult or Decimal('0.00')

# Juros proporcionais aos dias de atraso
juros_mes = titulo_atrasado.titu_juro_mes or Decimal('0.00')
juros = valor_original * (juros_mes / 100) * (dias_atraso / 30) if titulo_atrasado.titu_juro_mes_perc else Decimal('0.00')

valor_total = valor_original + multa + juros

# Registrar pagamento com encargos
pagamento_atraso = Bapatitulos.objects.create(
    bapa_empr=titulo_atrasado.titu_empr,
    bapa_fili=titulo_atrasado.titu_fili,
    bapa_forn=titulo_atrasado.titu_forn,
    bapa_titu=titulo_atrasado,
    bapa_seri=titulo_atrasado.titu_seri,
    bapa_parc=titulo_atrasado.titu_parc,
    bapa_dpag=data_pagamento,
    bapa_apag=valor_original,
    bapa_pago=valor_total,
    bapa_valo_pago=valor_total,
    bapa_vmul=multa,  # Valor da multa
    bapa_vjur=juros,  # Valor dos juros
    bapa_pmul=titulo_atrasado.titu_mult,  # % Multa
    bapa_pjur=juros_mes,  # % Juros
    bapa_topa='A',  # Tipo: Atrasado
    bapa_hist=f'Pagamento com {dias_atraso} dias de atraso. Multa: R$ {multa}, Juros: R$ {juros}',
    bapa_lote_valo='PAG002'
)

# Baixar título
titulo_atrasado.titu_aber = 'A'
titulo_atrasado.save()

print(f"Pagamento com atraso: R$ {valor_total} (original: R$ {valor_original}, encargos: R$ {multa + juros})")
```

### 6. Relatórios e Consultas

```python
# Títulos vencidos
def titulos_vencidos(empresa, filial):
    from django.db.models import Q

    return Titulospagar.objects.filter(
        titu_empr=empresa,
        titu_fili=filial,
        titu_aber='A',  # Abertos
        titu_venc__lt=date.today()  # Vencidos
    ).order_by('titu_venc')

# Títulos a vencer nos próximos dias
def titulos_a_vencer(empresa, filial, dias=30):
    data_limite = date.today() + timedelta(days=dias)

    return Titulospagar.objects.filter(
        titu_empr=empresa,
        titu_fili=filial,
        titu_aber='A',
        titu_venc__range=[date.today(), data_limite]
    ).order_by('titu_venc')

# Posição por fornecedor
def posicao_fornecedor(empresa, filial, fornecedor):
    from django.db.models import Sum, Count

    titulos_abertos = Titulospagar.objects.filter(
        titu_empr=empresa,
        titu_fili=filial,
        titu_forn=fornecedor,
        titu_aber='A'
    )

    resumo = titulos_abertos.aggregate(
        total_titulos=Count('titu_titu'),
        valor_total=Sum('titu_valo'),
        vencidos=Count('titu_titu', filter=Q(titu_venc__lt=date.today())),
        valor_vencido=Sum('titu_valo', filter=Q(titu_venc__lt=date.today()))
    )

    return {
        'fornecedor': fornecedor,
        'titulos_abertos': resumo['total_titulos'] or 0,
        'valor_total': resumo['valor_total'] or Decimal('0.00'),
        'titulos_vencidos': resumo['vencidos'] or 0,
        'valor_vencido': resumo['valor_vencido'] or Decimal('0.00')
    }

# Fluxo de caixa projetado
def fluxo_caixa_projetado(empresa, filial, data_inicio, data_fim):
    from django.db.models import Sum
    from django.db.models.functions import TruncDate

    return Titulospagar.objects.filter(
        titu_empr=empresa,
        titu_fili=filial,
        titu_aber='A',
        titu_venc__range=[data_inicio, data_fim]
    ).extra(
        select={'data_venc': 'DATE(titu_venc)'}
    ).values('data_venc').annotate(
        total_dia=Sum('titu_valo'),
        qtd_titulos=Count('titu_titu')
    ).order_by('data_venc')

# Relatório de pagamentos realizados
def relatorio_pagamentos(empresa, filial, data_inicio, data_fim):
    return Bapatitulos.objects.filter(
        bapa_empr=empresa,
        bapa_fili=filial,
        bapa_dpag__range=[data_inicio, data_fim]
    ).select_related('bapa_titu').order_by('bapa_dpag')
```

### 7. Funções Utilitárias

```python
# Calcular valor líquido com descontos
def calcular_valor_liquido(titulo, data_pagamento=None):
    if not data_pagamento:
        data_pagamento = date.today()

    valor_original = titulo.titu_valo
    desconto_total = Decimal('0.00')

    # Desconto à vista (se pago até o vencimento)
    if data_pagamento <= titulo.titu_venc and titulo.titu_desc_ao_dia:
        if titulo.titu_desc_ao_dia_perc:
            desconto_total += valor_original * (titulo.titu_desc_ao_dia / 100)
        else:
            desconto_total += titulo.titu_desc_ao_dia

    # Desconto por pontualidade
    if data_pagamento <= titulo.titu_venc and titulo.titu_desc_pont:
        if titulo.titu_desc_pont_perc:
            desconto_total += valor_original * (titulo.titu_desc_pont / 100)
        else:
            desconto_total += titulo.titu_desc_pont

    return valor_original - desconto_total

# Calcular encargos por atraso
def calcular_encargos_atraso(titulo, data_pagamento):
    if data_pagamento <= titulo.titu_venc:
        return {'multa': Decimal('0.00'), 'juros': Decimal('0.00')}

    dias_atraso = (data_pagamento - titulo.titu_venc).days
    valor_original = titulo.titu_valo

    # Multa
    multa = Decimal('0.00')
    if titulo.titu_mult:
        if titulo.titu_mult_perc:
            multa = valor_original * (titulo.titu_mult / 100)
        else:
            multa = titulo.titu_mult

    # Juros
    juros = Decimal('0.00')
    if titulo.titu_juro_mes:
        if titulo.titu_juro_mes_perc:
            juros = valor_original * (titulo.titu_juro_mes / 100) * (dias_atraso / 30)
        else:
            juros = titulo.titu_juro_mes * (dias_atraso / 30)

    return {'multa': multa, 'juros': juros, 'dias_atraso': dias_atraso}

# Validar dados do título
def validar_titulo(titulo_data):
    erros = []

    # Validar datas
    if titulo_data.get('titu_venc') and titulo_data.get('titu_emis'):
        if titulo_data['titu_venc'] < titulo_data['titu_emis']:
            erros.append('Data de vencimento não pode ser anterior à emissão')

    # Validar valor
    if titulo_data.get('titu_valo') and titulo_data['titu_valo'] <= 0:
        erros.append('Valor do título deve ser maior que zero')

    # Validar percentuais
    for campo in ['titu_desc_ao_dia', 'titu_desc_pont', 'titu_mult', 'titu_juro_mes']:
        valor = titulo_data.get(campo)
        eh_percentual = titulo_data.get(f'{campo}_perc')

        if valor and eh_percentual and (valor < 0 or valor > 100):
            erros.append(f'Percentual {campo} deve estar entre 0% e 100%')

    return erros

# Gerar número de título automático
def gerar_numero_titulo(empresa, filial, serie='NF'):
    ultimo_titulo = Titulospagar.objects.filter(
        titu_empr=empresa,
        titu_fili=filial,
        titu_seri=serie,
        titu_titu__startswith=f'{date.today().year}'
    ).order_by('-titu_titu').first()

    if ultimo_titulo:
        ultimo_numero = int(ultimo_titulo.titu_titu[-6:])  # Últimos 6 dígitos
        novo_numero = ultimo_numero + 1
    else:
        novo_numero = 1

    return f'{date.today().year}{novo_numero:06d}'
```

## API Endpoints

### Títulos a Pagar

```
contas_a_pagar


GET
/api/{slug}/contas_a_pagar/titulos-pagar/



POST
/api/{slug}/contas_a_pagar/titulos-pagar/



GET
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/



PUT
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/



PATCH
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/



DELETE
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/



POST
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/baixar_titulo/



DELETE
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/excluir_baixa/



GET
/api/{slug}/contas_a_pagar/titulos-pagar/{id}/historico_baixas/



GET
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/



PUT
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/



PATCH
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/



DELETE
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/



POST
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/baixar/



DELETE
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/excluir_baixa/



GET
/api/{slug}/contas_a_pagar/titulos-pagar/{titu_empr}/{titu_fili}/{titu_forn}/{titu_titu}/{titu_seri}/{titu_parc}/{titu_emis}/{titu_venc}/historico_baixas/
```
