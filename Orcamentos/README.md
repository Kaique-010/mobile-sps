# App Orcamentos

Este app gerencia o sistema de orçamentos de venda, permitindo criar propostas comerciais antes da efetivação dos pedidos.

## Funcionalidades

### 1. Gestão de Orçamentos

### 2. Itens do Orçamento

### Modelo Orcamentos

```python
class Orcamentos(models.Model):
    # Identificação
    pedi_empr = models.IntegerField()  # Empresa
    pedi_fili = models.IntegerField()  # Filial
    pedi_nume = models.BigAutoField(primary_key=True)  # Número do orçamento

    # Cliente e Vendedor
    pedi_forn = models.CharField(max_length=60)  # Cliente
    pedi_vend = models.CharField(max_length=15)  # Vendedor

    # Dados do Orçamento
    pedi_data = models.DateField()  # Data do orçamento
    pedi_tota = models.DecimalField(max_digits=15, decimal_places=2)  # Total
    pedi_obse = models.TextField()  # Observações
```

### Modelo ItensOrcamento

```python
class ItensOrcamento(models.Model):
    # Identificação
    iped_empr = models.IntegerField()  # Empresa
    iped_fili = models.IntegerField()  # Filial
    iped_pedi = models.CharField(max_length=50)  # Número do orçamento
    iped_item = models.IntegerField()  # Sequencial do item

    # Produto
    iped_prod = models.CharField(max_length=60)  # Código do produto
    iped_forn = models.IntegerField()  # Fornecedor do produto

    # Quantidades e Preços
    iped_quan = models.DecimalField(max_digits=15, decimal_places=5)  # Quantidade
    iped_unit = models.DecimalField(max_digits=15, decimal_places=5)  # Preço unitário
    iped_unli = models.DecimalField(max_digits=15, decimal_places=5)  # Preço líquido
    iped_tota = models.DecimalField(max_digits=15, decimal_places=2)  # Total do item

    # Descontos
    iped_desc = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto
    iped_pdes_item = models.DecimalField(max_digits=5, decimal_places=2)  # % Desconto

    # Controle
    iped_data = models.DateField()  # Data do item
```

## Exemplos de Uso

### 1. Criar Novo Orçamento

```python
from Orcamentos.models import Orcamentos, ItensOrcamento
from decimal import Decimal
from datetime import date

# Criar cabeçalho do orçamento
orcamento = Orcamentos.objects.create(
    pedi_empr=1,
    pedi_fili=1,
    pedi_forn='1001',  # Código do cliente
    pedi_data=date.today(),
    pedi_tota=Decimal('0.00'),  # Será calculado após itens
    pedi_vend='001',
    pedi_obse='Orçamento válido por 30 dias. Frete por conta do cliente.'
)

print(f"Orçamento criado: {orcamento.pedi_nume}")
```

### 2. Adicionar Itens ao Orçamento

```python
# Adicionar primeiro item
item1 = ItensOrcamento.objects.create(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(orcamento.pedi_nume),
    iped_item=1,
    iped_prod='PROD001',
    iped_quan=Decimal('10.00'),
    iped_unit=Decimal('25.50'),
    iped_tota=Decimal('255.00'),
    iped_desc=Decimal('0.00'),
    iped_pdes_item=Decimal('0.00'),
    iped_data=date.today()
)

# Adicionar segundo item com desconto
item2 = ItensOrcamento.objects.create(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(orcamento.pedi_nume),
    iped_item=2,
    iped_prod='PROD002',
    iped_quan=Decimal('5.00'),
    iped_unit=Decimal('100.00'),
    iped_pdes_item=Decimal('10.00'),
    iped_desc=Decimal('50.00'),
    iped_tota=Decimal('450.00'),  # 500 - 50 desconto
    iped_data=date.today()
)
```

### 3. Calcular Total do Orçamento

```python
from django.db.models import Sum

# Calcular total dos itens
total_itens = ItensOrcamento.objects.filter(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(orcamento.pedi_nume)
).aggregate(total=Sum('iped_tota'))['total'] or Decimal('0.00')

# Atualizar total do orçamento
orcamento.pedi_tota = total_itens
orcamento.save()

print(f"Total do orçamento: R$ {total_itens}")
```

### 4. Consultar Orçamentos

```python
# Orçamentos do dia
orcamentos_hoje = Orcamentos.objects.filter(
    pedi_data=date.today()
)

# Orçamentos por vendedor
orcamentos_vendedor = Orcamentos.objects.filter(
    pedi_vend='001',
    pedi_data__month=date.today().month
)

# Orçamentos por cliente
orcamentos_cliente = Orcamentos.objects.filter(
    pedi_forn='1001'
).order_by('-pedi_data')

# Orçamentos por período
from datetime import timedelta
inicio = date.today() - timedelta(days=30)
orcamentos_periodo = Orcamentos.objects.filter(
    pedi_data__gte=inicio
)
```

ENDPOINTS DISPONNÍVEIS
orcamentos

GET
/api/{slug}/orcamentos/orcamentos/

POST
/api/{slug}/orcamentos/orcamentos/

GET
/api/{slug}/orcamentos/orcamentos/{empresa}/{filial}/{numero}/

PUT
/api/{slug}/orcamentos/orcamentos/{empresa}/{filial}/{numero}/

PATCH
/api/{slug}/orcamentos/orcamentos/{empresa}/{filial}/{numero}/

DELETE
/api/{slug}/orcamentos/orcamentos/{empresa}/{filial}/{numero}/

POST
/api/{slug}/orcamentos/orcamentos/{empresa}/{filial}/{numero}/transformar-em-pedido/

GET
/api/{slug}/orcamentos/orcamentos/{pedi_nume}/

PUT
/api/{slug}/orcamentos/orcamentos/{pedi_nume}/

PATCH
/api/{slug}/orcamentos/orcamentos/{pedi_nume}/

DELETE
/api/{slug}/orcamentos/orcamentos/{pedi_nume}/

POST
/api/{slug}/orcamentos/orcamentos/{pedi_nume}/transformar-em-pedido/

GET
/api/{slug}/orcamentos/orcamentos/parametros-desconto/

PATCH
/api/{slug}/orcamentos/orcamentos/parametros-desconto/
