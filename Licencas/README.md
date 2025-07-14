# App Licenças

O app **Licenças** é responsável pelo gerenciamento de usuários, empresas, filiais e licenças do sistema. Ele controla a autenticação, autorização e licenciamento de funcionalidades para diferentes empresas e filiais.

# App Licenças

## Funcionalidades Principais

### 🔐 Gestão de Usuários

- Sistema de autenticação customizado com segurança melhorada
- Gerenciamento seguro de senhas
- Suporte a senhas em hash e texto plano (compatibilidade)
- Funcionalidade de alteração de senha via API
- Controle de setores por usuário
- Integração com sistema de permissões

### 🏢 Gestão de Empresas e Filiais

- Cadastro de empresas matriz
- Gerenciamento de filiais
- Controle por CNPJ
- Estrutura hierárquica

### 📋 Sistema de Licenças

- Controle de licenças por CNPJ
- Bloqueio/desbloqueio de licenças
- Limite de empresas e filiais
- Módulos liberados por licença
- Auditoria de alterações

## Estrutura dos Modelos

### Modelo `Usuarios`

```python
class Usuarios(AbstractBaseUser, PermissionsMixin):
    usua_codi = models.AutoField(primary_key=True)
    usua_nome = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, db_column='usua_senh_mobi')
    usua_seto = models.IntegerField(db_column='usua_seto')
```

**Campos principais:**

- `usua_codi`: Código único do usuário
- `usua_nome`: Nome de usuário (único)
- `password`: Senha do usuário
- `usua_seto`: Setor do usuário

### Modelo `Empresas`

```python
class Empresas(models.Model):
    empr_codi = models.AutoField(primary_key=True)
    empr_nome = models.CharField(max_length=100)
    empr_docu = models.CharField(max_length=14, unique=True)
```

**Campos principais:**

- `empr_codi`: Código único da empresa
- `empr_nome`: Nome da empresa
- `empr_docu`: CNPJ da empresa (único)

### Modelo `Filiais`

```python
class Filiais(models.Model):
    empr_empr = models.IntegerField(primary_key=True)
    empr_codi = models.ForeignKey(Empresas, on_delete=models.CASCADE)
    empr_nome = models.CharField(max_length=100)
    empr_docu = models.CharField(max_length=14, unique=True)
```

**Campos principais:**

- `empr_empr`: Código da Empresa
- `empr_codi`: Referência à empresa matriz
- `empr_nome`: Nome da filial
- `empr_docu`: CNPJ da filial (único)

### Modelo `Licencas`

```python
class Licencas(models.Model):
    lice_id = models.AutoField(primary_key=True)
    lice_docu = models.CharField(max_length=14, unique=True)
    lice_nome = models.CharField(max_length=100)
    lice_emai = models.EmailField(blank=True, null=True)
    lice_bloq = models.BooleanField(default=False)
    lice_nume_empr = models.IntegerField()
    lice_nume_fili = models.IntegerField()
```

**Campos principais:**

- `lice_id`: ID único da licença
- `lice_docu`: CNPJ da licença (único)
- `lice_nome`: Nome da licença
- `lice_emai`: Email de contato
- `lice_bloq`: Status de bloqueio
- `lice_nume_empr`: Número máximo de empresas
- `lice_nume_fili`: Número máximo de filiais

## Melhorias de Segurança

### Autenticação Aprimorada

- **Método `check_password` melhorado**: Suporta tanto senhas em hash quanto em texto plano para compatibilidade
- **Validação segura**: Primeiro tenta verificar hash do Django, depois fallback para texto plano
- **Logs de segurança**: Sistema de logs para tentativas de autenticação

### Alteração de Senha

- **Validação de senha atual**: Opção de validar senha atual antes da alteração
- **Validação de força**: Senha mínima de 4 caracteres
- **Suporte multi-banco**: Funciona com diferentes bancos de dados por licença
- **Tratamento de erros**: Mensagens de erro específicas e seguras

## Exemplos de Uso

### Criar Usuário

```python
from Licencas.models import Usuarios

# Criar usuário
usuario = Usuarios.objects.create_user(
    usua_nome='joao.silva',
    password='senha123',
    usua_seto=1
)
```

### Autenticar Usuário

```python
# Verificar senha (método melhorado)
usuario = Usuarios.objects.get(usua_nome='joao.silva')
if usuario.check_password('senha123'):
    print('Senha correta')
```

### Alterar Senha

```python
# Usando método de instância
usuario = Usuarios.objects.get(usua_nome='joao.silva')
usuario.atualizar_senha('nova_senha_123')

# Usando função utilitária
from Licencas.utils import atualizar_senha
atualizar_senha('joao.silva', 'nova_senha_123', request)
```

### Gerenciar Empresas

```python
from Licencas.models import Empresas, Filiais

# Criar empresa
empresa = Empresas.objects.create(
    empr_nome='Empresa ABC Ltda',
    empr_docu='12345678000195'
)

# Criar filial
filial = Filiais.objects.create(
    empr_codi=empresa,
    empr_nome='Filial São Paulo',
    empr_docu='12345678000276'
)
```

