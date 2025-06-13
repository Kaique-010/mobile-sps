# App Contas a Pagar

Este app gerencia o sistema de contas a pagar, controlando títulos, fornecedores, vencimentos e pagamentos da empresa.

## Funcionalidades

### 1. Gestão de Títulos a Pagar

- **Cadastro de Títulos**: Registro de obrigações financeiras
- **Controle de Vencimentos**: Gestão de prazos e datas
- **Parcelamento**: Suporte a títulos parcelados
- **Provisões**: Controle de provisões contábeis
- **Histórico**: Rastreamento completo de alterações

### 2. Controle de Pagamentos

- **Baixas**: Registro de pagamentos realizados
- **Formas de Pagamento**: Dinheiro, cheque, transferência
- **Juros e Multas**: Cálculo automático de encargos
- **Descontos**: Aplicação de descontos por antecipação
- **Conciliação Bancária**: Integração com extratos

### 3. Gestão Financeira

- **Fluxo de Caixa**: Projeções de pagamentos
- **Relatórios Gerenciais**: Análises por fornecedor, vencimento
- **Controle de Aprovação**: Workflow de aprovações
- **Integração Contábil**: Lançamentos automáticos
- **DDA**: Débito Direto Autorizado

## Estrutura dos Dados

### Modelo Titulospagar

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
titulo_pagar.titu_aber = 'B'  # Baixado
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
    bapa_form='T',  # Forma: Transferência
    bapa_hist=f'Pagamento com {dias_atraso} dias de atraso. Multa: R$ {multa}, Juros: R$ {juros}',
    bapa_lote_valo='PAG002'
)

# Baixar título
titulo_atrasado.titu_aber = 'B'
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
GET /api/{licenca}/contas-a-pagar/titulos/
POST /api/{licenca}/contas-a-pagar/titulos/
GET /api/{licenca}/contas-a-pagar/titulos/{numero}/
PUT /api/{licenca}/contas-a-pagar/titulos/{numero}/
PATCH /api/{licenca}/contas-a-pagar/titulos/{numero}/
DELETE /api/{licenca}/contas-a-pagar/titulos/{numero}/
```

### Pagamentos
```
GET /api/{licenca}/contas-a-pagar/pagamentos/
POST /api/{licenca}/contas-a-pagar/pagamentos/
GET /api/{licenca}/contas-a-pagar/pagamentos/{id}/
PUT /api/{licenca}/contas-a-pagar/pagamentos/{id}/
DELETE /api/{licenca}/contas-a-pagar/pagamentos/{id}/
```

### Ações Especiais
```
POST /api/{licenca}/contas-a-pagar/titulos/{numero}/pagar/
POST /api/{licenca}/contas-a-pagar/titulos/{numero}/parcelar/
GET /api/{licenca}/contas-a-pagar/relatorios/vencimentos/
GET /api/{licenca}/contas-a-pagar/relatorios/fornecedores/
GET /api/{licenca}/contas-a-pagar/fluxo-caixa/
POST /api/{licenca}/contas-a-pagar/titulos/importar/
```

### Filtros Disponíveis

#### Títulos
- `titu_empr`: Filtrar por empresa
- `titu_fili`: Filtrar por filial
- `titu_forn`: Filtrar por fornecedor
- `titu_aber`: Status (A/B/C)
- `vencimento_de`: Data inicial
- `vencimento_ate`: Data final
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo
- `vencidos`: Apenas vencidos
- `search`: Busca geral

#### Pagamentos
- `bapa_empr`: Empresa
- `bapa_fili`: Filial
- `bapa_forn`: Fornecedor
- `data_pagamento_de`: Data inicial
- `data_pagamento_ate`: Data final
- `forma_pagamento`: Forma
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo

### Exemplos de Requisições
```
GET /api/empresa123/contas-a-pagar/titulos/?titu_forn=1001&titu_aber=A
GET /api/empresa123/contas-a-pagar/titulos/?vencidos=true
GET /api/empresa123/contas-a-pagar/pagamentos/?data_pagamento_de=2024-01-01&data_pagamento_ate=2024-01-31
POST /api/empresa123/contas-a-pagar/titulos/2024000001/pagar/
{
  "valor_pago": 1500.00,
  "data_pagamento": "2024-01-15",
  "forma_pagamento": "T",
  "desconto": 75.00
}
```

## Considerações Técnicas

### Banco de Dados
- **Tabelas**: `titulospagar`, `bapatitulos`
- **Managed**: False (tabelas não gerenciadas pelo Django)
- **Chaves Compostas**: Múltiplos campos formam chaves únicas

### Índices Recomendados
```sql
-- Títulos a Pagar
CREATE INDEX idx_titulos_empresa_filial ON titulospagar (titu_empr, titu_fili);
CREATE INDEX idx_titulos_fornecedor ON titulospagar (titu_forn);
CREATE INDEX idx_titulos_vencimento ON titulospagar (titu_venc);
CREATE INDEX idx_titulos_status ON titulospagar (titu_aber);
CREATE INDEX idx_titulos_emissao ON titulospagar (titu_emis);
CREATE INDEX idx_titulos_valor ON titulospagar (titu_valo);
CREATE INDEX idx_titulos_conta ON titulospagar (titu_cont);
CREATE INDEX idx_titulos_centro_custo ON titulospagar (titu_cecu);

