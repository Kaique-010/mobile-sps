# Sistema de Parâmetros Administrativos

Este módulo implementa um sistema completo de gerenciamento de parâmetros administrativos para controlar o comportamento de diferentes módulos do sistema (Estoque, Pedidos, Orçamentos).

## Funcionalidades

- **Gestão Centralizada**: Todos os parâmetros em um local único
- **Multi-empresa/Filial**: Parâmetros específicos por empresa e filial
- **Módulos Específicos**: Parâmetros organizados por módulo (Estoque, Pedidos, Orçamentos)
- **API REST**: Interface completa para CRUD de parâmetros
- **Decoradores**: Aplicação automática de parâmetros em ViewSets
- **Utils Organizados**: Funções específicas para cada módulo
- **Permissões**: Controle de acesso baseado em permissões
- **Logs**: Auditoria completa das operações

## Estrutura do Projeto

```
parametros_admin/
├── __init__.py
├── apps.py              # Configuração do app
├── models.py            # Modelos de dados
├── serializers.py       # Serializers da API
├── views.py             # Views da API
├── urls.py              # URLs da API
├── permissions.py       # Permissões customizadas
├── utils_estoque.py     # Utils para parâmetros de estoque
├── utils_pedidos.py     # Utils para parâmetros de pedidos
├── utils_orcamentos.py  # Utils para parâmetros de orçamentos
├── decorators.py        # Decoradores para ViewSets
├── sql_parametros.sql   # Script SQL para popular parâmetros
├── migrations/          # Migrações do banco
├── README_PARAMETROS.md # Esta documentação
└── GUIA_USO_DECORADORES.md # Guia de uso dos decoradores
```

## Parâmetros Implementados

### Parâmetros de Estoque

- `entrada_automatica_estoque`: Permite entrada automática de estoque ao retornar um pedido de venda
- `saida_automatica_estoque`: Permite saída automática de estoque ao gravar um pedido de venda
- `permitir_estoque_negativo`: Permite que o estoque fique negativo
- `alerta_estoque_minimo`: Exibe alertas de estoque mínimo
- `calculo_automatico_custo`: Calcula custo médio automaticamente
- `pedido_volta_estoque`: Retorna produtos ao estoque quando pedido é cancelado

### Parâmetros de Pedidos

- `usar_preco_prazo`: Utiliza preço a prazo por padrão
- `usar_ultimo_preco`: Utiliza último preço aplicado para o cliente
- `desconto_pedido`: Permite aplicar desconto em pedidos
- `validar_estoque_pedido`: Valida disponibilidade de estoque
- `calcular_frete_automatico`: Calcula frete automaticamente

### Parâmetros de Orçamentos

- `baixa_estoque_orcamento`: Permite baixa de estoque em orçamentos
- `usar_preco_prazo`: Utiliza preço a prazo em orçamentos
- `usar_ultimo_preco`: Utiliza último preço aplicado
- `desconto_orcamento`: Permite desconto em orçamentos
- `validade_orcamento_dias`: Quantidade de dias de validade
- `conversao_automatica_pedido`: Permite conversão automática para pedido

## Como Usar

### 1. Usando Decoradores (Recomendado)

```python
from parametros_admin.decorators import (
    parametros_estoque_completo,
    parametros_pedidos_completo,
    parametros_orcamentos_completo
)
from rest_framework.viewsets import ModelViewSet

class EntradaEstoqueViewSet(ModelViewSet):

    @parametros_estoque_completo(operacao='entrada')
    def create(self, request, *args, **kwargs):
        # Parâmetros aplicados automaticamente
        # request.parametros_estoque contém todos os parâmetros
        return super().create(request, *args, **kwargs)

class PedidosViewSet(ModelViewSet):

    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        # Validações automáticas de estoque e preços
        return super().create(request, *args, **kwargs)
```

### 2. Usando Utils Diretamente

```python
from parametros_admin.utils_estoque import (
    verificar_entrada_automatica,
    processar_entrada_estoque
)
from parametros_admin.utils_pedidos import (
    obter_preco_produto,
    validar_desconto_pedido
)
from parametros_admin.utils_orcamentos import (
    calcular_data_validade_orcamento,
    converter_orcamento_para_pedido
)
```

