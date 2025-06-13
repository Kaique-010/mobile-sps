# App Lista Casamento

O app **Lista Casamento** gerencia listas de presentes para casamentos, permitindo que noivas criem listas de produtos desejados e controlem o status de cada item.

## Funcionalidades Principais

### 💍 Gestão de Listas
- Criação de listas de casamento personalizadas
- Vinculação com dados da noiva
- Controle de status da lista
- Data do evento
- Usuário responsável

### 🎁 Controle de Itens
- Cadastro de produtos desejados
- Controle de quantidades
- Status de finalização por item
- Vinculação com pedidos
- Rastreamento de usuário

### 📊 Acompanhamento
- Status da lista (Aberta, Aguardando, Finalizada, Cancelada)
- Controle por empresa/filial
- Auditoria de alterações
- Relatórios de progresso

## Estrutura dos Modelos

### Status da Lista
```python
STATUS_CHOICES = [
    ('0', 'Aberta'),
    ('1', 'Aguardando cliente'),
    ('2', 'Finalizada'),
    ('3', 'Cancelada'),
]
```

### Modelo `ListaCasamento`
```python
class ListaCasamento(models.Model):
    list_empr = models.IntegerField('Empresa')
    list_fili = models.IntegerField('Filial')
    list_codi = models.AutoField('Número Lista', primary_key=True)
    list_nome = models.CharField('Nome da Lista', max_length=60)
    list_noiv = models.ForeignKey(Entidades, on_delete=models.CASCADE)
    list_data = models.DateField('Data')
    list_stat = models.CharField('Status', choices=STATUS_CHOICES)
    list_usua = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
```

**Campos principais:**
- `list_codi`: Número único da lista
- `list_nome`: Nome personalizado da lista
- `list_noiv`: Referência à noiva (Entidades)
- `list_data`: Data do casamento
- `list_stat`: Status atual da lista
- `list_usua`: Usuário responsável

### Modelo `ItensListaCasamento`
```python
class ItensListaCasamento(models.Model):
    item_empr = models.IntegerField()
    item_fili = models.IntegerField()
    item_list = models.IntegerField()
    item_item = models.IntegerField(primary_key=True)
    item_prod = models.CharField(max_length=60)
    item_quan = models.DecimalField(max_digits=10, decimal_places=2)
    item_fina = models.BooleanField(default=False)
    item_pedi = models.IntegerField()
```

**Campos principais:**
- `item_item`: Número do item na lista
- `item_prod`: Código do produto
- `item_quan`: Quantidade desejada
- `item_fina`: Item finalizado/comprado
- `item_pedi`: Número do pedido relacionado

## Exemplos de Uso

### Criar Lista de Casamento
```python
from listacasamento.models import ListaCasamento
from Entidades.models import Entidades
from Licencas.models import Usuarios
from datetime import date

# Buscar noiva
noiva = Entidades.objects.get(enti_codi=123)
usuario = Usuarios.objects.get(usua_codi=1)

# Criar lista
lista = ListaCasamento.objects.create(
    list_empr=1,
    list_fili=1,
    list_nome="Lista de Casamento - Maria & João",
    list_noiv=noiva,
    list_data=date(2024, 12, 15),
    list_stat='0',  # Aberta
    list_usua=usuario
)
```

### Adicionar Itens à Lista
```python
from listacasamento.models import ItensListaCasamento

# Adicionar item
item = ItensListaCasamento.objects.create(
    item_empr=1,
    item_fili=1,
    item_list=lista.list_codi,
    item_item=1,
    item_prod="JOGO_PANELAS_001",
    item_quan=1.00,
    item_fina=False,
    item_pedi=0,
    item_usua=1
)
```

### Finalizar Item
```python
# Marcar item como finalizado
item.item_fina = True
item.item_pedi = 12345  # Número do pedido
item.save()

print(f"Item {item.item_prod} finalizado!")
```

### Consultar Progresso da Lista
```python
# Verificar itens da lista
itens_total = lista.itens_lista.count()
itens_finalizados = lista.itens_lista.filter(item_fina=True).count()
progresso = (itens_finalizados / itens_total) * 100 if itens_total > 0 else 0

print(f"Progresso: {progresso:.1f}% ({itens_finalizados}/{itens_total})")
```