-- Pagamentos
CREATE INDEX idx_pagamentos_empresa_filial ON bapatitulos (bapa_empr, bapa_fili);
CREATE INDEX idx_pagamentos_fornecedor ON bapatitulos (bapa_forn);
CREATE INDEX idx_pagamentos_data ON bapatitulos (bapa_dpag);
CREATE INDEX idx_pagamentos_titulo ON bapatitulos (bapa_titu);
CREATE INDEX idx_pagamentos_forma ON bapatitulos (bapa_form);
CREATE INDEX idx_pagamentos_valor ON bapatitulos (bapa_valo_pago);
```

### Validações Recomendadas

```python
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

def clean(self):
    # Validar datas
    if hasattr(self, 'titu_venc') and hasattr(self, 'titu_emis'):
        if self.titu_venc and self.titu_emis and self.titu_venc < self.titu_emis:
            raise ValidationError('Data de vencimento não pode ser anterior à emissão')
    
    # Validar valores
    if hasattr(self, 'titu_valo') and self.titu_valo and self.titu_valo <= 0:
        raise ValidationError('Valor do título deve ser maior que zero')
    
    # Validar percentuais
    campos_percentual = [
        ('titu_desc_ao_dia', 'titu_desc_ao_dia_perc'),
        ('titu_desc_pont', 'titu_desc_pont_perc'),
        ('titu_mult', 'titu_mult_perc'),
        ('titu_juro_mes', 'titu_juro_mes_perc')
    ]
    
    for campo_valor, campo_perc in campos_percentual:
        if hasattr(self, campo_valor) and hasattr(self, campo_perc):
            valor = getattr(self, campo_valor)
            eh_perc = getattr(self, campo_perc)
            
            if valor and eh_perc and (valor < 0 or valor > 100):
                raise ValidationError(f'Percentual {campo_valor} deve estar entre 0% e 100%')
    
    # Validar status
    if hasattr(self, 'titu_aber') and self.titu_aber not in ['A', 'B', 'C']:
        raise ValidationError('Status deve ser A (Aberto), B (Baixado) ou C (Cancelado)')
    
    # Validar pagamento
    if hasattr(self, 'bapa_pago') and hasattr(self, 'bapa_apag'):
        if self.bapa_pago and self.bapa_apag and self.bapa_pago < 0:
            raise ValidationError('Valor pago não pode ser negativo')
```

### Triggers e Procedures

```sql
-- Trigger para validar pagamentos
CREATE TRIGGER trg_valida_pagamento
BEFORE INSERT ON bapatitulos
FOR EACH ROW
BEGIN
    DECLARE v_status CHAR(1);
    DECLARE v_valor_titulo DECIMAL(15,2);
    
    -- Verificar se título existe e está aberto
    SELECT titu_aber, titu_valo INTO v_status, v_valor_titulo
    FROM titulospagar 
    WHERE titu_titu = NEW.bapa_titu;
    
    IF v_status != 'A' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Título não está aberto para pagamento';
    END IF;
    
    -- Validar valor do pagamento
    IF NEW.bapa_pago > v_valor_titulo * 1.5 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Valor do pagamento muito alto';
    END IF;
