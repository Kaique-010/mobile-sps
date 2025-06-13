# App Entidades

Este app gerencia o cadastro de entidades (clientes, fornecedores, vendedores, funcionários e outros) do sistema.

## Funcionalidades

### 1. Gestão de Entidades

- **Cadastro Completo**: Informações pessoais e empresariais
- **Múltiplos Tipos**: Suporte a diferentes tipos de entidades
- **Documentos**: CPF/CNPJ e Inscrição Estadual
- **Endereço Completo**: CEP, endereço, número, cidade e estado
- **Contatos**: Telefone, celular e email

### 2. Tipos de Entidades Suportados

- **FO - FORNECEDOR**: Empresas ou pessoas que fornecem produtos/serviços
- **CL - CLIENTE**: Clientes que compram produtos/serviços
- **AM - AMBOS**: Entidades que são tanto clientes quanto fornecedores
- **OU - OUTROS**: Outras categorias de entidades
- **VE - VENDEDOR**: Vendedores e representantes
- **FU - FUNCIONÁRIOS**: Funcionários da empresa

### 3. Validações e Controles

- **Chave Única**: Cada entidade possui um código único (enti_clie)
- **Empresa**: Vinculação obrigatória com empresa (enti_empr)
- **Documentos Opcionais**: CPF/CNPJ conforme necessidade
- **Contatos Flexíveis**: Campos de contato opcionais

## Estrutura dos Dados

### Modelo Entidades

```python
class Entidades(models.Model):
    # Identificação
    enti_empr = models.IntegerField()  # ID da empresa
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)  # Código único
    enti_nome = models.CharField(max_length=100)  # Nome/Razão Social
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES)  # Tipo
    enti_fant = models.CharField(max_length=100)  # Nome fantasia
    
    # Documentos
    enti_cpf = models.CharField(max_length=11)  # CPF
    enti_cnpj = models.CharField(max_length=14)  # CNPJ
    enti_insc_esta = models.CharField(max_length=11)  # Inscrição Estadual
    
    # Endereço
    enti_cep = models.CharField(max_length=8)  # CEP
    enti_ende = models.CharField(max_length=60)  # Endereço
    enti_nume = models.CharField(max_length=4)  # Número
    enti_cida = models.CharField(max_length=60)  # Cidade
    enti_esta = models.CharField(max_length=2)  # Estado (UF)
    
    # Contatos
    enti_fone = models.CharField(max_length=14)  # Telefone
    enti_celu = models.CharField(max_length=15)  # Celular
    enti_emai = models.CharField(max_length=60)  # Email
```

## Exemplos de Uso

### 1. Criar Nova Entidade

```python
from Entidades.models import Entidades

# Criar um novo cliente
cliente = Entidades.objects.create(
    enti_empr=1,
    enti_clie=1001,
    enti_nome='João Silva',
    enti_tipo_enti='CL',
    enti_cpf='12345678901',
    enti_cep='12345678',
    enti_ende='Rua das Flores',
    enti_nume='123',
    enti_cida='São Paulo',
    enti_esta='SP',
    enti_fone='1133334444',
    enti_emai='joao@email.com'
)
```

### 2. Buscar Entidades por Tipo

```python
# Buscar todos os clientes
clientes = Entidades.objects.filter(enti_tipo_enti='CL')

# Buscar todos os fornecedores
fornecedores = Entidades.objects.filter(enti_tipo_enti='FO')

# Buscar entidades que são ambos (cliente e fornecedor)
ambos = Entidades.objects.filter(enti_tipo_enti='AM')
```

### 3. Buscar por Empresa

```python
# Buscar todas as entidades de uma empresa específica
entidades_empresa = Entidades.objects.filter(enti_empr=1)

# Contar entidades por empresa
from django.db.models import Count
contagem = Entidades.objects.values('enti_empr').annotate(
    total=Count('enti_clie')
)
```

### 4. Filtros Avançados

