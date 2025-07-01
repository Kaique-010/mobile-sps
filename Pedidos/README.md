# App Pedidos

Este app gerencia o sistema completo de pedidos de venda, incluindo cabeçalho do pedido, itens, controle de status e integração financeira.

## Funcionalidades

### 1. Gestão de Pedidos de Venda

- **Cabeçalho do Pedido**: Dados principais do pedido
- **Controle de Status**: Acompanhamento do ciclo de vida
- **Tipos Financeiros**: À vista, a prazo ou sem financeiro
- **Vendedores**: Associação com vendedores
- **Observações**: Campo livre para anotações

### 2. Itens do Pedido

- **Produtos**: Vinculação com cadastro de produtos
- **Quantidades**: Controle preciso de quantidades
- **Preços**: Unitário e total por item
- **Descontos**: Por item e percentual
- **Frete**: Rateio de frete por item
- **Custos**: Controle de custos por item

### 3. Controle de Status

- **Pendente**: Pedido criado, aguardando processamento
- **Processando**: Em preparação
- **Enviado**: Despachado para entrega
- **Concluído**: Finalizado com sucesso
- **Cancelado**: Cancelado pelo cliente ou sistema

### 4. Tipos Financeiros

- **À Vista**: Pagamento imediato
- **A Prazo**: Pagamento parcelado
- **Sem Financeiro**: Pedidos sem cobrança (amostras, brindes)

## Estrutura dos Dados

### Modelo PedidoVenda

```python
class PedidoVenda(models.Model):
    # Identificação
    pedi_empr = models.IntegerField()  # Empresa
    pedi_fili = models.IntegerField()  # Filial
    pedi_nume = models.BigAutoField(primary_key=True)  # Número do pedido

    # Cliente e Vendedor
    pedi_forn = models.CharField(max_length=60)  # Cliente/Fornecedor
    pedi_vend = models.CharField(max_length=15)  # Vendedor

    # Dados do Pedido
    pedi_data = models.DateField()  # Data do pedido
    pedi_tota = models.DecimalField(max_digits=15, decimal_places=2)  # Total
    pedi_fina = models.CharField(choices=TIPO_FINANCEIRO)  # Tipo financeiro

    # Controle
    pedi_stat = models.CharField(choices=STATUS_CHOICES)  # Status
    pedi_canc = models.BooleanField()  # Cancelado
    pedi_obse = models.TextField()  # Observações
```

### Modelo Itenspedidovenda

```python
class Itenspedidovenda(models.Model):
    # Identificação
    iped_empr = models.IntegerField()  # Empresa
    iped_fili = models.IntegerField()  # Filial
    iped_pedi = models.CharField(max_length=50)  # Número do pedido
    iped_item = models.IntegerField()  # Sequencial do item

    # Produto
    iped_prod = models.CharField(max_length=60)  # Código do produto
    iped_unme = models.CharField(max_length=6)  # Unidade de medida

    # Quantidades e Preços
    iped_quan = models.DecimalField(max_digits=15, decimal_places=5)  # Quantidade
    iped_unit = models.DecimalField(max_digits=15, decimal_places=5)  # Preço unitário
    iped_unli = models.DecimalField(max_digits=15, decimal_places=5)  # Preço líquido
    iped_tota = models.DecimalField(max_digits=15, decimal_places=2)  # Total do item

    # Descontos e Custos
    iped_desc = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto
    iped_perc_desc = models.DecimalField(max_digits=5, decimal_places=2)  # % Desconto
    iped_cust = models.DecimalField(max_digits=15, decimal_places=4)  # Custo
    iped_fret = models.DecimalField(max_digits=15, decimal_places=2)  # Frete

    # Controle
    iped_vend = models.IntegerField()  # Vendedor
    iped_tipo = models.IntegerField()  # Tipo do item
    iped_desc_item = models.BooleanField()  # Item com desconto
    iped_data = models.DateField(auto_now=True)  # Data do item
```

## Exemplos de Uso

### 1. Criar Novo Pedido

