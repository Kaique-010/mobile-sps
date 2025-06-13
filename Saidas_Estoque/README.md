# App Saidas_Estoque

## Visão Geral

O app **Saidas_Estoque** é responsável pelo controle e gestão das saídas de produtos do estoque da empresa. Este módulo permite registrar, consultar e gerenciar todas as movimentações de saída de mercadorias, mantendo um histórico completo das operações de baixa no estoque.

## Funcionalidades Principais

- **Registro de Saídas**: Cadastro de saídas de produtos do estoque
- **Controle de Quantidades**: Gestão das quantidades movimentadas
- **Controle de Valores**: Registro dos valores totais das saídas
- **Histórico de Movimentações**: Manutenção do histórico completo de saídas
- **Controle por Empresa/Filial**: Segregação por empresa e filial
- **Observações**: Campo para anotações e observações sobre as saídas
- **Rastreabilidade**: Controle de usuário responsável pela movimentação

## Modelos

### SaidasEstoque

Modelo principal que representa uma saída de produto do estoque.

```python
class SaidasEstoque(models.Model):
    said_sequ = models.IntegerField(primary_key=True)  # Sequencial único
    said_empr = models.IntegerField(default=1)         # Código da empresa
    said_fili = models.IntegerField(default=1)         # Código da filial
    said_prod = models.CharField(max_length=10)        # Código do produto
    said_enti = models.CharField(max_length=10)        # Código da entidade (cliente)
    said_data = models.DateField()                     # Data da saída
    said_quan = models.DecimalField(max_digits=10, decimal_places=2)  # Quantidade
    said_tota = models.DecimalField(max_digits=10, decimal_places=2)  # Valor total
    said_obse = models.CharField(max_length=100)       # Observações
    said_usua = models.IntegerField()                  # Usuário responsável
```

#### Campos Principais:
- **said_sequ**: Chave primária sequencial
- **said_empr/said_fili**: Identificação da empresa e filial
- **said_prod**: Código do produto (relaciona com app Produtos)
- **said_enti**: Código da entidade cliente (relaciona com app Entidades)
- **said_data**: Data da movimentação de saída
- **said_quan**: Quantidade de produtos saída
- **said_tota**: Valor total da saída
- **said_obse**: Campo para observações adicionais
- **said_usua**: Usuário que registrou a saída

#### Constraints:
- **Unique Constraint**: `(said_empr, said_fili, said_prod, said_data)` - Evita duplicação de saídas
- **Ordenação**: Por data decrescente (`-said_data`)

## Exemplos de Uso

### Registrar Nova Saída

```python
from Saidas_Estoque.models import SaidasEstoque
from datetime import date

# Criar nova saída de estoque
saida = SaidasEstoque.objects.create(
    said_empr=1,
    said_fili=1,
    said_prod='PROD001',
    said_enti='CLI001',
    said_data=date.today(),
    said_quan=25.00,
    said_tota=1250.00,
    said_obse='Saída por venda',
    said_usua=1
)
```

### Consultar Saídas por Produto

```python
# Buscar todas as saídas de um produto específico
saidas_produto = SaidasEstoque.objects.filter(
    said_prod='PROD001'
).order_by('-said_data')

# Calcular total de saídas do produto
total_quantidade = sum(saida.said_quan for saida in saidas_produto)
total_valor = sum(saida.said_tota for saida in saidas_produto)
```

### Relatório de Saídas por Período

```python
from datetime import datetime, timedelta
from django.db.models import Sum, Count

# Saídas dos últimos 30 dias
data_inicio = datetime.now().date() - timedelta(days=30)
saidas_periodo = SaidasEstoque.objects.filter(
    said_data__gte=data_inicio
)

# Agrupar por produto
resumo_saidas = SaidasEstoque.objects.filter(
    said_data__gte=data_inicio
).values('said_prod').annotate(
    total_quantidade=Sum('said_quan'),
    total_valor=Sum('said_tota'),
    total_movimentacoes=Count('said_sequ')
)
```

### Controle de Estoque