```python
# Buscar por nome (case-insensitive)
entidades = Entidades.objects.filter(
    enti_nome__icontains='silva'
)

# Buscar por cidade
entidades_sp = Entidades.objects.filter(
    enti_cida__iexact='São Paulo'
)

# Buscar entidades com email
com_email = Entidades.objects.filter(
    enti_emai__isnull=False
).exclude(enti_emai='')
```

## API Endpoints

### Listar Entidades
```
GET /api/{licenca}/entidades/entidades/
```

### Criar Entidade
```
POST /api/{licenca}/entidades/entidades/
```

### Obter Entidade Específica
```
GET /api/{licenca}/entidades/entidades/{id}/
```

### Atualizar Entidade
```
PUT /api/{licenca}/entidades/entidades/{id}/
PATCH /api/{licenca}/entidades/entidades/{id}/
```

### Excluir Entidade
```
DELETE /api/{licenca}/entidades/entidades/{id}/
```

### Filtros Disponíveis

- `enti_empr`: Filtrar por empresa
- `enti_tipo_enti`: Filtrar por tipo de entidade
- `enti_nome`: Buscar por nome (contém)
- `enti_cida`: Filtrar por cidade
- `enti_esta`: Filtrar por estado
- `search`: Busca geral em nome e fantasia

### Exemplo de Requisição
```
GET /api/empresa123/entidades/entidades/?enti_tipo_enti=CL&enti_esta=SP&search=silva
```

## Considerações Técnicas

### Banco de Dados
- **Tabela**: `entidades`
- **Managed**: False (tabela não gerenciada pelo Django)
- **Chave Primária**: `enti_clie` (BigIntegerField)

### Índices Recomendados
```sql
-- Índices para performance
CREATE INDEX idx_entidades_empresa ON entidades (enti_empr);
CREATE INDEX idx_entidades_tipo ON entidades (enti_tipo_enti);
CREATE INDEX idx_entidades_nome ON entidades (enti_nome);
CREATE INDEX idx_entidades_cidade_estado ON entidades (enti_cida, enti_esta);
CREATE INDEX idx_entidades_cpf ON entidades (enti_cpf) WHERE enti_cpf IS NOT NULL;
CREATE INDEX idx_entidades_cnpj ON entidades (enti_cnpj) WHERE enti_cnpj IS NOT NULL;
```

### Validações Recomendadas

```python
# Adicionar validações customizadas
from django.core.exceptions import ValidationError

def clean(self):
    # Validar CPF ou CNPJ
    if not self.enti_cpf and not self.enti_cnpj:
        if self.enti_tipo_enti in ['CL', 'FO', 'AM']:
            raise ValidationError('CPF ou CNPJ é obrigatório para este tipo de entidade')
    
    # Validar formato do email
    if self.enti_emai:
        from django.core.validators import validate_email
        validate_email(self.enti_emai)
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Em outros models, referenciar entidades
class Pedido(models.Model):
    cliente = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        related_name='pedidos'
    )

class ContaReceber(models.Model):
    cliente = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        limit_choices_to={'enti_tipo_enti__in': ['CL', 'AM']}
    )
```

### Consultas com Relacionamentos

```python
# Buscar pedidos de um cliente
cliente = Entidades.objects.get(enti_clie=1001)
pedidos = cliente.pedidos.all()

# Buscar clientes com pedidos
clientes_com_pedidos = Entidades.objects.filter(
    enti_tipo_enti='CL',
    pedidos__isnull=False
).distinct()
```

## Troubleshooting

### Problemas Comuns

1. **Erro de chave duplicada**
   - Verificar se `enti_clie` é único
   - Usar `get_or_create()` para evitar duplicatas

2. **Problemas de encoding**
   - Verificar charset da tabela no banco
   - Usar UTF-8 para caracteres especiais

3. **Performance lenta**
   - Criar índices apropriados
   - Usar `select_related()` em consultas com relacionamentos
   - Paginar resultados grandes

4. **Validação de documentos**
   - Implementar validadores para CPF/CNPJ
   - Verificar duplicatas de documentos

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'Entidades': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```