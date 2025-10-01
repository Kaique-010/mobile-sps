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

-- Tabela: ordemservicoimgantes
CREATE TABLE ordemservicoimgantes (
iman_id SERIAL PRIMARY KEY,
iman_empr INTEGER NOT NULL,
iman_fili INTEGER NOT NULL,
iman_orde INTEGER NOT NULL,
iman_codi INTEGER NOT NULL,
iman_come TEXT,
iman_imag BYTEA,
iman_obse VARCHAR(255),
img_latitude DECIMAL(9,6),
img_longitude DECIMAL(9,6),
img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: ordemservicoimgdurante
CREATE TABLE ordemservicoimgdurante (
imdu_id SERIAL PRIMARY KEY,
imdu_empr INTEGER NOT NULL,
imdu_fili INTEGER NOT NULL,
imdu_orde INTEGER NOT NULL,
imdu_codi INTEGER NOT NULL,
imdu_come TEXT,
imdu_imag BYTEA,
imdu_obse VARCHAR(255),
img_latitude DECIMAL(9,6),
img_longitude DECIMAL(9,6),
img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: ordemservicoimgdepois
CREATE TABLE ordemservicoimgdepois (
imde_id SERIAL PRIMARY KEY,
imde_empr INTEGER NOT NULL,
imde_fili INTEGER NOT NULL,
imde_orde INTEGER NOT NULL,
imde_codi INTEGER NOT NULL,
imde_come TEXT,
imde_imag BYTEA,
imde_obse VARCHAR(255),
img_latitude DECIMAL(9,6),
img_longitude DECIMAL(9,6),
img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ordemservicoimgantes
DO $$
BEGIN
IF NOT EXISTS (
SELECT 1 FROM information_schema.columns
WHERE table_name='ordemservicoimgantes' AND column_name='img_latitude'
) THEN
ALTER TABLE ordemservicoimgantes ADD COLUMN img_latitude DECIMAL(9,6);
END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgantes' AND column_name='img_longitude'
    ) THEN
        ALTER TABLE ordemservicoimgantes ADD COLUMN img_longitude DECIMAL(9,6);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgantes' AND column_name='img_data'
    ) THEN
        ALTER TABLE ordemservicoimgantes ADD COLUMN img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

END$$;

-- ordemservicoimgdurante
DO $$
BEGIN
IF NOT EXISTS (
SELECT 1 FROM information_schema.columns
WHERE table_name='ordemservicoimgdurante' AND column_name='img_latitude'
) THEN
ALTER TABLE ordemservicoimgdurante ADD COLUMN img_latitude DECIMAL(9,6);
END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgdurante' AND column_name='img_longitude'
    ) THEN
        ALTER TABLE ordemservicoimgdurante ADD COLUMN img_longitude DECIMAL(9,6);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgdurante' AND column_name='img_data'
    ) THEN
        ALTER TABLE ordemservicoimgdurante ADD COLUMN img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

END$$;

-- ordemservicoimgdepois
DO $$
BEGIN
IF NOT EXISTS (
SELECT 1 FROM information_schema.columns
WHERE table_name='ordemservicoimgdepois' AND column_name='img_latitude'
) THEN
ALTER TABLE ordemservicoimgdepois ADD COLUMN img_latitude DECIMAL(9,6);
END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgdepois' AND column_name='img_longitude'
    ) THEN
        ALTER TABLE ordemservicoimgdepois ADD COLUMN img_longitude DECIMAL(9,6);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='ordemservicoimgdepois' AND column_name='img_data'
    ) THEN
        ALTER TABLE ordemservicoimgdepois ADD COLUMN img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;

END$$;

##Novos end points

- POST /ordens/{id}/avancar-setor/ - Avança ordem para próximo setor
- GET /ordens/{id}/proximos-setores/ - Lista setores disponíveis
- GET /ordens/{id}/historico-workflow/ - Histórico de movimentações

ENDPOINTS DISPONÍVEIS
ordemdeservico

GET
/api/{slug}/ordemdeservico/fase-setor/

GET
/api/{slug}/ordemdeservico/fase-setor/{osfs_codi}/

