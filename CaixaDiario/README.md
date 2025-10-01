# App CaixaDiario

Este app gerencia o controle de caixa diário, incluindo abertura, fechamento e movimentações financeiras do caixa.

## Funcionalidades

### 1. Controle de Caixa

- **Abertura de Caixa**: Registro de abertura diária por operador
- **Fechamento de Caixa**: Encerramento com conferência de valores
- **Múltiplos Caixas**: Suporte a vários caixas por filial
- **Controle por Operador**: Rastreamento de responsabilidade
- **Integração ECF**: Suporte a equipamentos fiscais

## API Endpoints

caixadiario

GET
/api/{slug}/caixadiario/caixageral/

POST
/api/{slug}/caixadiario/caixageral/

GET
/api/{slug}/caixadiario/caixageral/{caix_empr}/

PUT
/api/{slug}/caixadiario/caixageral/{caix_empr}/

PATCH
/api/{slug}/caixadiario/caixageral/{caix_empr}/

DELETE
/api/{slug}/caixadiario/caixageral/{caix_empr}/

GET
/api/{slug}/caixadiario/movicaixa/

POST
/api/{slug}/caixadiario/movicaixa/

GET
/api/{slug}/caixadiario/movicaixa/{movi_empr}/

PUT
/api/{slug}/caixadiario/movicaixa/{movi_empr}/

PATCH
/api/{slug}/caixadiario/movicaixa/{movi_empr}/

DELETE
/api/{slug}/caixadiario/movicaixa/{movi_empr}/

POST
/api/{slug}/caixadiario/movicaixa/adicionar_item/

POST
/api/{slug}/caixadiario/movicaixa/adicionar_itens_lote/

POST
/api/{slug}/caixadiario/movicaixa/finalizar_venda/

POST
/api/{slug}/caixadiario/movicaixa/iniciar_venda/

POST
/api/{slug}/caixadiario/movicaixa/processar_pagamento/