### Relatórios
```python
# Listas por status
listas_abertas = ListaCasamento.objects.filter(list_stat='0')
listas_finalizadas = ListaCasamento.objects.filter(list_stat='2')

# Itens mais solicitados
from django.db.models import Count
itens_populares = ItensListaCasamento.objects.values('item_prod').annotate(
    total=Count('item_prod')
).order_by('-total')[:10]
```

## Endpoints da API

### Listas de Casamento
```http
GET /api/listas-casamento/
GET /api/listas-casamento/{id}/
POST /api/listas-casamento/
PUT /api/listas-casamento/{id}/
DELETE /api/listas-casamento/{id}/
```

### Itens da Lista
```http
GET /api/listas-casamento/{id}/itens/
POST /api/listas-casamento/{id}/itens/
PUT /api/itens-lista/{id}/
DELETE /api/itens-lista/{id}/
```

**Filtros disponíveis:**
- `?list_stat=0` - Por status
- `?list_data__gte=2024-01-01` - Por data
- `?list_noiv=123` - Por noiva
- `?item_fina=false` - Itens não finalizados

**Exemplo de requisição:**
```json
POST /api/listas-casamento/
{
    "list_empr": 1,
    "list_fili": 1,
    "list_nome": "Lista Maria & João",
    "list_noiv": 123,
    "list_data": "2024-12-15",
    "list_stat": "0",
    "list_usua": 1
}
```

## Considerações Técnicas

### Banco de Dados
- Tabelas: `listacasamento`, `itenslistacasamento`
- Índices em campos de busca frequente
- Relacionamentos com Entidades e Usuarios
- Constraint de unicidade em itens

### Validações
- Data do casamento não pode ser no passado
- Quantidade deve ser positiva
- Produto deve existir no cadastro
- Status válido conforme choices

### Performance
- Índices em campos de filtro
- Paginação em listas grandes
- Cache de consultas frequentes

## Integração com Outros Apps

### Entidades
- Dados da noiva/cliente
- Informações de contato
- Endereço de entrega

### Produtos
- Catálogo de produtos disponíveis
- Preços e especificações
- Controle de estoque

### Pedidos
- Conversão de itens em pedidos
- Controle de vendas
- Faturamento

### Licenças
- Usuários responsáveis
- Controle de acesso
- Auditoria

## Troubleshooting

### Problemas Comuns

**Lista não aparece:**
```python
# Verificar se lista existe
try:
    lista = ListaCasamento.objects.get(list_codi=123)
    print(f"Lista encontrada: {lista.list_nome}")
except ListaCasamento.DoesNotExist:
    print("Lista não encontrada")
```

**Item duplicado:**
```python
# Verificar duplicatas
duplicatas = ItensListaCasamento.objects.filter(
    item_list=123,
    item_prod="PRODUTO_001"
).count()

if duplicatas > 1:
    print("Item duplicado encontrado")
```

**Progresso incorreto:**
```python
# Recalcular progresso
lista = ListaCasamento.objects.get(list_codi=123)
itens = lista.itens_lista
total = itens.count()
finalizados = itens.filter(item_fina=True).count()

print(f"Progresso real: {finalizados}/{total}")
```

### Logs de Debug
```python
import logging
logger = logging.getLogger('listacasamento')

# Log de criação
logger.info(f'Lista criada: {lista.list_codi} - {lista.list_nome}')

# Log de finalização
logger.info(f'Item finalizado: {item.item_prod} - Lista {item.item_list}')
```

### Comandos de Manutenção
```bash
# Listar listas abertas
python manage.py shell -c "from listacasamento.models import ListaCasamento; print(ListaCasamento.objects.filter(list_stat='0').count())"

# Verificar itens sem pedido
python manage.py shell -c "from listacasamento.models import ItensListaCasamento; print(ItensListaCasamento.objects.filter(item_fina=True, item_pedi=0).count())"

# Relatório de progresso
python manage.py shell -c "from listacasamento.models import *; [print(f'Lista {l.list_codi}: {l.itens_lista.filter(item_fina=True).count()}/{l.itens_lista.count()}') for l in ListaCasamento.objects.filter(list_stat='0')]"
```