```python
# Verificar estoque disponível antes da saída
def verificar_estoque_disponivel(produto_codigo, quantidade_saida):
    from Entradas_Estoque.models import EntradaEstoque
    
    # Calcular total de entradas
    total_entradas = EntradaEstoque.objects.filter(
        entr_prod=produto_codigo
    ).aggregate(total=Sum('entr_quan'))['total'] or 0
    
    # Calcular total de saídas
    total_saidas = SaidasEstoque.objects.filter(
        said_prod=produto_codigo
    ).aggregate(total=Sum('said_quan'))['total'] or 0
    
    estoque_atual = total_entradas - total_saidas
    
    return estoque_atual >= quantidade_saida

# Validar saída antes de salvar
def validar_saida(saida_data):
    if saida_data['said_quan'] <= 0:
        raise ValueError('Quantidade deve ser maior que zero')
    
    if not verificar_estoque_disponivel(saida_data['said_prod'], saida_data['said_quan']):
        raise ValueError('Estoque insuficiente para a saída')
```

### Relatórios Avançados

```python
# Produtos com maior saída no período
def produtos_maior_saida(data_inicio, data_fim):
    return SaidasEstoque.objects.filter(
        said_data__range=[data_inicio, data_fim]
    ).values('said_prod').annotate(
        total_quantidade=Sum('said_quan'),
        total_valor=Sum('said_tota')
    ).order_by('-total_quantidade')

# Clientes com maior volume de compras
def clientes_maior_volume(data_inicio, data_fim):
    return SaidasEstoque.objects.filter(
        said_data__range=[data_inicio, data_fim],
        said_enti__isnull=False
    ).values('said_enti').annotate(
        total_quantidade=Sum('said_quan'),
        total_valor=Sum('said_tota')
    ).order_by('-total_valor')
```

## Endpoints da API

### Listar Saídas
```http
GET /api/saidas-estoque/
GET /api/saidas-estoque/?said_prod=PROD001
GET /api/saidas-estoque/?said_data__gte=2024-01-01
GET /api/saidas-estoque/?said_enti=CLI001
```

### Criar Nova Saída
```http
POST /api/saidas-estoque/
Content-Type: application/json

{
    "said_empr": 1,
    "said_fili": 1,
    "said_prod": "PROD001",
    "said_enti": "CLI001",
    "said_data": "2024-01-15",
    "said_quan": 10.00,
    "said_tota": 500.00,
    "said_obse": "Saída por venda",
    "said_usua": 1
}
```

### Buscar Saída Específica
```http
GET /api/saidas-estoque/{id}/
```

### Atualizar Saída
```http
PUT /api/saidas-estoque/{id}/
Content-Type: application/json

{
    "said_quan": 15.00,
    "said_tota": 750.00,
    "said_obse": "Quantidade corrigida"
}
```

### Filtros Avançados
```http
# Saídas por período
GET /api/saidas-estoque/?said_data__range=2024-01-01,2024-01-31

# Saídas por cliente e produto
GET /api/saidas-estoque/?said_enti=CLI001&said_prod=PROD001

# Saídas com valor acima de um limite
GET /api/saidas-estoque/?said_tota__gte=1000.00

# Saídas sem cliente (transferências internas)
GET /api/saidas-estoque/?said_enti__isnull=true
```

### Relatórios via API
```http
# Resumo de saídas por produto
GET /api/saidas-estoque/resumo-por-produto/?data_inicio=2024-01-01&data_fim=2024-01-31

# Top produtos com maior saída
GET /api/saidas-estoque/top-produtos/?limite=10

# Estoque atual por produto
GET /api/saidas-estoque/estoque-atual/?said_prod=PROD001
```

## Considerações Técnicas

### Banco de Dados
- **Tabela**: `saidasestoque`
- **Chave Primária**: `said_sequ` (sequencial)
- **Índices Recomendados**:
  - `(said_empr, said_fili, said_prod, said_data)` - Unique constraint
  - `said_data` - Para consultas por período
  - `said_prod` - Para consultas por produto
  - `said_enti` - Para consultas por cliente
  - `said_usua` - Para auditoria por usuário

### Validações
- Quantidade deve ser maior que zero
- Valor total deve ser maior que zero
- Verificação de estoque disponível
- Data não pode ser futura
- Produto deve existir no cadastro
- Cliente deve existir no cadastro (se informado)

