# Guia de Uso dos Decoradores de Parâmetros

Este guia explica como usar os decoradores criados para facilitar a aplicação de parâmetros administrativos nas ViewSets.

## Estrutura Organizada

A nova estrutura organiza os utils dentro do app `parametros_admin`:

```
parametros_admin/
├── utils_estoque.py      # Parâmetros de estoque
├── utils_pedidos.py      # Parâmetros de pedidos  
├── utils_orcamentos.py   # Parâmetros de orçamentos
├── decorators.py         # Decoradores para ViewSets
└── sql_parametros.sql    # Script para popular parâmetros
```

## Decoradores Disponíveis

### 1. Decoradores Simples

#### `@aplicar_parametros_estoque(operacao='entrada')`
Aplica parâmetros de estoque automaticamente.

**Parâmetros:**
- `operacao`: 'entrada', 'saida' ou 'verificacao'

**Exemplo:**
```python
from parametros_admin.decorators import aplicar_parametros_estoque
from rest_framework.viewsets import ModelViewSet

class EntradaEstoqueViewSet(ModelViewSet):
    
    @aplicar_parametros_estoque(operacao='entrada')
    def create(self, request, *args, **kwargs):
        # Os parâmetros estarão disponíveis em:
        # request.parametros_estoque
        # request.empresa_id
        # request.filial_id
        
        return super().create(request, *args, **kwargs)
    
    @aplicar_parametros_estoque(operacao='saida')
    def destroy(self, request, *args, **kwargs):
        # Verificações automáticas de estoque negativo
        return super().destroy(request, *args, **kwargs)
```

#### `@aplicar_parametros_pedidos`
Aplica parâmetros de pedidos automaticamente.

**Exemplo:**
```python
from parametros_admin.decorators import aplicar_parametros_pedidos

class PedidosViewSet(ModelViewSet):
    
    @aplicar_parametros_pedidos
    def create(self, request, *args, **kwargs):
        # Parâmetros disponíveis em request.parametros_pedidos
        # Validação automática de estoque se habilitada
        
        return super().create(request, *args, **kwargs)
```

#### `@aplicar_parametros_orcamentos`
Aplica parâmetros de orçamentos automaticamente.

**Exemplo:**
```python
from parametros_admin.decorators import aplicar_parametros_orcamentos

class OrcamentosViewSet(ModelViewSet):
    
    @aplicar_parametros_orcamentos
    def create(self, request, *args, **kwargs):
        # Data de validade calculada automaticamente
        # Verificação de baixa de estoque se habilitada
        
        return super().create(request, *args, **kwargs)
```

### 2. Decoradores Combinados (Recomendados)

#### `@parametros_estoque_completo(operacao='entrada')`
Combina verificação de permissões, log e aplicação de parâmetros.

**Exemplo:**
```python
from parametros_admin.decorators import parametros_estoque_completo

class EntradaEstoqueViewSet(ModelViewSet):
    
    @parametros_estoque_completo(operacao='entrada')
    def create(self, request, *args, **kwargs):
        # Todas as verificações aplicadas automaticamente:
        # - Permissões
        # - Log da operação
        # - Parâmetros de estoque
        # - Validações específicas
        
        return super().create(request, *args, **kwargs)
```

#### `@parametros_pedidos_completo`
Combina todas as verificações para pedidos.

**Exemplo:**
```python
from parametros_admin.decorators import parametros_pedidos_completo

class PedidosViewSet(ModelViewSet):
    
    @parametros_pedidos_completo
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @parametros_pedidos_completo
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
```

#### `@parametros_orcamentos_completo`
Combina todas as verificações para orçamentos.

**Exemplo:**
```python
from parametros_admin.decorators import parametros_orcamentos_completo

class OrcamentosViewSet(ModelViewSet):
    
    @parametros_orcamentos_completo
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
```

### 3. Decoradores Utilitários

#### `@verificar_permissoes_parametros(modulo_nome)`
Verifica permissões específicas do módulo.

#### `@log_operacao_parametros(operacao)`
Registra logs das operações.

#### `@validar_dados_obrigatorios(campos_obrigatorios)`
Valida campos obrigatórios na requisição.

**Exemplo:**
```python
from parametros_admin.decorators import (
    verificar_permissoes_parametros,
    log_operacao_parametros,
    validar_dados_obrigatorios
)

class CustomViewSet(ModelViewSet):
    
    @verificar_permissoes_parametros('estoque')
    @log_operacao_parametros('consulta_estoque')
    @validar_dados_obrigatorios(['produto_codigo', 'quantidade'])
    def custom_action(self, request, *args, **kwargs):
        # Sua lógica aqui
        pass
```

## Usando os Utils Diretamente

Se preferir usar as funções diretamente sem decoradores:

### Utils de Estoque
```python
from parametros_admin.utils_estoque import (
    obter_parametros_estoque,
    verificar_entrada_automatica,
    processar_entrada_estoque,
    verificar_estoque_disponivel
)

def minha_view(request):
    empresa_id = 1
    filial_id = 1
    
    # Obter todos os parâmetros
    parametros = obter_parametros_estoque(empresa_id, filial_id, request)
    
    # Verificar entrada automática
    if verificar_entrada_automatica(empresa_id, filial_id, request):
        # Processar entrada
        resultado = processar_entrada_estoque(dados_entrada, request)
```