### 3. Populando os Parâmetros

Execute o script SQL para criar os parâmetros padrão:

```bash
# MySQL
mysql -u usuario -p database_name < parametros_admin/sql_parametros.sql

# PostgreSQL
psql -U usuario -d database_name -f parametros_admin/sql_parametros.sql
```

### 4. Verificar Parâmetros Específicos

```python
def minha_funcao(request):
    empresa_id = 1
    filial_id = 1

    # Verificar parâmetros de estoque
    from parametros_admin.utils_estoque import verificar_entrada_automatica

    if verificar_entrada_automatica(empresa_id, filial_id, request):
        # Processar entrada automática
        pass

    # Obter preço de produto
    from parametros_admin.utils_pedidos import obter_preco_produto

    preco = obter_preco_produto(
        'PROD001', empresa_id, filial_id, request, 'prazo'
    )
```

## API Endpoints

### Parâmetros do Sistema

```
GET    /api/parametros/                    # Listar parâmetros
POST   /api/parametros/                    # Criar parâmetro
GET    /api/parametros/{id}/               # Obter parâmetro
PUT    /api/parametros/{id}/               # Atualizar parâmetro
DELETE /api/parametros/{id}/               # Deletar parâmetro
```

### Módulos

```
GET    /api/parametros/modulos/            # Listar módulos
GET    /api/parametros/modulos/{id}/       # Obter módulo
```

### Endpoints Específicos

```
GET    /api/parametros/por-empresa/{empresa_id}/{filial_id}/
GET    /api/parametros/por-modulo/{modulo_id}/
POST   /api/parametros/aplicar-estoque/
POST   /api/parametros/aplicar-pedidos/
POST   /api/parametros/aplicar-orcamentos/
```

## Modelos de Dados

### ParametroSistema

```python
class ParametroSistema(models.Model):
    para_codi = models.AutoField(primary_key=True)
    para_empr = models.IntegerField()  # Empresa
    para_fili = models.IntegerField()  # Filial
    para_modu = models.ForeignKey(Modulo)  # Módulo
    para_nome = models.CharField(max_length=100)  # Nome do parâmetro
    para_valo = models.TextField()  # Valor
    para_desc = models.TextField()  # Descrição
    para_ativ = models.BooleanField(default=True)  # Ativo
    para_tipo = models.CharField(max_length=20)  # Tipo (BOOLEAN, INTEGER, etc.)
    para_obri = models.BooleanField(default=False)  # Obrigatório
    para_cria = models.DateTimeField(auto_now_add=True)
    para_alte = models.DateTimeField(auto_now=True)
```

### Modulo

```python
class Modulo(models.Model):
    modu_codi = models.AutoField(primary_key=True)
    modu_nome = models.CharField(max_length=100)
    modu_desc = models.TextField()
    modu_ativ = models.BooleanField(default=True)
```

## Permissões

O sistema implementa permissões específicas:

- `parametros_admin.view_parametrosistema`: Visualizar parâmetros
- `parametros_admin.add_parametrosistema`: Adicionar parâmetros
- `parametros_admin.change_parametrosistema`: Alterar parâmetros
- `parametros_admin.delete_parametrosistema`: Deletar parâmetros
- `parametros_admin.view_estoque_parametros`: Parâmetros de estoque
- `parametros_admin.view_pedidos_parametros`: Parâmetros de pedidos
- `parametros_admin.view_orcamentos_parametros`: Parâmetros de orçamentos

## Logs e Auditoria

Todas as operações são registradas:

```python
# Configurar no settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'parametros_admin.log',
        },
    },
    'loggers': {
        'parametros_admin': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Exemplos de Uso

### Entrada de Estoque com Parâmetros

```python
from parametros_admin.decorators import parametros_estoque_completo

class EntradaEstoqueViewSet(ModelViewSet):

    @parametros_estoque_completo(operacao='entrada')
    def create(self, request, *args, **kwargs):
        # Verificações automáticas:
        # - Entrada automática habilitada?
        # - Cálculo de custo automático?
        # - Alertas de estoque mínimo?

        dados = request.data

        # Processar entrada usando utils
        from parametros_admin.utils_estoque import processar_entrada_estoque

        resultado = processar_entrada_estoque(dados, request)

        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'erro': resultado['erro']},
                status=status.HTTP_400_BAD_REQUEST
            )
