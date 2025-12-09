# Migração do roteamento por licenças para banco de dados

## Visão geral
- O arquivo `core/licencas.json` foi substituído por uma tabela `licencas_web_licencaweb`.
- O roteamento por `slug` permanece idêntico, com retrocompatibilidade via fallback para o JSON caso a tabela esteja vazia ou indisponível.

## Estrutura da tabela
- Campos: `slug`, `cnpj`, `db_name`, `db_host`, `db_port`, `modulos`.
- Novos campos: `db_user`, `db_password` (antes lidos do `.env`).

## App Django
- Novo app: `licencas_web` (adicionado em `INSTALLED_APPS`).
- Modelo: `LicencaWeb`.
- Migrações:
  - `0001_initial`: criação da tabela.
  - `0002_load_initial_licencas`: carga inicial a partir de `core/licencas.json`, incluindo credenciais do `.env` por prefixo (`<SLUG>_DB_USER` e `<SLUG>_DB_PASSWORD`).

## Adaptações no código
- `core/licenca_context.py`: passa a ler do banco; se falhar, usa o JSON.
- `core/utils.get_db_from_slug`: prioriza credenciais da tabela; fallback para `.env`.
- `core/db_router.py` e `core/middleware.py`: continuam funcionando sem alterações de rota (slug).

## Retrocompatibilidade
- Se a tabela estiver vazia ou sem migrações aplicadas, o sistema usa `core/licencas.json` automaticamente.
- Variáveis de ambiente continuam válidas e são usadas como fallback de credenciais.

## Testes
- Testes em `licencas_web/tests.py` validam:
  - Criação de configuração de banco via `slug` usando credenciais da tabela.
  - Fallback para `.env` quando não há credenciais na tabela.
  - Extração do `slug` a partir do path de requisição.

## Como migrar ambientes existentes
1. Garantir que `licencas_web` esteja em `INSTALLED_APPS`.
2. Rodar migrações:
   - `python manage.py migrate licencas_web`
3. Validar carga inicial:
   - Verificar registros de `LicencaWeb` criados a partir de `core/licencas.json`.
   - Popular `db_user`/`db_password` via `.env` ou editar diretamente na tabela.
4. Verificar rotas:
   - `/api/<slug>/...` e `/web/home/<slug>/...` devem seguir funcionando.

## Observações de segurança
- `db_password` é armazenado no banco; restringir acesso administrativo.
- Nunca commitar credenciais em repositório; preferir `.env` para provisionamento inicial.

## Atualização do `savexml1`
- O registro `slug=save1` é migrado automaticamente via `0002_load_initial_licencas`.
- Credenciais podem ser lidas do `.env` (`SAVE1_DB_USER`, `SAVE1_DB_PASSWORD`) e gravadas na tabela.
