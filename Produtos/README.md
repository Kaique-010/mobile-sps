# App Produtos

Este app gerencia o cadastro completo de produtos, incluindo categorização, preços, estoque e histórico de alterações.

## Funcionalidades

### 1. Gestão de Produtos

- **Cadastro Completo**: Código, nome, unidade de medida, localização
- **Categorização**: Grupos, subgrupos, famílias e marcas
- **Classificação Fiscal**: NCM para tributação
- **Código de Barras**: Suporte a código de barras
- **Imagens**: Upload e exibição de fotos dos produtos

### 2. Estrutura Hierárquica

- **Grupos de Produtos**: Categorias principais
- **Subgrupos**: Subcategorias dentro dos grupos
- **Famílias**: Classificação mais específica
- **Marcas**: Fabricantes e marcas dos produtos
- **Unidades de Medida**: UN, KG, M, L, etc.

### 3. Gestão de Preços

- **Tabela de Preços**: Preços por empresa e filial
- **Múltiplos Preços**: À vista, a prazo, varejo
- **Cálculos Automáticos**: Margem, impostos, frete
- **Histórico de Preços**: Rastreamento de alterações
- **Reajustes**: Controle de percentuais de reajuste

### 4. Controle de Estoque

- **Saldos por Filial**: Controle individualizado
- **Localização**: Posição física no estoque
- **Movimentações**: Integração com entradas e saídas

## Estrutura dos Dados

### Modelo Produtos

```python
class Produtos(models.Model):
    # Identificação
    prod_empr = models.CharField(max_length=50)  # Empresa
    prod_codi = models.CharField(max_length=50, primary_key=True)  # Código único
    prod_nome = models.CharField(max_length=255)  # Nome do produto

    # Classificação
    prod_unme = models.ForeignKey(UnidadeMedida)  # Unidade de medida
    prod_grup = models.ForeignKey(GrupoProduto)  # Grupo
    prod_fami = models.ForeignKey(FamiliaProduto)  # Família
    prod_marc = models.ForeignKey(Marca)  # Marca

    # Detalhes
    prod_loca = models.CharField(max_length=255)  # Localização
    prod_ncm = models.CharField(max_length=10)  # NCM
    prod_coba = models.CharField(max_length=50)  # Código de barras
    prod_foto = models.BinaryField()  # Foto do produto
```

### Modelo Tabelaprecos

```python
class Tabelaprecos(models.Model):
    # Identificação
    tabe_empr = models.IntegerField()  # Empresa
    tabe_fili = models.IntegerField()  # Filial
    tabe_prod = models.CharField(max_length=60)  # Produto

    # Preços
    tabe_prco = models.DecimalField(max_digits=15, decimal_places=2)  # Preço base
    tabe_avis = models.DecimalField(max_digits=15, decimal_places=2)  # Preço à vista
    tabe_apra = models.DecimalField(max_digits=15, decimal_places=2)  # Preço a prazo
    tabe_vare = models.DecimalField(max_digits=15, decimal_places=2)  # Varejo

    # Custos e Impostos
    tabe_cust = models.DecimalField(max_digits=15, decimal_places=2)  # Custo
    tabe_cuge = models.DecimalField(max_digits=15, decimal_places=2)  # Custo geral
    tabe_icms = models.DecimalField(max_digits=15, decimal_places=2)  # ICMS
    tabe_vipi = models.DecimalField(max_digits=15, decimal_places=2)  # Valor IPI
    tabe_pipi = models.DecimalField(max_digits=15, decimal_places=2)  # % IPI
    tabe_valo_st = models.DecimalField(max_digits=15, decimal_places=2)  # Valor ST
    tabe_perc_st = models.DecimalField(max_digits=7, decimal_places=4)  # % ST

    # Outros
    tabe_marg = models.DecimalField(max_digits=15, decimal_places=4)  # Margem
    tabe_desc = models.DecimalField(max_digits=15, decimal_places=2)  # Desconto
    tabe_fret = models.DecimalField(max_digits=15, decimal_places=4)  # Frete
    tabe_desp = models.DecimalField(max_digits=15, decimal_places=4)  # Despesas
```

### Modelo SaldoProduto

```python
class SaldoProduto(models.Model):
    produto_codigo = models.ForeignKey(Produtos)  # Produto
    empresa = models.CharField(max_length=50)  # Empresa
    filial = models.CharField(max_length=50)  # Filial
    saldo_estoque = models.DecimalField(max_digits=10, decimal_places=2)  # Saldo
```

## Exemplos de Uso

### 1. Criar Novo Produto

```python
from Produtos.models import Produtos, GrupoProduto, UnidadeMedida, Marca

# Buscar dependências
grupo = GrupoProduto.objects.get(codigo=1)
unidade = UnidadeMedida.objects.get(unid_codi='UN')
marca = Marca.objects.get(codigo=1)

# Criar produto
produto = Produtos.objects.create(
    prod_empr='1',
    prod_codi='PROD001',
    prod_nome='Produto Exemplo',
    prod_unme=unidade,
    prod_grup=grupo,
    prod_marc=marca,
    prod_ncm='12345678',
    prod_loca='A1-B2-C3'
)
```