```

### Pedido com Validação de Estoque

```python
from parametros_admin.decorators import parametros_pedidos_completo

class PedidosViewSet(ModelViewSet):

    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        # Validações automáticas:
        # - Estoque disponível?
        # - Preços corretos aplicados?
        # - Descontos permitidos?

        # Os parâmetros estão em request.parametros_pedidos
        parametros = request.parametros_pedidos

        if parametros['validar_estoque_pedido']['ativo']:
            # Validação já foi feita pelo decorator
            pass

        return super().create(request, *args, **kwargs)
```

### Orçamento com Data de Validade

```python
from parametros_admin.decorators import parametros_orcamentos_completo

class OrcamentosViewSet(ModelViewSet):

    @parametros_orcamentos_completo
    def create(self, request, *args, **kwargs):
        # Data de validade calculada automaticamente
        # request.data['data_validade'] já foi preenchida

        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def converter_para_pedido(self, request, pk=None):
        from parametros_admin.utils_orcamentos import converter_orcamento_para_pedido

        resultado = converter_orcamento_para_pedido(pk, request)

        if resultado['conversao_ok']:
            return Response(resultado)
        else:
            return Response(
                {'erro': resultado['erro']},
                status=status.HTTP_400_BAD_REQUEST
            )
```

## Integração com Sistema Existente

### 1. Adicionar ao INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... outros apps
    'parametros_admin',
]
```

### 2. Incluir URLs

```python
# core/urls.py
urlpatterns = [
    # ... outras URLs
    path('api/parametros/', include('parametros_admin.urls')),
]
```

### 3. Executar Migrações

```bash
python manage.py makemigrations parametros_admin
python manage.py migrate
```

### 4. Popular Parâmetros

```bash
mysql -u usuario -p database_name < parametros_admin/sql_parametros.sql
```

## Manutenção

### Adicionar Novos Parâmetros

1. Adicione no script SQL
2. Crie funções nos utils correspondentes
3. Atualize os decoradores se necessário
4. Documente o novo parâmetro

### Modificar Parâmetros Existentes

1. Atualize via API ou Django Admin
2. Teste as funcionalidades afetadas
3. Atualize documentação se necessário

## Segurança

- **Validação**: Todos os dados são validados antes de serem salvos
- **Permissões**: Acesso controlado por permissões específicas
- **Logs**: Todas as operações são registradas
- **Sanitização**: Valores são sanitizados antes do uso
- **Multi-tenant**: Isolamento por empresa/filial

## Performance

- **Cache**: Parâmetros são cacheados para melhor performance
- **Índices**: Índices otimizados para consultas frequentes
- **Lazy Loading**: Carregamento sob demanda
- **Bulk Operations**: Operações em lote quando possível

## Troubleshooting

### Parâmetro não encontrado

- Verifique se o parâmetro existe na base
- Confirme empresa_id e filial_id corretos
- Verifique se o módulo está ativo

### Permissão negada

- Confirme permissões do usuário
- Verifique configuração de grupos
- Teste com usuário admin

### Erro de validação

- Verifique tipos de dados
- Confirme valores obrigatórios
- Teste com dados mínimos

Para mais detalhes sobre o uso dos decoradores, consulte o arquivo `GUIA_USO_DECORADORES.md`.

#popular os parametros

# Popular todos os parâmetros

python manage.py populate_parametros

# Listar parâmetros existentes

python manage.py populate_parametros --listar

# Popular para empresa/filial específica

python manage.py populate_parametros --empresa 1 --filial 1

# Listar parâmetros por empresa/filial

python manage.py populate_parametros --empresa 1 --filial 1 --listar

# Atualizar parâmetro específico

python manage.py populate_parametros --empresa 1 --filial 1 --parametro 'nome_parametro' --valor 'novo_valor'

# Desativar módulo para empresa/filial

python manage.py populate_parametros --empresa 1 --filial 1 --desativar 'nome_modulo'