GET
/api/{slug}/ordemdeservico/financeiro/consultar-titulos/{orde_nume}/

POST
/api/{slug}/ordemdeservico/financeiro/gerar-titulos/

GET
/api/{slug}/ordemdeservico/financeiro/relatorio/

POST
/api/{slug}/ordemdeservico/financeiro/remover-titulos/

GET
/api/{slug}/ordemdeservico/historico-workflow/

POST
/api/{slug}/ordemdeservico/historico-workflow/

GET
/api/{slug}/ordemdeservico/historico-workflow/{id}/

GET
/api/{slug}/ordemdeservico/imagens-antes/

POST
/api/{slug}/ordemdeservico/imagens-antes/

GET
/api/{slug}/ordemdeservico/imagens-antes/{id}/

PUT
/api/{slug}/ordemdeservico/imagens-antes/{id}/

PATCH
/api/{slug}/ordemdeservico/imagens-antes/{id}/

DELETE
/api/{slug}/ordemdeservico/imagens-antes/{id}/

GET
/api/{slug}/ordemdeservico/imagens-depois/

POST
/api/{slug}/ordemdeservico/imagens-depois/

GET
/api/{slug}/ordemdeservico/imagens-depois/{id}/

PUT
/api/{slug}/ordemdeservico/imagens-depois/{id}/

PATCH
/api/{slug}/ordemdeservico/imagens-depois/{id}/

DELETE
/api/{slug}/ordemdeservico/imagens-depois/{id}/

GET
/api/{slug}/ordemdeservico/imagens-durante/

POST
/api/{slug}/ordemdeservico/imagens-durante/

GET
/api/{slug}/ordemdeservico/imagens-durante/{id}/

PUT
/api/{slug}/ordemdeservico/imagens-durante/{id}/

PATCH
/api/{slug}/ordemdeservico/imagens-durante/{id}/

DELETE
/api/{slug}/ordemdeservico/imagens-durante/{id}/

GET
/api/{slug}/ordemdeservico/ordens/

POST
/api/{slug}/ordemdeservico/ordens/

POST
/api/{slug}/ordemdeservico/ordens/{id}/avancar-setor/

GET
/api/{slug}/ordemdeservico/ordens/{id}/historico-workflow/

GET
/api/{slug}/ordemdeservico/ordens/{id}/proximos-setores/

GET
/api/{slug}/ordemdeservico/ordens/{id}/

PUT
/api/{slug}/ordemdeservico/ordens/{id}/

PATCH
/api/{slug}/ordemdeservico/ordens/{id}/

DELETE
/api/{slug}/ordemdeservico/ordens/{id}/

POST
/api/{slug}/ordemdeservico/ordens/{id}/atualizar_total/

GET
/api/{slug}/ordemdeservico/pecas/

POST
/api/{slug}/ordemdeservico/pecas/

GET
/api/{slug}/ordemdeservico/pecas/{id}/

PUT
/api/{slug}/ordemdeservico/pecas/{id}/

PATCH
/api/{slug}/ordemdeservico/pecas/{id}/

DELETE
/api/{slug}/ordemdeservico/pecas/{id}/

POST
/api/{slug}/ordemdeservico/pecas/update-lista/

GET
/api/{slug}/ordemdeservico/servicos/

POST
/api/{slug}/ordemdeservico/servicos/

GET
/api/{slug}/ordemdeservico/servicos/{id}/

PUT
/api/{slug}/ordemdeservico/servicos/{id}/

PATCH
/api/{slug}/ordemdeservico/servicos/{id}/

DELETE
/api/{slug}/ordemdeservico/servicos/{id}/

POST
/api/{slug}/ordemdeservico/servicos/update-lista/

GET
/api/{slug}/ordemdeservico/workflow-setor/

POST
/api/{slug}/ordemdeservico/workflow-setor/

GET
/api/{slug}/ordemdeservico/workflow-setor/{wkfl_id}/

PUT
/api/{slug}/ordemdeservico/workflow-setor/{wkfl_id}/

PATCH
/api/{slug}/ordemdeservico/workflow-setor/{wkfl_id}/

DELETE
/api/{slug}/ordemdeservico/workflow-setor/{wkfl_id}/
