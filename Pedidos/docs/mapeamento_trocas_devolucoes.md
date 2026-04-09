# Mapeamento inicial — Trocas e Devoluções no app de Pedidos

## 1) Objetivo

Estruturar o fluxo de **troca/devolução** a partir de um pedido de venda já existente, garantindo coerência entre:

- **Comercial/Pedidos** (origem + itens selecionados);
- **Estoque** (volta e/ou nova saída);
- **Financeiro** (estorno, abatimento, crédito ou novo título);
- **Comissões** (reversão e novo cálculo).

Este documento é um mapa funcional/técnico inicial para implementação incremental.

---

## 2) Princípios (estrutura horizontal)

Para manter a estrutura horizontal, o processo deve ser decomposto em camadas com responsabilidades claras:

1. **Camada de Orquestração (Use Case / Service)**
   - Coordena o processo de troca/devolução ponta a ponta.
   - Não implementa regras detalhadas de estoque/financeiro/comissão.

2. **Camada de Domínio por Contexto**
   - `Pedidos`: valida vínculo com pedido original e itens elegíveis.
   - `Estoque`: executa volta e saída de estoque.
   - `Financeiro`: executa ajuste financeiro conforme cenário.
   - `Comissões`: estorna e recalcula comissão.

3. **Camada de Infraestrutura**
   - Persistência, integração entre apps, logs, auditoria e idempotência.

> Regra geral: cada contexto deve expor uma interface simples para o orquestrador, evitando acoplamento cruzado direto entre módulos.

---

## 3) Fluxo funcional macro

### Etapa A — Selecionar pedido original

1. Usuário informa/seleciona pedido de origem.
2. Sistema valida:
   - pedido existe;
   - não está cancelado;
   - possui itens elegíveis para troca/devolução;
   - não excede quantidade já devolvida anteriormente.

### Etapa B — Selecionar itens para troca/devolução

Para cada item selecionado:

- produto;
- quantidade solicitada;
- motivo da troca/devolução;
- condição do item (revenda, avaria, descarte, assistência);
- tipo de operação:
  - **Devolução total/parcial**;
  - **Troca com reposição** (gera retorno + nova saída);
  - **Troca por item diferente** (retorno do item A e saída do item B).

### Etapa C — Confirmar e processar

Ao confirmar, disparar sequência transacional:

1. Criar documento de troca/devolução (cabeçalho + itens);
2. Processar **movimentações de estoque**;
3. Processar **ajustes financeiros**;
4. Processar **ajustes de comissão**;
5. Atualizar status e trilha de auditoria.

---

## 4) Regras de negócio mínimas por domínio

### 4.1 Pedidos

- Toda troca/devolução deve referenciar um `pedido_origem`.
- Itens devolvidos não podem ultrapassar quantidade líquida vendida.
- Deve existir controle de saldos por item:
  - `qtd_vendida`;
  - `qtd_devolvida_acumulada`;
  - `qtd_saldo_trocavel`.

### 4.2 Estoque

Cenários:

1. **Devolução sem reposição**
   - gera **entrada** no estoque (quando item retorna para revenda) OU
   - gera entrada em local de avaria/quarentena.

2. **Troca com reposição do mesmo item**
   - entrada do item devolvido;
   - saída do item de reposição.

3. **Troca por item diferente**
   - entrada do item devolvido;
   - saída do novo item.

Controles essenciais:

- motivo de movimentação;
- vínculo com transação de troca;
- idempotência (não processar a mesma troca duas vezes).

### 4.3 Financeiro

Cenários:

- **Estorno total/parcial** (cancelar/baixar títulos);
- **Geração de crédito** para uso futuro;
- **Abatimento em aberto** no pedido original;
- **Diferença a cobrar/pagar** quando troca envolve itens com valores diferentes.

Regras:

- preservar rastreabilidade entre título original e ajuste;
- bloquear fechamento sem regra financeira definida.

### 4.4 Comissões

- Estornar comissão sobre valor devolvido;
- Recalcular comissão da reposição (se aplicável);
- Tratar janela de pagamento:
  - comissão já paga → gerar débito/compensação futura;
  - comissão não paga → ajustar no cálculo corrente.

---

## 5) Proposta de status da troca/devolução

- `RASCUNHO`
- `AGUARDANDO_APROVACAO` (opcional)
- `PROCESSANDO`
- `CONCLUIDA`
- `PARCIAL` (quando parte falha)
- `CANCELADA`
- `ERRO_PROCESSAMENTO`

---

## 6) Estrutura de dados sugerida (conceitual)

### `troca_devolucao` (cabeçalho)

- `id`
- `empresa`, `filial`
- `pedido_origem`
- `cliente`, `vendedor`
- `tipo` (TROCA, DEVOLUCAO)
- `status`
- `valor_total_devolvido`
- `valor_total_reposto`
- `saldo_financeiro`
- `criado_em`, `criado_por`, `finalizado_em`

### `troca_devolucao_item`

- `id`, `troca_devolucao_id`
- `item_pedido_origem`
- `produto_origem`, `qtd_origem`
- `produto_reposicao` (opcional), `qtd_reposicao`
- `motivo`, `condicao_item`
- `valor_origem`, `valor_reposicao`
- `status_item`

### `troca_devolucao_evento` (auditoria)

- `id`, `troca_devolucao_id`
- `tipo_evento` (ESTOQUE_ENTRADA, ESTOQUE_SAIDA, FINANCEIRO_AJUSTE, COMISSAO_ESTORNO etc.)
- `payload_resumo`
- `processado_em`
- `sucesso`, `mensagem_erro`

---

## 7) Sequência técnica recomendada (MVP)

1. **Fase 1 — Motor de devolução simples**
   - Devolução parcial/total sem item de reposição.
   - Entrada de estoque + ajuste financeiro + estorno comissão.

2. **Fase 2 — Troca com reposição**
   - Permitir item de reposição (mesmo produto).
   - Ajustar diferença financeira (se houver).

3. **Fase 3 — Troca cruzada (produto diferente)**
   - Regras de preço, margem, comissão e aprovação.

4. **Fase 4 — Governança**
   - Aprovação por perfil.
   - Métricas em dashboard (taxa de troca, motivos, impacto financeiro).

---

## 8) Checklist de validação (antes de implementar)

- Definir se a troca gera **novo pedido** ou documento próprio (recomendado: documento próprio com referência ao pedido).
- Definir tabela/campo de vínculo com movimentos de estoque já existentes.
- Definir estratégia para títulos financeiros já liquidados.
- Definir política de comissão por cenário (paga/não paga).
- Definir matriz de permissões (quem cria, aprova, cancela).
- Definir catálogo padronizado de motivos de troca/devolução.

---

## 9) Próximo passo sugerido

Com base neste mapa, criar:

1. **Especificação funcional curta** (regras e telas);
2. **Contrato técnico entre módulos** (`Pedidos`, `Estoque`, `Financeiro`, `Comissões`);
3. **Backlog por fase** com histórias pequenas e critérios de aceite.