```python
from Pedidos.models import PedidoVenda, Itenspedidovenda
from decimal import Decimal
from datetime import date

# Criar cabeçalho do pedido
pedido = PedidoVenda.objects.create(
    pedi_empr=1,
    pedi_fili=1,
    pedi_forn='1001',  # Código do cliente
    pedi_data=date.today(),
    pedi_tota=Decimal('0.00'),  # Será calculado após itens
    pedi_fina='0',  # À vista
    pedi_vend='001',
    pedi_stat='0',  # Pendente
    pedi_obse='Pedido criado via sistema'
)

print(f"Pedido criado: {pedido.pedi_nume}")
```

### 2. Adicionar Itens ao Pedido

```python
# Adicionar primeiro item
item1 = Itenspedidovenda.objects.create(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(pedido.pedi_nume),
    iped_item=1,
    iped_prod='PROD001',
    iped_quan=Decimal('10.00'),
    iped_unit=Decimal('25.50'),
    iped_tota=Decimal('255.00'),
    iped_unme='UN',
    iped_desc=Decimal('0.00'),
    iped_perc_desc=Decimal('0.00')
)

# Adicionar segundo item com desconto
item2 = Itenspedidovenda.objects.create(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(pedido.pedi_nume),
    iped_item=2,
    iped_prod='PROD002',
    iped_quan=Decimal('5.00'),
    iped_unit=Decimal('100.00'),
    iped_perc_desc=Decimal('10.00'),
    iped_desc=Decimal('50.00'),
    iped_tota=Decimal('450.00'),  # 500 - 50 desconto
    iped_unme='UN'
)
```

### 3. Calcular Total do Pedido

```python
from django.db.models import Sum

# Calcular total dos itens
total_itens = Itenspedidovenda.objects.filter(
    iped_empr=1,
    iped_fili=1,
    iped_pedi=str(pedido.pedi_nume)
).aggregate(total=Sum('iped_tota'))['total'] or Decimal('0.00')

# Atualizar total do pedido
pedido.pedi_tota = total_itens
pedido.save()

print(f"Total do pedido: R$ {total_itens}")
```

### 4. Consultar Pedidos por Status

```python
# Pedidos pendentes
pedidos_pendentes = PedidoVenda.objects.filter(
    pedi_stat='0',
    pedi_canc=False
)

# Pedidos do dia
pedidos_hoje = PedidoVenda.objects.filter(
    pedi_data=date.today()
)

# Pedidos por vendedor
pedidos_vendedor = PedidoVenda.objects.filter(
    pedi_vend='001',
    pedi_data__month=date.today().month
)
```

### 5. Atualizar Status do Pedido

```python
# Processar pedido
pedido.pedi_stat = '1'  # Processando
pedido.save()

# Enviar pedido
pedido.pedi_stat = '2'  # Enviado
pedido.save()

# Concluir pedido
pedido.pedi_stat = '3'  # Concluído
pedido.save()

# Cancelar pedido
pedido.pedi_stat = '4'  # Cancelado
pedido.pedi_canc = True
pedido.save()
```

### 6. Relatórios e Consultas

```python
# Vendas por período
from django.db.models import Sum, Count
from datetime import datetime, timedelta

# Vendas do mês
inicio_mes = date.today().replace(day=1)
vendas_mes = PedidoVenda.objects.filter(
    pedi_data__gte=inicio_mes,
    pedi_canc=False
).aggregate(
    total_vendas=Sum('pedi_tota'),
    qtd_pedidos=Count('pedi_nume')
)

# Top produtos vendidos
top_produtos = Itenspedidovenda.objects.values('iped_prod').annotate(
    total_vendido=Sum('iped_quan'),
    valor_total=Sum('iped_tota')
).order_by('-total_vendido')[:10]

# Performance de vendedores
vendedores = PedidoVenda.objects.values('pedi_vend').annotate(
    total_vendas=Sum('pedi_tota'),
    qtd_pedidos=Count('pedi_nume')
).order_by('-total_vendas')
```

## API Endpoints

### Pedidos

```
GET /api/{licenca}/pedidos/pedidos/
POST /api/{licenca}/pedidos/pedidos/
GET /api/{licenca}/pedidos/pedidos/{numero}/
PUT /api/{licenca}/pedidos/pedidos/{numero}/
PATCH /api/{licenca}/pedidos/pedidos/{numero}/
DELETE /api/{licenca}/pedidos/pedidos/{numero}/
```

### Itens do Pedido