### Triggers e Procedures
- Atualização automática do estoque atual
- Validação de estoque disponível
- Cálculo de custos de saída (FIFO/LIFO)
- Logs de auditoria para rastreabilidade
- Validações de integridade referencial

### Performance
- Índices otimizados para consultas frequentes
- Paginação para listagens grandes
- Cache para cálculos de estoque
- Agregações otimizadas para relatórios

## Integração com Outros Apps

### Produtos
- Validação de códigos de produtos
- Atualização de estoque atual
- Controle de produtos ativos/inativos

### Entidades
- Validação de clientes
- Histórico de vendas por cliente
- Análise de comportamento de compra

### Pedidos
- Baixa automática por vendas
- Rastreamento de itens vendidos
- Integração com faturamento

### Auditoria
- Log de todas as operações
- Rastreabilidade de alterações
- Controle de usuários

### CaixaDiario
- Integração com movimentações financeiras
- Controle de vendas à vista

## Troubleshooting

### Problemas Comuns

1. **Erro de Estoque Insuficiente**
   ```python
   # Verificar estoque atual
   def verificar_estoque(produto_codigo):
       from django.db.models import Sum
       entradas = EntradaEstoque.objects.filter(
           entr_prod=produto_codigo
       ).aggregate(total=Sum('entr_quan'))['total'] or 0
       
       saidas = SaidasEstoque.objects.filter(
           said_prod=produto_codigo
       ).aggregate(total=Sum('said_quan'))['total'] or 0
       
       return entradas - saidas
   ```

2. **Erro de Duplicação de Saída**
   ```python
   # Verificar constraint unique
   saida_existe = SaidasEstoque.objects.filter(
       said_empr=1,
       said_fili=1,
       said_prod='PROD001',
       said_data='2024-01-15'
   ).exists()
   ```

3. **Problemas de Performance em Relatórios**
   ```python
   # Usar agregações otimizadas
   from django.db.models import Sum, Count, Avg
   
   resumo = SaidasEstoque.objects.filter(
       said_data__gte=data_inicio
   ).aggregate(
       total_quantidade=Sum('said_quan'),
       total_valor=Sum('said_tota'),
       total_movimentacoes=Count('said_sequ'),
       valor_medio=Avg('said_tota')
   )
   ```

### Logs de Debug
```python
import logging
logger = logging.getLogger('saidas_estoque')

# Log de saída criada
logger.info(f'Nova saída criada: {saida.said_sequ} - Produto: {saida.said_prod} - Quantidade: {saida.said_quan}')

# Log de validação de estoque
logger.warning(f'Estoque baixo para produto {produto_codigo}: {estoque_atual} unidades')

# Log de erro
logger.error(f'Erro ao criar saída: {str(e)}')
```

### Comandos de Manutenção
```bash
# Verificar integridade dos dados
python manage.py shell -c "from Saidas_Estoque.models import SaidasEstoque; print(SaidasEstoque.objects.count())"

# Recalcular estoques
python manage.py recalcular_estoques

# Relatório de estoque atual
python manage.py relatorio_estoque

# Backup de saídas
python manage.py dumpdata Saidas_Estoque > backup_saidas.json

# Verificar inconsistências
python manage.py verificar_estoque_negativo
```

### Monitoramento
```python
# Alertas de estoque baixo
def verificar_estoque_minimo():
    produtos_baixo_estoque = []
    
    for produto in Produtos.objects.filter(ativo=True):
        estoque_atual = calcular_estoque_atual(produto.codigo)
        if estoque_atual < produto.estoque_minimo:
            produtos_baixo_estoque.append({
                'produto': produto.codigo,
                'estoque_atual': estoque_atual,
                'estoque_minimo': produto.estoque_minimo
            })
    
    return produtos_baixo_estoque
```

## Conclusão

O app **Saidas_Estoque** é essencial para o controle de estoque da empresa, fornecendo funcionalidades completas para registro e gestão de saídas de produtos. Sua integração com outros módulos garante a consistência dos dados e permite um controle eficiente do estoque, evitando rupturas e otimizando a gestão de inventário.