### 2. Definir Preços

```python
from Produtos.models import Tabelaprecos
from decimal import Decimal

# Criar tabela de preços
preco = Tabelaprecos.objects.create(
    tabe_empr=1,
    tabe_fili=1,
    tabe_prod='PROD001',
    tabe_prco=Decimal('100.00'),
    tabe_avis=Decimal('95.00'),
    tabe_apra=Decimal('105.00'),
    tabe_cust=Decimal('70.00'),
    tabe_marg=Decimal('30.00'),
    tabe_icms=Decimal('18.00')
)
```

### 3. Consultar Estoque

```python
from Produtos.models import SaldoProduto

# Saldo de um produto específico
saldo = SaldoProduto.objects.filter(
    produto_codigo='PROD001',
    empresa='1',
    filial='1'
).first()

print(f"Saldo: {saldo.saldo_estoque}")

# Produtos com estoque baixo
produtos_baixo_estoque = SaldoProduto.objects.filter(
    saldo_estoque__lt=10
)
```

### 4. Buscar por Categoria

```python
# Produtos de um grupo específico
produtos_grupo = Produtos.objects.filter(
    prod_grup__codigo=1
)

# Produtos de uma marca
produtos_marca = Produtos.objects.filter(
    prod_marc__nome__icontains='Nike'
)

# Produtos com preço em uma faixa
from django.db.models import Q
produtos_preco = Produtos.objects.filter(
    tabelaprecos__tabe_prco__range=(50, 200)
).distinct()
```

### 5. Relatórios de Preços

```python
# Histórico de alterações de preço
from Produtos.models import Tabelaprecoshist

historico = Tabelaprecoshist.objects.filter(
    tabe_prod='PROD001'
).order_by('-tabe_data_hora')

# Produtos com maior margem
from django.db.models import F
produtos_margem = Tabelaprecos.objects.annotate(
    margem_calculada=F('tabe_prco') - F('tabe_cust')
).order_by('-margem_calculada')
```

## API Endpoints

### Produtos

```
GET /api/{licenca}/produtos/produtos/
POST /api/{licenca}/produtos/produtos/
GET /api/{licenca}/produtos/produtos/{codigo}/
PUT /api/{licenca}/produtos/produtos/{codigo}/
PATCH /api/{licenca}/produtos/produtos/{codigo}/
DELETE /api/{licenca}/produtos/produtos/{codigo}/
```

### Grupos de Produtos

```
GET /api/{licenca}/produtos/grupos/
POST /api/{licenca}/produtos/grupos/
```

### Tabela de Preços

```
GET /api/{licenca}/produtos/precos/
POST /api/{licenca}/produtos/precos/
GET /api/{licenca}/produtos/precos/{id}/
PUT /api/{licenca}/produtos/precos/{id}/
```

### Saldos

```
GET /api/{licenca}/produtos/saldos/
GET /api/{licenca}/produtos/saldos/{produto_codigo}/
```

### Filtros Disponíveis

#### Produtos

- `prod_empr`: Filtrar por empresa
- `prod_grup`: Filtrar por grupo
- `prod_marc`: Filtrar por marca
- `prod_nome`: Buscar por nome (contém)
- `search`: Busca geral em nome e código

#### Preços

- `tabe_empr`: Filtrar por empresa
- `tabe_fili`: Filtrar por filial
- `tabe_prod`: Filtrar por produto
- `preco_min`: Preço mínimo
- `preco_max`: Preço máximo

### Exemplo de Requisições

```
GET /api/empresa123/produtos/produtos/?prod_grup=1&search=notebook
GET /api/empresa123/produtos/precos/?tabe_empr=1&preco_min=100&preco_max=500
GET /api/empresa123/produtos/saldos/?empresa=1&saldo_min=10
```

## Considerações Técnicas

### Banco de Dados

- **Tabelas**: `produtos`, `tabelaprecos`, `saldosprodutos`, `gruposprodutos`, etc.
- **Managed**: False (tabelas não gerenciadas pelo Django)
- **Chaves Compostas**: Empresa + Filial + Produto para preços

### Índices Recomendados

```sql
-- Produtos
CREATE INDEX idx_produtos_empresa ON produtos (prod_empr);
CREATE INDEX idx_produtos_grupo ON produtos (prod_grup);
CREATE INDEX idx_produtos_marca ON produtos (prod_marc);
CREATE INDEX idx_produtos_nome ON produtos (prod_nome);
CREATE INDEX idx_produtos_ncm ON produtos (prod_ncm);

-- Preços
CREATE INDEX idx_precos_produto ON tabelaprecos (tabe_prod);
CREATE INDEX idx_precos_empresa_filial ON tabelaprecos (tabe_empr, tabe_fili);
CREATE INDEX idx_precos_valor ON tabelaprecos (tabe_prco);

-- Saldos
CREATE INDEX idx_saldos_produto ON saldosprodutos (sapr_prod);
CREATE INDEX idx_saldos_empresa_filial ON saldosprodutos (sapr_empr, sapr_fili);
CREATE INDEX idx_saldos_estoque ON saldosprodutos (sapr_sald);
```

