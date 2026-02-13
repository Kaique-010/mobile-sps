# Guia de Implementação e Parametrização - Módulo Agrícola

## Visão Geral

Este documento descreve as decisões de modelagem e a estrutura de parametrização do módulo agrícola, bem como o processo de sincronização entre empresas.

## 1. Modelagem de Estoque e Lotes

### 1.1 Controle de Estoque Global
A tabela `EstoqueFazenda` é utilizada para o controle consolidado do estoque por empresa, filial, fazenda e produto.
- **Model**: `EstoqueFazenda`
- **Campos Chave**: `estq_empr`, `estq_fili`, `estq_faze`, `estq_prod`
- **Saldo**: `estq_quant`

### 1.2 Controle de Lotes
Para produtos que requerem rastreabilidade detalhada (ex: defensivos, sementes), utilizamos a tabela `LoteProdutos`.
- **Model**: `LoteProdutos`
- **Tabela**: `produtos_lotes`
- **Campo de Quantidade**: `lote_quant` (validado como o campo correto para saldo de lote, em detrimento de `lote_quan`).
- **Relação**: Um produto pode ter múltiplos lotes. O somatório de `lote_quant` deve ser conciliado com `EstoqueFazenda.estq_quant` se o parâmetro `controla_lote` estiver ativo.

## 2. Parametrização

Os parâmetros agrícolas são definidos em `Agricola.registry.ParametrosAgricolasRegistry`.

### 2.1 Estrutura
Os parâmetros são armazenados na tabela `ParametroAgricola` (model), mas suas definições (tipo, default, label) ficam no código (registry).

Exemplos de parâmetros:
- `controla_estoque` (bool): Ativa/desativa validações de estoque.
- `permite_estoque_negativo` (bool): Permite saídas sem saldo suficiente.
- `controla_lote` (bool): Exige identificação de lote nas movimentações.

### 2.2 Serviço
O `ParametroAgricolaService` (`Agricola.service.parametros`) é responsável por ler e escrever esses parâmetros, utilizando cache ou consulta direta ao banco.

## 3. Sincronização Multi-Empresa

Para ambientes multi-tenant onde múltiplas empresas/filiais operam em bancos de dados distintos (roteamento por licença), a sincronização de parâmetros deve garantir que novos parâmetros definidos no `Registry` sejam criados em todos os bancos de dados configurados.

### 3.1 Processo de Sync
O comando `sync_parametros_agricola` foi atualizado para:
1. Carregar todas as licenças ativas via `core.licencas_loader.carregar_licencas_dict`.
2. Iterar sobre cada banco de dados configurado.
3. Garantir a existência dos registros de parâmetros para todas as empresas/filiais encontradas naquele banco.

Isso elimina a necessidade de executar o comando manualmente para cada banco individualmente.

## 4. Guia de Manutenção

### Adicionar Novo Parâmetro
1. Edite `d:\mobile-sps\Agricola\registry.py` e adicione a chave no dicionário `PARAMS`.
   ```python
   "novo_parametro": {
       "tipo": bool,
       "default": False,
       "label": "Novo Parâmetro",
       "grupo": "Geral"
   }
   ```
2. Execute o comando de sincronização:
   ```bash
   python manage.py sync_parametros_agricola
   ```

### Ajustes de Layout
O painel de parâmetros (`parametros_agricolas.html`) segue o padrão visual do painel de módulos, utilizando Tailwind/CSS customizado para modo escuro (`#0f1419`).
