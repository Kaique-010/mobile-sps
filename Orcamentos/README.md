# App Orcamentos

Este app gerencia o sistema de orçamentos de venda, permitindo criar propostas comerciais antes da efetivação dos pedidos.

## Funcionalidades

### 1. Gestão de Orçamentos

- **Propostas Comerciais**: Criação de orçamentos para clientes
- **Controle por Empresa/Filial**: Segregação por unidade de negócio
- **Vendedores**: Associação com equipe de vendas
- **Validade**: Controle de prazo dos orçamentos
- **Observações**: Campo livre para condições especiais

### 2. Itens do Orçamento

- **Produtos**: Vinculação com cadastro de produtos
- **Quantidades**: Controle preciso de quantidades
- **Preços**: Unitário, líquido e total por item
- **Descontos**: Por item e percentual
- **Fornecedores**: Associação com fornecedores dos produtos

### 3. Processo de Vendas

- **Elaboração**: Criação da proposta comercial
- **Apresentação**: Envio para cliente
- **Negociação**: Ajustes de preços e condições
- **Aprovação**: Aceite do cliente
- **Conversão**: Transformação em pedido de venda

## Estrutura dos Dados

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

### 5. Relatórios de Orçamentos

```python
# Orçamentos por vendedor
from django.db.models import Sum, Count, Avg

relatorio_vendedores = Orcamentos.objects.values('pedi_vend').annotate(
    total_orcamentos=Count('pedi_nume'),
    valor_total=Sum('pedi_tota'),
    ticket_medio=Avg('pedi_tota')
).order_by('-valor_total')

# Produtos mais orçados
produtos_orcados = ItensOrcamento.objects.values('iped_prod').annotate(
    total_quantidade=Sum('iped_quan'),
    total_valor=Sum('iped_tota'),
    qtd_orcamentos=Count('iped_pedi', distinct=True)
).order_by('-total_quantidade')

# Performance mensal
from django.db.models import TruncMonth
performance_mensal = Orcamentos.objects.annotate(
    mes=TruncMonth('pedi_data')
).values('mes').annotate(
    total_orcamentos=Count('pedi_nume'),
    valor_total=Sum('pedi_tota')
).order_by('mes')
```

### 6. Converter Orçamento em Pedido

```python
def converter_orcamento_em_pedido(orcamento_id):
    """Converte um orçamento em pedido de venda"""
    from Pedidos.models import PedidoVenda, Itenspedidovenda
    
    # Buscar orçamento
    orcamento = Orcamentos.objects.get(pedi_nume=orcamento_id)
    itens_orcamento = ItensOrcamento.objects.filter(
        iped_pedi=str(orcamento_id)
    )
    
    # Criar pedido
    pedido = PedidoVenda.objects.create(
        pedi_empr=orcamento.pedi_empr,
        pedi_fili=orcamento.pedi_fili,
        pedi_forn=orcamento.pedi_forn,
        pedi_data=date.today(),
        pedi_tota=orcamento.pedi_tota,
        pedi_vend=orcamento.pedi_vend,
        pedi_fina='0',  # Definir tipo financeiro
        pedi_stat='0',  # Pendente
        pedi_obse=f'Convertido do orçamento {orcamento_id}'
    )
    
    # Criar itens do pedido
    for item_orc in itens_orcamento:
        Itenspedidovenda.objects.create(
            iped_empr=item_orc.iped_empr,
            iped_fili=item_orc.iped_fili,
            iped_pedi=str(pedido.pedi_nume),
            iped_item=item_orc.iped_item,
            iped_prod=item_orc.iped_prod,
            iped_quan=item_orc.iped_quan,
            iped_unit=item_orc.iped_unit,
            iped_tota=item_orc.iped_tota,
            iped_desc=item_orc.iped_desc,
            iped_perc_desc=item_orc.iped_pdes_item
        )
    
    return pedido
```

## API Endpoints

### Orçamentos
```
GET /api/{licenca}/orcamentos/orcamentos/
POST /api/{licenca}/orcamentos/orcamentos/
GET /api/{licenca}/orcamentos/orcamentos/{numero}/
PUT /api/{licenca}/orcamentos/orcamentos/{numero}/
PATCH /api/{licenca}/orcamentos/orcamentos/{numero}/
DELETE /api/{licenca}/orcamentos/orcamentos/{numero}/
```

### Itens do Orçamento
```
GET /api/{licenca}/orcamentos/itens/
POST /api/{licenca}/orcamentos/itens/
GET /api/{licenca}/orcamentos/itens/{id}/
PUT /api/{licenca}/orcamentos/itens/{id}/
DELETE /api/{licenca}/orcamentos/itens/{id}/
```