```
GET /api/{licenca}/pedidos/itens/
POST /api/{licenca}/pedidos/itens/
GET /api/{licenca}/pedidos/itens/{id}/
PUT /api/{licenca}/pedidos/itens/{id}/
DELETE /api/{licenca}/pedidos/itens/{id}/
```

### Filtros Disponíveis

#### Pedidos

- `pedi_empr`: Filtrar por empresa
- `pedi_fili`: Filtrar por filial
- `pedi_forn`: Filtrar por cliente
- `pedi_vend`: Filtrar por vendedor
- `pedi_stat`: Filtrar por status
- `pedi_fina`: Filtrar por tipo financeiro
- `pedi_data`: Filtrar por data (range)
- `pedi_canc`: Filtrar cancelados
- `search`: Busca geral

#### Itens

- `iped_pedi`: Filtrar por pedido
- `iped_prod`: Filtrar por produto
- `iped_vend`: Filtrar por vendedor
- `data_range`: Filtrar por período

### Exemplos de Requisições

```
GET /api/empresa123/pedidos/pedidos/?pedi_stat=0&pedi_data__gte=2024-01-01
GET /api/empresa123/pedidos/pedidos/?pedi_vend=001&pedi_fina=0
GET /api/empresa123/pedidos/itens/?iped_pedi=12345
GET /api/empresa123/pedidos/pedidos/?search=cliente123
```

## Considerações Técnicas

### Banco de Dados

- **Tabelas**: `pedidosvenda`, `itenspedidovenda`
- **Managed**: False (tabelas não gerenciadas pelo Django)
- **Chaves Compostas**: Empresa + Filial + Pedido + Item

### Índices Recomendados

```sql
-- Pedidos
CREATE INDEX idx_pedidos_empresa_filial ON pedidosvenda (pedi_empr, pedi_fili);
CREATE INDEX idx_pedidos_cliente ON pedidosvenda (pedi_forn);
CREATE INDEX idx_pedidos_vendedor ON pedidosvenda (pedi_vend);
CREATE INDEX idx_pedidos_data ON pedidosvenda (pedi_data);
CREATE INDEX idx_pedidos_status ON pedidosvenda (pedi_stat);
CREATE INDEX idx_pedidos_cancelado ON pedidosvenda (pedi_canc);

-- Itens
CREATE INDEX idx_itens_pedido ON itenspedidovenda (iped_pedi);
CREATE INDEX idx_itens_produto ON itenspedidovenda (iped_prod);
CREATE INDEX idx_itens_vendedor ON itenspedidovenda (iped_vend);
CREATE INDEX idx_itens_data ON itenspedidovenda (iped_data);
```

### Validações Recomendadas

```python
from django.core.exceptions import ValidationError
from decimal import Decimal

def clean(self):
    # Validar total do pedido
    if self.pedi_tota < 0:
        raise ValidationError('Total do pedido não pode ser negativo')

    # Validar status
    if self.pedi_canc and self.pedi_stat not in ['4']:
        raise ValidationError('Pedido cancelado deve ter status cancelado')

    # Validar quantidades nos itens
    if hasattr(self, 'iped_quan') and self.iped_quan <= 0:
        raise ValidationError('Quantidade deve ser maior que zero')

    # Validar preços
    if hasattr(self, 'iped_unit') and self.iped_unit < 0:
        raise ValidationError('Preço unitário não pode ser negativo')
```

### Triggers e Procedures

```sql
-- Trigger para atualizar total do pedido
CREATE TRIGGER trg_atualiza_total_pedido
AFTER INSERT OR UPDATE OR DELETE ON itenspedidovenda
FOR EACH ROW
BEGIN
    UPDATE pedidosvenda
    SET pedi_tota = (
        SELECT COALESCE(SUM(iped_tota), 0)
        FROM itenspedidovenda
        WHERE iped_pedi = NEW.iped_pedi
    )
    WHERE pedi_nume = NEW.iped_pedi;
END;

-- Procedure para cancelar pedido
CREATE PROCEDURE sp_cancelar_pedido(IN p_pedido VARCHAR(50))
BEGIN
    UPDATE pedidosvenda
    SET pedi_stat = '4', pedi_canc = TRUE
    WHERE pedi_nume = p_pedido;
END;
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Com Entidades (Clientes)
class PedidoVenda(models.Model):
    cliente = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        db_column='pedi_forn',
        to_field='enti_clie'
    )

# Com Produtos
class Itenspedidovenda(models.Model):
    produto = models.ForeignKey(
        'Produtos.Produtos',
        on_delete=models.PROTECT,
        db_column='iped_prod',
        to_field='prod_codi'
    )

# Com Contas a Receber
class ContaReceber(models.Model):
    pedido = models.ForeignKey(
        'Pedidos.PedidoVenda',
        on_delete=models.PROTECT,
        related_name='contas_receber'
    )
```

