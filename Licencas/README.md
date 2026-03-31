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



# Mobile SPS — Backend Django

Sistema de gestão multi-tenant com controle de licenças, planos trial e autenticação JWT.

---

## Stack

- Python 3.12 + Django 2.2.28
- PostgreSQL (multi-banco por licença)
- Django REST Framework + SimpleJWT
- Celery 5.3.6 + Redis (tasks agendadas)

---

## Configuração do ambiente

```bash
# Ativar virtualenv
& .venv/Scripts/Activate.ps1   # Windows
source .venv/bin/activate       # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Rodar migrações
python manage.py migrate

# Subir servidor
python manage.py runserver
```

### Variáveis de ambiente (.env)

```env
SECRET_KEY=...
DEBUG=True
USE_LOCAL_DB=True

LOCAL_DB_NAME=...
LOCAL_DB_USER=...
LOCAL_DB_PASSWORD=...
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=...
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=...

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=True   # True em dev, False em produção
```

---

## Arquitetura multi-tenant

Cada cliente tem seu próprio banco de dados PostgreSQL. O banco `default` armazena metadados globais (`LicencaWeb`, `Plano`). O roteamento é feito pelo `LicencaDBRouter` via slug na URL.

```
/api/{slug}/app/recurso/
         ↑
     identifica o banco do cliente
```

---

## Sistema de Planos e Trial

### Modelos envolvidos

| Modelo | Banco | Descrição |
|--------|-------|-----------|
| `Plano` | default | Define tipo, preço, duração e status do plano |
| `LicencaWeb` | default | Licença do cliente, vinculada a um Plano |

### Criação de ambiente trial

O método `PlanoService.criar_ambiente_trial()` executa em sequência:

1. Gera slug incremental (`saveweb001`, `saveweb002`, ...)
2. Cria `Plano` (15 dias, gratuito) e `LicencaWeb` no banco `default`
3. Cria banco PostgreSQL remoto a partir do template `base_modelo`
4. Popula dados iniciais: `Empresa`, `Filial`, usuários `web` e `admin`
5. Sincroniza e libera módulos via `PermissaoModulo`

```python
from planos.services import PlanoService

resultado = PlanoService.criar_ambiente_trial({
    'nome_empresa': 'Empresa X',
    'cnpj': '00000000000000',
    'email': 'contato@empresa.com',
    'telefone': '11999999999',
})
```

---

## Bloqueio de trial expirado

### 1. Task Celery (verificação diária)

Arquivo: `planos/tasks.py`

Roda todo dia às 00:05 e desativa planos trial com `plan_data_expi` no passado. Para cada plano expirado:
- Define `plan_ativ = False`
- Envia e-mail ao cliente informando a expiração

Agendamento em `settings.py`:

```python
CELERY_BEAT_SCHEDULE = {
    'verificar-trials-expirados-diario': {
        'task': 'planos.tasks.verificar_trials_expirados',
        'schedule': 86400,  # 24h
    },
}
```

### 2. Bloqueio no login (defesa em profundidade)

Arquivo: `Licencas/views.py` — `LoginView.post()`

No momento do login, após buscar a `LicencaWeb`, o sistema verifica o plano:

```python
licenca_web = LicencaWeb.objects.using('default').select_related('plano').filter(cnpj=docu).first()

if licenca_web and licenca_web.plano_id:
    plano = Plano.objects.using('default').get(id=licenca_web.plano_id)

    if plano.plan_trial:
        # Desativa on-the-fly se Celery atrasou
        if plano.plan_ativ and plano.plan_data_expi:
            if timezone.now() > plano.plan_data_expi:
                plano.plan_ativ = False
                plano.save(using='default', update_fields=['plan_ativ'])

        # Bloqueia o login
        if not plano.plan_ativ:
            return Response(
                {'error': 'Seu período de trial expirou.', 'code': 'trial_expirado'},
                status=403
            )
```

**Por que buscar com `using('default')` explicitamente?**
O `DATABASE_ROUTER` do projeto roteia queries pelo slug da URL. No contexto do login, o router pode direcionar para o banco do cliente em vez do `default`, causando `Plano.DoesNotExist`. A busca explícita evita esse problema.

### 3. Subir workers em produção

```bash
# Worker Celery
celery -A core worker --loglevel=info

# Beat (agendador)
celery -A core beat --loglevel=info
```

---

## Simulando o bloqueio de trial (desenvolvimento)

```bash
python manage.py shell
```

```python
from planos.models import Plano
from django.utils import timezone
from datetime import timedelta

# Forçar expiração de um plano
plano = Plano.objects.get(id=13)
plano.plan_ativ = True
plano.plan_data_expi = timezone.now() - timedelta(days=1)
plano.save()

# Rodar a task manualmente
from planos.tasks import verificar_trials_expirados
resultado = verificar_trials_expirados.apply()
print(resultado.result)

# Confirmar desativação
plano.refresh_from_db()
print(f"plan_ativ: {plano.plan_ativ}")  # False
```

---

## Dependências críticas (versões testadas)

```
celery==5.3.6
kombu==5.3.7
billiard==4.2.1
vine==5.1.0
amqp==5.2.0
```

> ⚠️ As versões anteriores (`celery==5.2.7` + `kombu==5.2.4` + `billiard==3.6.4.0`) são incompatíveis com Python 3.12 e causam `ImportError: cannot import name 'shared_task'`.

---

## Próximos passos planejados

- [ ] Envio de contrato de renovação quando trial expirar (ClickSign / PDF + link de aceite)
- [ ] Página web de renovação de plano
- [ ] Webhook de pagamento para reativar licença automaticamente