### Ações Especiais
```
POST /api/{licenca}/orcamentos/orcamentos/{numero}/converter-pedido/
GET /api/{licenca}/orcamentos/relatorios/vendedores/
GET /api/{licenca}/orcamentos/relatorios/produtos/
```

### Filtros Disponíveis

#### Orçamentos
- `pedi_empr`: Filtrar por empresa
- `pedi_fili`: Filtrar por filial
- `pedi_forn`: Filtrar por cliente
- `pedi_vend`: Filtrar por vendedor
- `pedi_data`: Filtrar por data (range)
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo
- `search`: Busca geral

#### Itens
- `iped_pedi`: Filtrar por orçamento
- `iped_prod`: Filtrar por produto
- `iped_forn`: Filtrar por fornecedor
- `data_range`: Filtrar por período

### Exemplos de Requisições
```
GET /api/empresa123/orcamentos/orcamentos/?pedi_vend=001&pedi_data__gte=2024-01-01
GET /api/empresa123/orcamentos/orcamentos/?pedi_forn=1001&valor_min=1000
GET /api/empresa123/orcamentos/itens/?iped_pedi=12345
POST /api/empresa123/orcamentos/orcamentos/12345/converter-pedido/
```

## Considerações Técnicas

### Banco de Dados
- **Tabelas**: `orcamentosvenda`, `itensorcamentovenda`
- **Managed**: False (tabelas não gerenciadas pelo Django)
- **Chaves Compostas**: Empresa + Filial + Orçamento + Item

### Índices Recomendados
```sql
-- Orçamentos
CREATE INDEX idx_orcamentos_empresa_filial ON orcamentosvenda (pedi_empr, pedi_fili);
CREATE INDEX idx_orcamentos_cliente ON orcamentosvenda (pedi_forn);
CREATE INDEX idx_orcamentos_vendedor ON orcamentosvenda (pedi_vend);
CREATE INDEX idx_orcamentos_data ON orcamentosvenda (pedi_data);
CREATE INDEX idx_orcamentos_total ON orcamentosvenda (pedi_tota);

-- Itens
CREATE INDEX idx_itens_orc_orcamento ON itensorcamentovenda (iped_pedi);
CREATE INDEX idx_itens_orc_produto ON itensorcamentovenda (iped_prod);
CREATE INDEX idx_itens_orc_fornecedor ON itensorcamentovenda (iped_forn);
CREATE INDEX idx_itens_orc_data ON itensorcamentovenda (iped_data);
```

### Validações Recomendadas

```python
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

def clean(self):
    # Validar total do orçamento
    if self.pedi_tota < 0:
        raise ValidationError('Total do orçamento não pode ser negativo')
    
    # Validar data (não pode ser muito antiga)
    if self.pedi_data < date.today() - timedelta(days=365):
        raise ValidationError('Data do orçamento muito antiga')
    
    # Validar quantidades nos itens
    if hasattr(self, 'iped_quan') and self.iped_quan <= 0:
        raise ValidationError('Quantidade deve ser maior que zero')
    
    # Validar preços
    if hasattr(self, 'iped_unit') and self.iped_unit < 0:
        raise ValidationError('Preço unitário não pode ser negativo')
    
    # Validar desconto
    if hasattr(self, 'iped_pdes_item') and (self.iped_pdes_item < 0 or self.iped_pdes_item > 100):
        raise ValidationError('Percentual de desconto deve estar entre 0% e 100%')
```

### Triggers e Procedures