### Controlar Licenças

```python
from Licencas.models import Licencas

# Criar licença
licenca = Licencas.objects.create(
    lice_docu='12345678000195',
    lice_nome='Licença Empresa ABC',
    lice_emai='contato@empresaabc.com',
    lice_nume_empr=5,
    lice_nume_fili=10
)

# Bloquear licença
licenca.lice_bloq = True
licenca.save()

# Verificar módulos liberados
modulos = licenca.get_modu_libe()
print(f'Módulos liberados: {modulos}')
```

# App Licenças

## Endpoints da API

### Usuários

```http
GET /api/usuarios/
GET /api/usuarios/{id}/
POST /api/usuarios/
PUT /api/usuarios/{id}/
DELETE /api/usuarios/{id}/
```

### Autenticação e Segurança

```http
POST /api/licencas/login/
POST /api/licencas/alterar-senha/
```

#### Alterar Senha

**Endpoint:** `POST /api/licencas/alterar-senha/`

**Headers:**

```
Authorization: Bearer {token}
Content-Type: application/json
```

**Body:**

```json
{
  "usuarioname": "nome_do_usuario",
  "nova_senha": "nova_senha_123",
  "senha_atual": "senha_atual_opcional"
}
```

**Resposta de Sucesso:**

```json
{
  "message": "Senha alterada com sucesso."
}
```

**Validações:**

- Nova senha deve ter pelo menos 4 caracteres
- Se `senha_atual` for fornecida, será validada
- Usuário deve existir no sistema

### Empresas

```http
GET /api/empresas/
GET /api/empresas/{id}/
POST /api/empresas/
PUT /api/empresas/{id}/
```

### Licenças

```http
GET /api/licencas/
GET /api/licencas/{id}/
POST /api/licencas/
PUT /api/licencas/{id}/
```

**Filtros disponíveis:**

- `?lice_docu=12345678000195` - Filtrar por CNPJ
- `?lice_bloq=false` - Filtrar por status de bloqueio
- `?lice_nome__icontains=ABC` - Buscar por nome

**Exemplo de requisição:**

```json
POST /api/licencas/
{
    "lice_docu": "12345678000195",
    "lice_nome": "Licença Teste",
    "lice_emai": "teste@empresa.com",
    "lice_nume_empr": 3,
    "lice_nume_fili": 5,
    "lice_bloq": false
}
```

## Considerações Técnicas

### Banco de Dados

- Tabelas: `usuarios`, `empresas`, `filiais`, `licencas`
- Índices em campos únicos (CNPJ, nome de usuário)
- Relacionamentos com chaves estrangeiras

### Segurança

- Sistema de autenticação customizado
- Controle de permissões por usuário
- Validação de CNPJ
- Criptografia de senhas (quando habilitada)

### Performance

- Índices em campos de busca frequente
- Cache de consultas de licenças
- Otimização de queries com select_related

## Integração com Outros Apps

### OrdemdeServico

- Usuários vinculados a setores
- Controle de acesso por setor

### Todos os Apps

- Validação de licenças
- Controle de empresas/filiais
- Autenticação de usuários

## Troubleshooting

### Problemas Comuns

**Erro de autenticação:**

```python
# Verificar se usuário existe
try:
    usuario = Usuarios.objects.get(usua_nome='nome_usuario')
except Usuarios.DoesNotExist:
    print('Usuário não encontrado')
```

**Licença bloqueada:**

```python
# Verificar status da licença
licenca = Licencas.objects.get(lice_docu='12345678000195')
if licenca.lice_bloq:
    print('Licença bloqueada')
```

**Limite de empresas/filiais:**

```python
# Verificar limites
empresa_count = Empresas.objects.filter(empr_docu__startswith='12345').count()
if empresa_count >= licenca.lice_nume_empr:
    print('Limite de empresas atingido')
```

### Logs de Debug

```python
import logging
logger = logging.getLogger('licencas')

# Log de autenticação
logger.info(f'Tentativa de login: {username}')

# Log de licença
logger.warning(f'Licença bloqueada: {cnpj}')
```

### Comandos de Manutenção

```bash
# Verificar licenças expiradas
python manage.py shell -c "from Licencas.models import Licencas; print(Licencas.objects.filter(lice_bloq=True).count())"

# Resetar senha de usuário
python manage.py shell -c "from Licencas.models import Usuarios; u = Usuarios.objects.get(usua_nome='admin'); u.set_password('nova_senha'); u.save()"

# Listar empresas por licença
python manage.py shell -c "from Licencas.models import *; [print(f'{e.empr_nome}: {e.empr_docu}') for e in Empresas.objects.all()]"
```

update usuarios SET usua_senh_mobi = 'roma3030@' WHERE usua_codi = 1;
update usuarios SET usua_seto = 'ADM' WHERE usua_codi = 1;
