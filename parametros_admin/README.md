# App Parâmetros Admin

O app **Parâmetros Admin** é responsável pelo gerenciamento de módulos, permissões e configurações do sistema. Ele controla quais módulos estão disponíveis para cada empresa/filial e gerencia parâmetros específicos.

## 🎯 Funcionalidades Principais

### 📋 Gestão de Módulos
- Cadastro de todos os módulos do sistema
- Controle de ativação/desativação de módulos
- Ordenação e ícones para interface
- Comando para popular módulos automaticamente

### 🔐 Sistema de Permissões
- Controle granular de módulos por empresa/filial
- Permissões específicas por usuário
- Migração automática do sistema de licenças
- Cache de permissões para performance

### ⚙️ Configurações
- Configurações de estoque por empresa/filial
- Configurações financeiras
- Parâmetros gerais do sistema
- Log de alterações

## 🚀 Como Usar

### 1. Popular Módulos do Sistema

Primeiro, execute o comando para popular todos os módulos:

```bash
python manage.py popular_modulos
```

Este comando irá:
- Criar/atualizar todos os módulos do sistema na tabela `modulomobile`
- Incluir todos os 27 módulos disponíveis
- Definir ícones e ordem de exibição

### 2. Popular Permissões Baseadas no licencas.json

Para migrar as permissões do sistema antigo:

```bash
python manage.py popular_modulos --popular-permissoes --banco casaa
```

Este comando irá:
- Ler o arquivo `licencas.json`
- Criar permissões na tabela `permissoesmodulosmobile`
- Liberar módulos para empresa 1, filial 1 (padrão)

### 3. Login com Novo Sistema

O login agora busca módulos da tabela ao invés do `licencas.json`:

```json
POST /api/casaa/licencas/login/
{
    "username": "usuario",
    "password": "senha",
    "docu": "12345678000195",
    "empresa_id": 1,
    "filial_id": 1
}
```

**Resposta:**
```json
{
    "access": "token...",
    "refresh": "token...",
    "usuario": {
        "username": "usuario",
        "usuario_id": 1,
        "empresa_id": 1,
        "filial_id": 1
    },
    "licenca": {
        "lice_id": 1,
        "lice_nome": "Licença Empresa"
    },
    "modulos": ["dashboards", "Produtos", "Pedidos", ...]
}
```

## 📊 Estrutura dos Modelos

### Modelo `Modulo`
```python
class Modulo(models.Model):
    modu_codi = models.AutoField(primary_key=True)
    modu_nome = models.CharField(max_length=50, unique=True)
    modu_desc = models.TextField()
    modu_ativ = models.BooleanField(default=True)
    modu_icone = models.CharField(max_length=50, blank=True)
    modu_ordem = models.IntegerField(default=0)
```

### Modelo `PermissaoModulo`
```python
class PermissaoModulo(models.Model):
    perm_codi = models.AutoField(primary_key=True)
    perm_empr = models.IntegerField()
    perm_fili = models.IntegerField()
    perm_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    perm_ativ = models.BooleanField(default=True)
    perm_usua_libe = models.CharField(max_length=150, blank=True)
```

## 🔧 Endpoints da API

### Módulos
```http
GET /api/{slug}/parametros_admin/modulos-disponiveis/
POST /api/{slug}/parametros_admin/configurar-modulos-empresa/
GET /api/{slug}/parametros_admin/modulos-empresa-filial/?empresa_id=1&filial_id=1
```

### Permissões
```http
GET /api/{slug}/parametros_admin/permissoes-modulos/
POST /api/{slug}/parametros_admin/permissoes-modulos/
PUT /api/{slug}/parametros_admin/permissoes-modulos/{id}/
DELETE /api/{slug}/parametros_admin/permissoes-modulos/{id}/
```

### Configurações
```http
GET /api/{slug}/parametros_admin/configuracao-estoque/
GET /api/{slug}/parametros_admin/configuracao-financeiro/
GET /api/{slug}/parametros_admin/parametros-gerais/
```

## 📝 Exemplos de Uso

### Configurar Módulos para uma Empresa

```python
# Via API
POST /api/casaa/parametros_admin/configurar-modulos-empresa/
{
    "empresa_id": 1,
    "filial_id": 1,
    "modulos": ["dashboards", "Produtos", "Pedidos", "Entidades"]
}
```

### Verificar Módulos Liberados

```python
# Via API
GET /api/casaa/parametros_admin/modulos-empresa-filial/?empresa_id=1&filial_id=1

# Resposta
{
    "empresa_id": 1,
    "filial_id": 1,
    "modulos_liberados": ["dashboards", "Produtos", "Pedidos"],
    "total_modulos": 3
}
```

### Via Python
```python
from parametros_admin.utils import get_modulos_liberados_empresa

# Buscar módulos liberados
modulos = get_modulos_liberados_empresa('casaa', 1, 1)
print(f"Módulos liberados: {modulos}")
```

## 🔄 Migração do Sistema Antigo

### Passo a Passo

1. **Popular módulos:**
   ```bash
   python manage.py popular_modulos
   ```

2. **Popular permissões para cada licença:**
   ```bash
   python manage.py popular_modulos --popular-permissoes --banco casaa
   python manage.py popular_modulos --popular-permissoes --banco alma
   python manage.py popular_modulos --popular-permissoes --banco demonstracao
   ```

3. **Verificar se funcionou:**
   ```bash
   python manage.py shell
   ```
   ```python
   from parametros_admin.models import Modulo, PermissaoModulo
   print(f"Total de módulos: {Modulo.objects.count()}")
   print(f"Total de permissões: {PermissaoModulo.objects.count()}")
   ```

## 🎯 Vantagens do Novo Sistema

### ✅ Integridade
- Dados no banco ao invés de arquivo JSON
- Transações para garantir consistência
- Log de alterações

### ✅ Flexibilidade
- Controle granular por empresa/filial
- Permissões específicas por usuário
- Fácil adição de novos módulos

### ✅ Performance
- Cache de permissões
- Consultas otimizadas
- Menos dependências externas

### ✅ Manutenibilidade
- Interface administrativa
- Logs de auditoria
- Backup automático

## 🔍 Troubleshooting

### Módulo não encontrado
```bash
# Verificar se o módulo existe
python manage.py shell -c "from parametros_admin.models import Modulo; print(Modulo.objects.filter(modu_nome='Produtos').exists())"
```

### Permissões não funcionando
```bash
# Verificar permissões da empresa
python manage.py shell -c "from parametros_admin.models import PermissaoModulo; print(PermissaoModulo.objects.filter(perm_empr=1, perm_fili=1).count())"
```

### Cache não atualizando
```python
# Limpar cache manualmente
from django.core.cache import cache
cache.clear()
```

## 📋 Próximos Passos

1. **Implementar interface administrativa** para gerenciar permissões
2. **Adicionar controle de data de vencimento** para permissões
3. **Criar relatórios** de uso de módulos
4. **Implementar notificações** para módulos vencendo
5. **Adicionar controle de versão** de módulos 