# App Entradas_Estoque

## Visão Geral

O app **Entradas_Estoque** é responsável pelo controle e gestão das entradas de produtos no estoque da empresa. Este módulo permite registrar, consultar e gerenciar todas as movimentações de entrada de mercadorias, mantendo um histórico completo das operações de estoque.

## Funcionalidades Principais

- **Registro de Entradas**: Cadastro de entradas de produtos no estoque
- **Controle de Quantidades**: Gestão das quantidades movimentadas
- **Controle de Valores**: Registro dos valores totais das entradas
- **Histórico de Movimentações**: Manutenção do histórico completo de entradas
- **Controle por Empresa/Filial**: Segregação por empresa e filial
- **Observações**: Campo para anotações e observações sobre as entradas

## Modelos

### EntradaEstoque

Modelo principal que representa uma entrada de produto no estoque.

```python
class EntradaEstoque(models.Model):
    entr_sequ = models.IntegerField(primary_key=True)  # Sequencial único
    entr_empr = models.IntegerField(default=1)         # Código da empresa
    entr_fili = models.IntegerField(default=1)         # Código da filial
    entr_prod = models.CharField(max_length=10)        # Código do produto
    entr_enti = models.CharField(max_length=10)        # Código da entidade (fornecedor)
    entr_data = models.DateField()                     # Data da entrada
    entr_quan = models.DecimalField(max_digits=10, decimal_places=2)  # Quantidade
    entr_tota = models.DecimalField(max_digits=10, decimal_places=2)  # Valor total
    entr_obse = models.CharField(max_length=100)       # Observações
    entr_usua = models.IntegerField()                  # Usuário responsável
```

#### Campos Principais:
- **entr_sequ**: Chave primária sequencial
- **entr_empr/entr_fili**: Identificação da empresa e filial
- **entr_prod**: Código do produto (relaciona com app Produtos)
- **entr_enti**: Código da entidade fornecedora (relaciona com app Entidades)
- **entr_data**: Data da movimentação de entrada
- **entr_quan**: Quantidade de produtos entrada
- **entr_tota**: Valor total da entrada
- **entr_obse**: Campo para observações adicionais
- **entr_usua**: Usuário que registrou a entrada

## Exemplos de Uso

### Registrar Nova Entrada

```python
from Entradas_Estoque.models import EntradaEstoque
from datetime import date

# Criar nova entrada de estoque
entrada = EntradaEstoque.objects.create(
    entr_empr=1,
    entr_fili=1,
    entr_prod='PROD001',
    entr_enti='FORN001',
    entr_data=date.today(),
    entr_quan=100.00,
    entr_tota=5000.00,
    entr_obse='Entrada por compra',
    entr_usua=1
)
```

### Consultar Entradas por Produto

```python
# Buscar todas as entradas de um produto específico
entradas_produto = EntradaEstoque.objects.filter(
    entr_prod='PROD001'
).order_by('-entr_data')

# Calcular total de entradas do produto
total_quantidade = sum(entrada.entr_quan for entrada in entradas_produto)
total_valor = sum(entrada.entr_tota for entrada in entradas_produto)
```

### Relatório de Entradas por Período

```python
from datetime import datetime, timedelta

# Entradas dos últimos 30 dias
data_inicio = datetime.now().date() - timedelta(days=30)
entradas_periodo = EntradaEstoque.objects.filter(
    entr_data__gte=data_inicio
).select_related('produto', 'fornecedor')

# Agrupar por produto
from django.db.models import Sum
resumo_entradas = EntradaEstoque.objects.filter(
    entr_data__gte=data_inicio
).values('entr_prod').annotate(
    total_quantidade=Sum('entr_quan'),
    total_valor=Sum('entr_tota')
)
```

### Validações e Funções Utilitárias

```python
# Validar entrada antes de salvar
def validar_entrada(entrada_data):
    if entrada_data['entr_quan'] <= 0:
        raise ValueError('Quantidade deve ser maior que zero')
    
    if entrada_data['entr_tota'] <= 0:
        raise ValueError('Valor total deve ser maior que zero')
    
    # Verificar se produto existe
    from Produtos.models import Produtos
    if not Produtos.objects.filter(prod_codi=entrada_data['entr_prod']).exists():
        raise ValueError('Produto não encontrado')

# Calcular valor unitário
def calcular_valor_unitario(entrada):
    if entrada.entr_quan > 0:
        return entrada.entr_tota / entrada.entr_quan
    return 0
```