### Workflows de Integração

```python
# Gerar contas a receber do pedido
def gerar_contas_receber(pedido):
    if pedido.pedi_fina == '1':  # A prazo
        # Criar parcelas
        pass
    elif pedido.pedi_fina == '0':  # À vista
        # Criar conta única
        pass

# Baixar estoque dos produtos
def baixar_estoque(pedido):
    for item in pedido.itens.all():
        # Atualizar saldo do produto
        pass

# Gerar comissão para vendedor
def calcular_comissao(pedido):
    # Calcular comissão baseada no total
    pass
```

## Troubleshooting

### Problemas Comuns

1. **Erro de chave duplicada em itens**

   - Verificar sequencial do item
   - Usar `get_or_create()` com cuidado

2. **Total do pedido inconsistente**

   - Implementar recálculo automático
   - Validar antes de salvar

3. **Performance lenta em relatórios**

   - Criar índices apropriados
   - Usar agregações no banco
   - Implementar cache

4. **Problemas de concorrência**

   - Usar transações atômicas
   - Implementar locks quando necessário

5. **Status inconsistente**
   - Validar transições de status
   - Implementar máquina de estados

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'Pedidos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Comandos de Manutenção

```python
# management/commands/recalcular_totais.py
from django.core.management.base import BaseCommand
from Pedidos.models import PedidoVenda, Itenspedidovenda

class Command(BaseCommand):
    def handle(self, *args, **options):
        for pedido in PedidoVenda.objects.all():
            total = pedido.itens.aggregate(
                total=Sum('iped_tota')
            )['total'] or 0
            pedido.pedi_tota = total
            pedido.save()

# management/commands/limpar_pedidos_antigos.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Arquivar pedidos antigos
        pass
```

CREATE OR REPLACE VIEW Pedidos_geral as(
WITH itens_agrupados AS (
SELECT
i.iped_empr,
i.iped_fili,
i.iped_pedi,
SUM(i.iped_quan) AS quantidade,
STRING_AGG(p.prod_nome, ', ' ORDER BY i.iped_item) AS produtos
FROM itenspedidovenda i
LEFT JOIN produtos p
ON i.iped_prod = p.prod_codi
AND i.iped_empr = p.prod_empr
GROUP BY i.iped_empr, i.iped_fili, i.iped_pedi
)

SELECT
p.pedi_empr AS Empresa,
p.pedi_fili AS Filial,
p.pedi_nume AS Numero_Pedido,
c.enti_clie AS Codigo_Cliente,
c.enti_nome AS Nome_Cliente,
p.pedi_data AS Data_Pedido,
COALESCE(i.quantidade, 0) AS Quantidade_Total,
COALESCE(i.produtos, 'Sem itens') AS Itens_do_Pedido,
p.pedi_tota AS Valor_Total,
CASE
WHEN CAST(p.pedi_fina AS INTEGER) = 0 THEN 'À VISTA'
WHEN CAST(p.pedi_fina AS INTEGER) = 1 THEN 'A PRAZO'
WHEN CAST(p.pedi_fina AS INTEGER) = 2 THEN 'SEM FINANCEIRO'
ELSE 'OUTRO'
END AS Tipo_Financeiro,
v.enti_nome AS Nome_Vendedor
FROM pedidosvenda p
LEFT JOIN entidades c
ON p.pedi_forn = c.enti_clie AND p.pedi_empr = c.enti_empr
LEFT JOIN entidades v
ON p.pedi_vend = v.enti_clie AND p.pedi_empr = v.enti_empr
LEFT JOIN itens_agrupados i
ON p.pedi_nume = i.iped_pedi AND p.pedi_empr = i.iped_empr AND p.pedi_fili = i.iped_fili
ORDER BY p.pedi_data DESC, p.pedi_nume DESC)