END;

-- Trigger para atualizar status do título após pagamento
CREATE TRIGGER trg_atualiza_status_titulo
AFTER INSERT ON bapatitulos
FOR EACH ROW
BEGIN
    DECLARE v_total_pago DECIMAL(15,2);
    DECLARE v_valor_titulo DECIMAL(15,2);
    
    -- Calcular total pago
    SELECT COALESCE(SUM(bapa_pago), 0), MAX(t.titu_valo)
    INTO v_total_pago, v_valor_titulo
    FROM bapatitulos b
    JOIN titulospagar t ON t.titu_titu = b.bapa_titu
    WHERE b.bapa_titu = NEW.bapa_titu;
    
    -- Atualizar status se totalmente pago
    IF v_total_pago >= v_valor_titulo THEN
        UPDATE titulospagar 
        SET titu_aber = 'B'
        WHERE titu_titu = NEW.bapa_titu;
    END IF;
END;

-- Procedure para calcular posição financeira
CREATE PROCEDURE sp_posicao_financeira(
    IN p_empresa INT,
    IN p_filial INT,
    IN p_data_base DATE
)
BEGIN
    SELECT 
        t.titu_forn,
        COUNT(*) as qtd_titulos,
        SUM(t.titu_valo) as valor_total,
        SUM(CASE WHEN t.titu_venc < p_data_base THEN t.titu_valo ELSE 0 END) as valor_vencido,
        COUNT(CASE WHEN t.titu_venc < p_data_base THEN 1 END) as qtd_vencidos
    FROM titulospagar t
    WHERE t.titu_empr = p_empresa
    AND t.titu_fili = p_filial
    AND t.titu_aber = 'A'
    GROUP BY t.titu_forn
    ORDER BY valor_total DESC;
END;
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Com Entidades (Fornecedores)
class Titulospagar(models.Model):
    fornecedor = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        db_column='titu_forn',
        to_field='enti_forn'
    )

# Com Compras/Notas Fiscais
class Titulospagar(models.Model):
    nota_fiscal = models.ForeignKey(
        'NotasFiscais.NotaFiscal',
        on_delete=models.SET_NULL,
        db_column='titu_id_nota_fisc',
        null=True,
        blank=True
    )

# Com Contabilidade
class Titulospagar(models.Model):
    conta_contabil = models.ForeignKey(
        'Contabilidade.PlanoContas',
        on_delete=models.PROTECT,
        db_column='titu_cont'
    )
    
    centro_custo = models.ForeignKey(
        'Contabilidade.CentroCusto',
        on_delete=models.PROTECT,
        db_column='titu_cecu'
    )