## Endpoints da API

### Listar Entradas
```http
GET /api/entradas-estoque/
GET /api/entradas-estoque/?entr_prod=PROD001
GET /api/entradas-estoque/?entr_data__gte=2024-01-01
GET /api/entradas-estoque/?entr_enti=FORN001
```

### Criar Nova Entrada
```http
POST /api/entradas-estoque/
Content-Type: application/json

{
    "entr_empr": 1,
    "entr_fili": 1,
    "entr_prod": "PROD001",
    "entr_enti": "FORN001",
    "entr_data": "2024-01-15",
    "entr_quan": 50.00,
    "entr_tota": 2500.00,
    "entr_obse": "Entrada por compra",
    "entr_usua": 1
}
```

### Buscar Entrada Específica
```http
GET /api/entradas-estoque/{id}/
```

### Atualizar Entrada
```http
PUT /api/entradas-estoque/{id}/
Content-Type: application/json

{
    "entr_quan": 60.00,
    "entr_tota": 3000.00,
    "entr_obse": "Quantidade corrigida"
}
```

### Filtros Avançados
```http
# Entradas por período
GET /api/entradas-estoque/?entr_data__range=2024-01-01,2024-01-31

# Entradas por fornecedor e produto
GET /api/entradas-estoque/?entr_enti=FORN001&entr_prod=PROD001

# Entradas com valor acima de um limite
GET /api/entradas-estoque/?entr_tota__gte=1000.00
```

## Considerações Técnicas

### Banco de Dados
- **Tabela**: `entradasestoque`
- **Chave Primária**: `entr_sequ` (sequencial)
- **Índices Recomendados**:
  - `(entr_empr, entr_fili, entr_prod, entr_data)` - Unique constraint
  - `entr_data` - Para consultas por período
  - `entr_prod` - Para consultas por produto
  - `entr_enti` - Para consultas por fornecedor

### Validações
- Quantidade deve ser maior que zero
- Valor total deve ser maior que zero
- Data não pode ser futura
- Produto deve existir no cadastro
- Fornecedor deve existir no cadastro (se informado)

### Triggers e Procedures
- Atualização automática do estoque atual
- Cálculo de custos médios
- Logs de auditoria para rastreabilidade
- Validações de integridade referencial

## Integração com Outros Apps

### Produtos
- Validação de códigos de produtos
- Atualização de estoque atual
- Cálculo de custos médios

### Entidades
- Validação de fornecedores
- Histórico de compras por fornecedor

### Auditoria
- Log de todas as operações
- Rastreabilidade de alterações
- Controle de usuários

## Troubleshooting

### Problemas Comuns

1. **Erro de Produto Não Encontrado**
   ```python
   # Verificar se produto existe
   from Produtos.models import Produtos
   produto_existe = Produtos.objects.filter(prod_codi='PROD001').exists()
   ```

2. **Erro de Duplicação de Entrada**
   ```python
   # Verificar constraint unique_together
   entrada_existe = EntradaEstoque.objects.filter(
       entr_empr=1,
       entr_fili=1,
       entr_prod='PROD001',
       entr_data='2024-01-15'
   ).exists()
   ```

3. **Problemas de Performance**
   ```python
   # Usar select_related para otimizar consultas
   entradas = EntradaEstoque.objects.select_related(
       'produto', 'fornecedor'
   ).filter(entr_data__gte=data_inicio)
   ```

### Logs de Debug
```python
import logging
logger = logging.getLogger('entradas_estoque')

# Log de entrada criada
logger.info(f'Nova entrada criada: {entrada.entr_sequ} - Produto: {entrada.entr_prod}')

# Log de erro
logger.error(f'Erro ao criar entrada: {str(e)}')
```

### Comandos de Manutenção
```bash
# Verificar integridade dos dados
python manage.py shell -c "from Entradas_Estoque.models import EntradaEstoque; print(EntradaEstoque.objects.count())"

# Reprocessar estoques
python manage.py recalcular_estoques

# Backup de entradas
python manage.py dumpdata Entradas_Estoque > backup_entradas.json
```

## Conclusão

O app **Entradas_Estoque** é fundamental para o controle de estoque da empresa, fornecendo funcionalidades completas para registro e gestão de entradas de produtos. Sua integração com outros módulos garante a consistência e integridade dos dados do sistema.