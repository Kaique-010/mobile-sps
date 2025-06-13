# App Ordem de Serviço

O app **OrdemdeServico** gerencia ordens de serviço completas, incluindo peças, serviços, imagens e controle de status. É ideal para empresas de manutenção, assistência técnica e prestação de serviços.

## Funcionalidades Principais

### 📋 Gestão de Ordens
- Criação e controle de ordens de serviço
- Status de acompanhamento (Aberta → Finalizada)
- Tipos de serviço (Manutenção, Revisão, Upgrade)
- Controle de prioridade (Normal, Alerta, Urgente)
- Setorização por departamentos

### 🔧 Peças e Serviços
- Cadastro de peças utilizadas
- Registro de serviços executados
- Cálculo automático de totais
- Controle de quantidades e valores

### 📸 Documentação Visual
- Imagens antes do serviço
- Imagens durante execução
- Imagens após conclusão
- Geolocalização das imagens
- Comentários e observações

## Estrutura dos Modelos

### Status e Choices
```python
ORDEM_STATUS_CHOICES = (
    (0, "Aberta"),
    (1, "Orçamento gerado"),
    (2, "Aguardando Liberação"),
    (3, "Liberada"),
    (4, "Finalizada"),
    (5, "Reprovada"),
    (20, "Faturada_parcial"),
)

Ordem_Prioridade_Choices = (
    ("normal", "Normal"),
    ("alerta", "Alerta"),
    ("urgente", "Urgente")
)
```

### Modelo `Ordemservico`
```python
class Ordemservico(models.Model):
    orde_empr = models.IntegerField()
    orde_fili = models.IntegerField()
    orde_nume = models.IntegerField(primary_key=True)
    orde_tipo = models.CharField(max_length=20, choices=OrdensTipos)
    orde_data_aber = models.DateField(auto_now_add=True)
    orde_stat_orde = models.IntegerField(choices=ORDEM_STATUS_CHOICES)
    orde_prio = models.CharField(max_length=10, choices=Ordem_Prioridade_Choices)
    orde_tota = models.DecimalField(max_digits=15, decimal_places=4)
```

### Modelo `Ordemservicopecas`
```python
class Ordemservicopecas(models.Model):
    peca_empr = models.IntegerField()
    peca_fili = models.IntegerField()
    peca_orde = models.IntegerField()
    peca_codi = models.CharField(max_length=20)
    peca_quan = models.DecimalField(max_digits=15, decimal_places=4)
    peca_unit = models.DecimalField(max_digits=15, decimal_places=4)
    peca_tota = models.DecimalField(max_digits=15, decimal_places=4)
```

## Exemplos de Uso

### Criar Ordem de Serviço
```python
from OrdemdeServico.models import Ordemservico

orden = Ordemservico.objects.create(
    orde_empr=1,
    orde_fili=1,
    orde_tipo="1",  # Manutenção
    orde_prio="urgente",
    orde_prob="Problema no motor",
    orde_enti=123,  # Cliente
    orde_plac="ABC1234"
)
```

### Adicionar Peças
```python
from OrdemdeServico.models import Ordemservicopecas

peca = Ordemservicopecas.objects.create(
    peca_empr=1,
    peca_fili=1,
    peca_orde=orden.orde_nume,
    peca_codi="FILTRO001",
    peca_comp="Filtro de óleo",
    peca_quan=2,
    peca_unit=25.50,
    peca_tota=51.00
)
```

### Calcular Total da Ordem
```python
# Calcular total automaticamente
total = orden.calcular_total()
print(f"Total da ordem: R$ {total}")
```

## Endpoints da API

### Ordens de Serviço
```http
GET /api/ordens/
GET /api/ordens/{numero}/
POST /api/ordens/
PUT /api/ordens/{numero}/
```

**Filtros:**
- `?orde_stat_orde=0` - Por status
- `?orde_prio=urgente` - Por prioridade
- `?orde_enti=123` - Por cliente
- `?orde_data_aber__gte=2024-01-01` - Por data

### Peças e Serviços
```http
GET /api/ordens/{numero}/pecas/
POST /api/ordens/{numero}/pecas/
GET /api/ordens/{numero}/servicos/
```

## Integração com Outros Apps

### Entidades
- Clientes das ordens de serviço
- Dados de contato e endereço

### Produtos
- Peças utilizadas nos serviços
- Preços e especificações

### Contas a Receber
- Faturamento das ordens
- Controle de pagamentos

## Troubleshooting

### Problemas Comuns

**Total não calculado:**
```python
# Recalcular total
orden = Ordemservico.objects.get(orde_nume=123)
total = orden.calcular_total()
orden.save()
```

**Imagens não carregando:**
```python
# Verificar imagens da ordem
imagens = Ordemservicoimgantes.objects.filter(
    iman_orde=123
)
print(f"Total de imagens: {imagens.count()}")
```