### Utils de Pedidos
```python
from parametros_admin.utils_pedidos import (
    obter_preco_produto,
    validar_desconto_pedido,
    processar_pedido_completo
)

def processar_pedido(request):
    # Obter preço baseado nos parâmetros
    preco = obter_preco_produto(
        produto_codigo='PROD001',
        empresa_id=1,
        filial_id=1,
        request=request,
        tipo_preco='prazo'
    )
    
    # Validar desconto
    validar_desconto_pedido(10.0, 100.0, 1, 1, request)
```

### Utils de Orçamentos
```python
from parametros_admin.utils_orcamentos import (
    calcular_data_validade_orcamento,
    converter_orcamento_para_pedido,
    processar_orcamento_completo
)

def criar_orcamento(request):
    # Calcular validade
    data_validade = calcular_data_validade_orcamento(1, 1, request)
    
    # Processar orçamento completo
    resultado = processar_orcamento_completo(
        orcamento_data, itens_data, request
    )
```

## Dados Disponíveis nos Decoradores

Quando você usa os decoradores, os seguintes dados ficam disponíveis na `request`:

### Para Estoque
```python
# request.parametros_estoque
{
    'entrada_automatica_estoque': {'valor': 'true', 'ativo': True, 'existe': True},
    'saida_automatica_estoque': {'valor': 'true', 'ativo': True, 'existe': True},
    'permitir_estoque_negativo': {'valor': 'false', 'ativo': True, 'existe': True},
    # ... outros parâmetros
}

# request.empresa_id
# request.filial_id
```

### Para Pedidos
```python
# request.parametros_pedidos
{
    'usar_preco_prazo': {'valor': 'false', 'ativo': True, 'existe': True},
    'usar_ultimo_preco': {'valor': 'true', 'ativo': True, 'existe': True},
    'desconto_pedido': {'valor': 'true', 'ativo': True, 'existe': True},
    # ... outros parâmetros
}
```

### Para Orçamentos
```python
# request.parametros_orcamentos
{
    'baixa_estoque_orcamento': {'valor': 'false', 'ativo': True, 'existe': True},
    'validade_orcamento_dias': {'valor': '30', 'ativo': True, 'existe': True},
    'conversao_automatica_pedido': {'valor': 'true', 'ativo': True, 'existe': True},
    # ... outros parâmetros
}
```

## Resposta dos Decoradores

Os decoradores adicionam informações na resposta:

```json
{
    "data": {
        // ... seus dados normais
    },
    "parametros_aplicados": {
        "estoque": {
            "entrada_automatica_estoque": true,
            "saida_automatica_estoque": true,
            "permitir_estoque_negativo": false
        }
    }
}
```

## Tratamento de Erros

Os decoradores tratam automaticamente:

- **400 Bad Request**: Dados obrigatórios faltando, validações falharam
- **401 Unauthorized**: Usuário não autenticado
- **403 Forbidden**: Sem permissão para o módulo
- **500 Internal Server Error**: Erros internos

**Exemplo de resposta de erro:**
```json
{
    "erro": "Estoque insuficiente",
    "estoque_atual": 5.0,
    "quantidade_solicitada": 10
}
```

## Configuração de Logs

Os decoradores geram logs automáticos. Configure no `settings.py`:

```python
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

## Exemplo Completo de ViewSet

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from parametros_admin.decorators import (
    parametros_estoque_completo,
    parametros_pedidos_completo,
    validar_dados_obrigatorios
)
from .models import Produto
from .serializers import ProdutoSerializer

class ProdutoViewSet(ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    
    @parametros_estoque_completo(operacao='entrada')
    @validar_dados_obrigatorios(['quantidade', 'preco_custo'])
    @action(detail=True, methods=['post'])
    def entrada_estoque(self, request, pk=None):
        produto = self.get_object()
        quantidade = request.data['quantidade']
        preco_custo = request.data['preco_custo']
        
        # Os parâmetros já foram verificados pelo decorator
        # request.parametros_estoque contém todos os parâmetros
        
        # Sua lógica de entrada de estoque aqui
        
        return Response({'status': 'entrada processada'})
    
    @parametros_estoque_completo(operacao='saida')
    @action(detail=True, methods=['post'])
    def saida_estoque(self, request, pk=None):
        # Verificação automática de estoque negativo pelo decorator
        
        produto = self.get_object()
        quantidade = request.data.get('quantidade', 0)
        
        # Sua lógica de saída de estoque aqui
        
        return Response({'status': 'saída processada'})
    
    @parametros_pedidos_completo
    @action(detail=True, methods=['get'])
    def obter_preco_pedido(self, request, pk=None):
        produto = self.get_object()
        
        # Usar utils diretamente se necessário
        from parametros_admin.utils_pedidos import obter_preco_produto
        
        preco = obter_preco_produto(
            produto.codigo,
            request.empresa_id,
            request.filial_id,
            request,
            tipo_preco='prazo'
        )
        
        return Response({'preco': preco})
```

## Populando os Parâmetros

Após criar a estrutura, execute o script SQL:

```bash
# No seu banco de dados
mysql -u usuario -p database_name < parametros_admin/sql_parametros.sql

# Ou no PostgreSQL
psql -U usuario -d database_name -f parametros_admin/sql_parametros.sql
```

## Próximos Passos

1. Execute o script SQL para popular os parâmetros
2. Aplique os decoradores nas suas ViewSets existentes
3. Teste as funcionalidades
4. Configure logs se necessário
5. Ajuste permissões conforme sua necessidade

Esta estrutura organizada facilita a manutenção e uso dos parâmetros administrativos em todo o sistema.