```

### Workflows de Integração

```python
# Gerar título a partir de nota fiscal
def gerar_titulo_nota_fiscal(nota_fiscal, condicao_pagamento):
    """Gera títulos a pagar baseado em nota fiscal de compra"""
    
    if condicao_pagamento['parcelas'] == 1:
        # Pagamento à vista
        titulo = Titulospagar.objects.create(
            titu_empr=nota_fiscal.empresa,
            titu_fili=nota_fiscal.filial,
            titu_forn=nota_fiscal.fornecedor_id,
            titu_titu=gerar_numero_titulo(nota_fiscal.empresa, nota_fiscal.filial),
            titu_seri='NF',
            titu_parc='001',
            titu_emis=nota_fiscal.data_emissao,
            titu_venc=nota_fiscal.data_emissao + timedelta(days=condicao_pagamento['prazo']),
            titu_valo=nota_fiscal.valor_total,
            titu_hist=f'NF {nota_fiscal.numero} - {nota_fiscal.fornecedor.nome}',
            titu_id_nota_fisc=nota_fiscal.id,
            titu_cont=2010001,  # Fornecedores
            titu_aber='A'
        )
        return [titulo]
    
    else:
        # Pagamento parcelado
        titulos = []
        valor_parcela = nota_fiscal.valor_total / condicao_pagamento['parcelas']
        numero_base = gerar_numero_titulo(nota_fiscal.empresa, nota_fiscal.filial)
        
        for i in range(1, condicao_pagamento['parcelas'] + 1):
            dias_venc = condicao_pagamento['prazo'] + (i - 1) * condicao_pagamento['intervalo']
            
            titulo = Titulospagar.objects.create(
                titu_empr=nota_fiscal.empresa,
                titu_fili=nota_fiscal.filial,
                titu_forn=nota_fiscal.fornecedor_id,
                titu_titu=numero_base,
                titu_seri='NF',
                titu_parc=f'{i:03d}',
                titu_emis=nota_fiscal.data_emissao,
                titu_venc=nota_fiscal.data_emissao + timedelta(days=dias_venc),
                titu_valo=valor_parcela,
                titu_hist=f'NF {nota_fiscal.numero} - Parcela {i}/{condicao_pagamento["parcelas"]}',
                titu_id_nota_fisc=nota_fiscal.id,
                titu_gera_parc=True,
                titu_cont=2010001,
                titu_aber='A'
            )
            titulos.append(titulo)
        
        return titulos

# Integração com caixa
def registrar_pagamento_caixa(titulo, valor_pago, forma_pagamento):
    """Registra pagamento no caixa automaticamente"""
    from CaixaDiario.models import Movicaixa
    
    movimento = Movicaixa.objects.create(
        movi_empr=titulo.titu_empr,
        movi_fili=titulo.titu_fili,
        movi_caix=1,  # Caixa padrão
        movi_data=date.today(),
        movi_entr=Decimal('0.00'),
        movi_said=valor_pago,  # Saída de caixa
        movi_tipo=20,  # Tipo: Pagamento fornecedor
        movi_obse=f'Pagamento título {titulo.titu_titu} - {titulo.titu_hist}',
        movi_hora=timezone.now().time(),
        movi_seri='PAG'
    )
    
    return movimento
```

## Troubleshooting

### Problemas Comuns

1. **Erro de chave duplicada**
   - Verificar unicidade da combinação empresa+filial+fornecedor+título+série+parcela
   - Usar função de geração automática de números

2. **Cálculos incorretos de juros/multa**
   - Verificar configuração de percentuais vs valores fixos
   - Validar fórmulas de cálculo proporcional

3. **Performance lenta em relatórios**
   - Criar índices apropriados
   - Usar agregações no banco
   - Implementar cache para consultas frequentes

4. **Problemas de conciliação**
   - Verificar integridade referencial
   - Implementar validações de negócio
   - Usar transações atômicas

5. **Títulos não baixando automaticamente**
   - Verificar triggers de atualização
   - Validar cálculos de valores pagos
   - Conferir regras de negócio

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'contas_a_pagar': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Comandos de Manutenção

```python
# management/commands/recalcular_encargos.py
from django.core.management.base import BaseCommand
from contas_a_pagar.models import Titulospagar

class Command(BaseCommand):
    def handle(self, *args, **options):
        titulos_vencidos = Titulospagar.objects.filter(
            titu_aber='A',
            titu_venc__lt=date.today()
        )
        
        for titulo in titulos_vencidos:
            # Recalcular encargos
            encargos = calcular_encargos_atraso(titulo, date.today())
            
            # Atualizar campos se necessário
            if encargos['multa'] > 0 or encargos['juros'] > 0:
                self.stdout.write(
                    f"Título {titulo.titu_titu}: Multa R$ {encargos['multa']}, "
                    f"Juros R$ {encargos['juros']}"
                )
        
        self.stdout.write('Recálculo de encargos concluído')

# management/commands/alertas_vencimento.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Títulos vencendo nos próximos 7 dias
        titulos_alerta = titulos_a_vencer(1, 1, 7)
        
        for titulo in titulos_alerta:
            # Enviar alerta por email
            # Implementar notificação
            pass
        
        self.stdout.write(f'{titulos_alerta.count()} alertas enviados')
```