```sql
-- Trigger para atualizar total do orçamento
CREATE TRIGGER trg_atualiza_total_orcamento
AFTER INSERT OR UPDATE OR DELETE ON itensorcamentovenda
FOR EACH ROW
BEGIN
    UPDATE orcamentosvenda 
    SET pedi_tota = (
        SELECT COALESCE(SUM(iped_tota), 0)
        FROM itensorcamentovenda 
        WHERE iped_pedi = NEW.iped_pedi
    )
    WHERE pedi_nume = NEW.iped_pedi;
END;

-- Procedure para copiar orçamento
CREATE PROCEDURE sp_copiar_orcamento(
    IN p_orcamento_origem VARCHAR(50),
    IN p_novo_cliente VARCHAR(60)
)
BEGIN
    DECLARE novo_numero INT;
    
    -- Criar novo orçamento
    INSERT INTO orcamentosvenda (pedi_empr, pedi_fili, pedi_forn, pedi_data, pedi_tota, pedi_vend, pedi_obse)
    SELECT pedi_empr, pedi_fili, p_novo_cliente, CURDATE(), pedi_tota, pedi_vend, pedi_obse
    FROM orcamentosvenda WHERE pedi_nume = p_orcamento_origem;
    
    SET novo_numero = LAST_INSERT_ID();
    
    -- Copiar itens
    INSERT INTO itensorcamentovenda (iped_empr, iped_fili, iped_pedi, iped_item, iped_prod, iped_quan, iped_unit, iped_tota, iped_desc, iped_pdes_item, iped_data)
    SELECT iped_empr, iped_fili, novo_numero, iped_item, iped_prod, iped_quan, iped_unit, iped_tota, iped_desc, iped_pdes_item, CURDATE()
    FROM itensorcamentovenda WHERE iped_pedi = p_orcamento_origem;
END;
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Com Entidades (Clientes)
class Orcamentos(models.Model):
    cliente = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        db_column='pedi_forn',
        to_field='enti_clie'
    )

# Com Produtos
class ItensOrcamento(models.Model):
    produto = models.ForeignKey(
        'Produtos.Produtos',
        on_delete=models.PROTECT,
        db_column='iped_prod',
        to_field='prod_codi'
    )

# Com Pedidos (conversão)
class PedidoVenda(models.Model):
    orcamento_origem = models.ForeignKey(
        'Orcamentos.Orcamentos',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_gerados'
    )
```

### Workflows de Integração

```python
# Sincronizar preços com tabela de preços
def atualizar_precos_orcamento(orcamento_id):
    from Produtos.models import Tabelaprecos
    
    itens = ItensOrcamento.objects.filter(iped_pedi=orcamento_id)
    for item in itens:
        preco = Tabelaprecos.objects.filter(
            tabe_prod=item.iped_prod,
            tabe_empr=item.iped_empr,
            tabe_fili=item.iped_fili
        ).first()
        
        if preco:
            item.iped_unit = preco.tabe_prco
            item.iped_tota = item.iped_quan * item.iped_unit
            item.save()

# Verificar disponibilidade de estoque
def verificar_estoque_orcamento(orcamento_id):
    from Produtos.models import SaldoProduto
    
    itens = ItensOrcamento.objects.filter(iped_pedi=orcamento_id)
    produtos_indisponiveis = []
    
    for item in itens:
        saldo = SaldoProduto.objects.filter(
            produto_codigo=item.iped_prod,
            empresa=item.iped_empr,
            filial=item.iped_fili
        ).first()
        
        if not saldo or saldo.saldo_estoque < item.iped_quan:
            produtos_indisponiveis.append({
                'produto': item.iped_prod,
                'solicitado': item.iped_quan,
                'disponivel': saldo.saldo_estoque if saldo else 0
            })
    
    return produtos_indisponiveis
```

## Troubleshooting

### Problemas Comuns

1. **Erro de chave duplicada em itens**
   - Verificar sequencial do item
   - Usar numeração automática

2. **Total do orçamento inconsistente**
   - Implementar recálculo automático
   - Validar antes de salvar

3. **Performance lenta em relatórios**
   - Criar índices apropriados
   - Usar agregações no banco
   - Implementar cache para consultas frequentes

4. **Problemas na conversão para pedido**
   - Validar dados antes da conversão
   - Usar transações atômicas
   - Verificar disponibilidade de estoque

5. **Orçamentos duplicados**
   - Implementar validação de duplicatas
   - Usar função de cópia controlada

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'Orcamentos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Comandos de Manutenção

```python
# management/commands/recalcular_totais_orcamentos.py
from django.core.management.base import BaseCommand
from Orcamentos.models import Orcamentos, ItensOrcamento

class Command(BaseCommand):
    def handle(self, *args, **options):
        for orcamento in Orcamentos.objects.all():
            total = ItensOrcamento.objects.filter(
                iped_pedi=str(orcamento.pedi_nume)
            ).aggregate(total=Sum('iped_tota'))['total'] or 0
            
            orcamento.pedi_tota = total
            orcamento.save()
            
        self.stdout.write('Totais recalculados com sucesso')

# management/commands/limpar_orcamentos_antigos.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        from datetime import date, timedelta
        
        # Arquivar orçamentos com mais de 1 ano
        data_limite = date.today() - timedelta(days=365)
        orcamentos_antigos = Orcamentos.objects.filter(
            pedi_data__lt=data_limite
        )
        
        count = orcamentos_antigos.count()
        # Implementar arquivamento
        
        self.stdout.write(f'{count} orçamentos arquivados')
```