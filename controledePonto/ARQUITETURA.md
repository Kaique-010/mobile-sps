# Arquitetura Horizontal — controledePonto

## Visão Geral
- O app `controledePonto` adota uma arquitetura horizontal inspirada em DDD, separando responsabilidades em camadas coesas.
- Objetivo: manter regras de negócio independentes de frameworks, com fronteiras claras entre Domínio, Aplicação e Infraestrutura.

## Camadas e Pastas
- `Rest/dominio/entidades/`: modelos de domínio puros.
  - `registro_ponto.py`: entidade `RegistroPonto` com dados essenciais do registro.
- `Rest/dominio/portas/`: contratos (interfaces) que o domínio exige.
  - `repositorio_ponto.py`: interface `RepositorioPonto` para persistência.
- `Rest/aplicacoes/casos_uso/`: orquestra regras de negócio usando portas.
  - `pontos_uso.py`: `CasosDeUsoPonto` registra, lista e consulta registros.
- `repositorios.py`: implementação de portas usando infra Django ORM.
  - `RepositorioPontoModelo`: mapeia entidade de domínio para `models.RegistroPonto`.
- `models.py`: modelo Django que materializa os dados no banco.
- `Rest/serializers.py`: serializer DRF para expor/validar o modelo Django.
- `Rest/views.py`: endpoints REST; coordena banco-alvo, usa serializer e casos de uso.
- `Rest/urls.py`: roteamento.
- `Rest/permissoes.py`: permissões de acesso via DRF.

## Fluxo de Execução (Leitura/Escrita)
- Entrada HTTP → `Rest/views.py: RegistroPontoViewSet`
  - Obtém `banco` via query params ou default (`core.registry.get_licenca_db_config`).
  - `list`: filtra `queryset` no banco indicado e serializa.
  - `create`: valida payload pelo `RegistroPontoSerializer` e delega ao caso de uso.
- Caso de Uso → `Rest/aplicacoes/casos_uso/pontos_uso.py`
  - Cria `RegistroPonto` (domínio) e chama a porta `RepositorioPonto.registrar`.
- Porta/Infra → `repositorios.py`
  - `RepositorioPontoModelo` grava/consulta via `models.RegistroPonto.objects.using(banco)`.
  - Converte entre entidade de domínio e modelo Django quando necessário.

## Regras de Dependência
- Views/Serializers dependem de Django/DRF; não acessam regras de negócio diretamente.
- Casos de uso dependem apenas de portas do domínio; não conhecem Django.
- Infra (`repositorios.py`) conhece Django e implementa as portas.
- Entidades do domínio não dependem de Django/DRF.

## Decisões de Projeto
- `RegistroPonto` (domínio) tem `id` opcional para permitir criação sem acoplamento ao ORM.
- `RepositorioPonto.listar_por_id` retorna `Optional[List[RegistroPonto]]` para suportar múltiplos registros por colaborador.
- `ViewSet` calcula dinamicamente o `banco` e filtra por `colaborador_id` via query params.
- `Serializer` expõe `id` e mantém `data_hora` somente leitura; o caso de uso define o momento da marcação.

## Pontos de Extensão
- Auditar permissões e políticas de acesso em `Rest/permissoes.py`.
- Adicionar validações de domínio (ex.: alternância entre entrada/saída) nos casos de uso.
- Completar testes unitários para cada camada.

## Referências de Código
- `controledePonto/Rest/views.py`
- `controledePonto/Rest/serializers.py`
- `controledePonto/Rest/aplicacoes/casos_uso/pontos_uso.py`
- `controledePonto/Rest/dominio/entidades/registro_ponto.py`
- `controledePonto/Rest/dominio/portas/repositorio_ponto.py`
- `controledePonto/repositorios.py`
- `controledePonto/models.py`