### Validações Recomendadas

```python
from django.core.exceptions import ValidationError
from decimal import Decimal

def clean(self):
    # Validar preços
    if self.tabe_prco and self.tabe_cust:
        if self.tabe_prco < self.tabe_cust:
            raise ValidationError('Preço não pode ser menor que o custo')

    # Validar margem
    if self.tabe_marg and (self.tabe_marg < 0 or self.tabe_marg > 100):
        raise ValidationError('Margem deve estar entre 0% e 100%')

    # Validar NCM
    if self.prod_ncm and len(self.prod_ncm) != 8:
        raise ValidationError('NCM deve ter 8 dígitos')
```

### Performance

```python
# Usar select_related para relacionamentos
produtos = Produtos.objects.select_related(
    'prod_unme', 'prod_grup', 'prod_marc', 'prod_fami'
).all()

# Prefetch para relacionamentos reversos
grupos = GrupoProduto.objects.prefetch_related('produtos').all()

# Paginação para listas grandes
from django.core.paginator import Paginator
paginator = Paginator(produtos, 50)
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Pedidos
class ItemPedido(models.Model):
    produto = models.ForeignKey(
        'Produtos.Produtos',
        on_delete=models.PROTECT
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=15, decimal_places=2)

# Estoque
class MovimentoEstoque(models.Model):
    produto = models.ForeignKey(
        'Produtos.Produtos',
        on_delete=models.PROTECT
    )
    tipo = models.CharField(max_length=1, choices=[('E', 'Entrada'), ('S', 'Saída')])
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
```

### Consultas com Relacionamentos

```python
# Produtos mais vendidos
from django.db.models import Sum
produtos_vendidos = Produtos.objects.annotate(
    total_vendido=Sum('itempedido__quantidade')
).order_by('-total_vendido')

# Valor total do estoque
from django.db.models import F
valor_estoque = SaldoProduto.objects.aggregate(
    total=Sum(F('saldo_estoque') * F('produto_codigo__tabelaprecos__tabe_prco'))
)
```

## Troubleshooting

### Problemas Comuns

1. **Erro de chave duplicada em preços**

   - Verificar combinação empresa + filial + produto
   - Usar `update_or_create()` para evitar duplicatas

2. **Imagens não carregando**

   - Verificar configuração de MEDIA_URL
   - Implementar método para conversão de BinaryField

3. **Performance lenta em consultas**

   - Criar índices apropriados
   - Usar `select_related()` e `prefetch_related()`
   - Implementar cache para consultas frequentes

4. **Problemas de precisão decimal**

   - Usar `Decimal` ao invés de `float`
   - Configurar `DECIMAL_PLACES` adequadamente

5. **Sincronização de estoque**
   - Implementar triggers no banco
   - Usar transações atômicas
   - Validar movimentações

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'Produtos': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Comandos de Manutenção

```python
# management/commands/atualizar_precos.py
from django.core.management.base import BaseCommand
from Produtos.models import Tabelaprecos

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Lógica para atualização em lote de preços
        pass

# management/commands/sincronizar_estoque.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Lógica para sincronização de estoque
        pass
```

### SQL: CRIAÇÃO DA VIEW NO BANCO

CREATE OR REPLACE VIEW produtos_detalhados AS
SELECT
prod.prod_codi AS codigo,
prod.prod_nome AS nome,
prod.prod_unme AS unidade,
prod.prod_grup AS grupo_id,
grup.grup_desc AS grupo_nome,
prod.prod_marc AS marca_id,
marc.marc_nome AS marca_nome,
tabe.tabe_cuge AS custo,
tabe.tabe_avis AS preco_vista,
tabe.tabe_apra AS preco_prazo,
sald.sapr_sald AS saldo,
prod.prod_foto AS foto,
prod.prod_peso_brut AS peso_bruto,
prod.prod_peso_liqu AS peso_liquido,
sald.sapr_empr AS empresa,
sald.sapr_fili AS filial,
COALESCE(tabe.tabe_cuge, 0) _ COALESCE(sald.sapr_sald, 0) AS valor_total_estoque,
COALESCE(tabe.tabe_avis, 0) _ COALESCE(sald.sapr_sald, 0) AS valor_total_venda_vista,
COALESCE(tabe.tabe_apra, 0) \* COALESCE(sald.sapr_sald, 0) AS valor_total_venda_prazo
FROM produtos prod
LEFT JOIN gruposprodutos grup ON prod.prod_grup = grup.grup_codi
LEFT JOIN marca marc ON prod.prod_marc = marc.marc_codi
LEFT JOIN tabelaprecos tabe ON prod.prod_codi = tabe.tabe_prod AND prod.prod_empr = tabe.tabe_empr
LEFT JOIN saldosprodutos sald ON prod.prod_codi = sald.sapr_prod;
