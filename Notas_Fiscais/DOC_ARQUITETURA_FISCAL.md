# Documentação da Nova Arquitetura Fiscal

## Visão Geral

Este documento descreve a refatoração do motor fiscal do sistema, agora estruturado em uma arquitetura horizontal e determinística para facilitar auditoria, correções e testes.

## Componentes Principais

### 1. MotorFiscal (`CFOP/services/services.py`)

O orquestrador central do cálculo.

- **Responsabilidade**: Coordenar a busca de dados (NCM, CFOP, Alíquotas) e a execução das calculadoras.
- **Determinismo**: O fluxo é sequencial e explícito (Resolver -> Carregar Dados -> Aplicar Overrides -> Calcular).
- **Interface**: `calcular_item(ctx, item, tipo_oper, base_manual)`

### 2. Contexto Fiscal (`FiscalContext`)

Objeto imutável (dataclass) que carrega todo o estado necessário para o cálculo de um item.

- Elimina "side effects" e dependências globais ocultas.
- Contém: Produto, NCM, CFOP, Regras Fiscais, Alíquotas Base, Dados de ICMS (Origem/Destino).

### 3. Calculadoras (`TaxCalculator`)

Implementações isoladas para cada tributo, herdando de `TaxCalculator`.

- **IPICalculator**: Calcula IPI.
- **ICMSCalculator**: Calcula ICMS Próprio e ST (Substituição Tributária).
- **PISCOFINSCalculator**: Calcula PIS e COFINS.
- **IBSCBSCalculator**: Prepara o terreno para a Reforma Tributária.

### 4. Serviço de Aplicação (`CalculoImpostosService`)

Localizado em `Notas_Fiscais/services/calculo_impostos_service.py`.

- **Integração**: Ponte entre o `MotorFiscal` e os modelos de Nota Fiscal (`Nota`, `NotaItem`).
- **Persistência**: Salva os resultados calculados nas tabelas `NotaItem` e `NotaItemImposto`.
- **Transacional**: Garante atomicidade por nota.

### 5. Novos Componentes (Resolvers)

#### ResolverAliquotaPorRegime (`CFOP/services/auxiliares.py`)

Responsável por modular as alíquotas base conforme o regime da empresa (Simples vs Normal) e preparar para IBS/CBS.

- **Entrada**: NcmAliquota, Regime.
- **Saída**: Dict de alíquotas ajustadas.

#### ResolverCST (`CFOP/services/services.py`)

Centraliza a lógica de determinação de CST e CSOSN, removendo complexidade das calculadoras.

- **Lógica**: Prioriza Overrides > Regime (Simples/Normal) > Defaults.
- **Suporte**: ICMS (CST/CSOSN), IPI, PIS/COFINS.

#### ResolverIncidencia (`Notas_Fiscais/services/calculo_impostos_service.py`)

Atua no nível de negócio (Nota) para ajustar regras fiscais antes do cálculo matemático.

- **Uso**: Aplicação de isenções (Suframa, etc) alterando flags do CFOP em memória.

## Fluxo de Dados

1. **Emissão de Nota**: O `EmissaoNotaService` chama `CalculoImpostosService.aplicar_impostos(nota)`.
2. **Preparação**:
   - `ResolverIncidencia` aplica regras de negócio ao CFOP.
   - Serviço monta um `FiscalContext` com dados da empresa, cliente e produto.
3. **Cálculo (MotorFiscal)**:
   - Resolução de CFOP (baseado na operação e estados).
   - `ResolverAliquotaPorRegime` busca alíquotas ajustadas.
   - Aplicação de Overrides de CFOP ou NCM.
   - `ResolverCST` determina a situação tributária.
   - Execução sequencial das Calculadoras.
4. **Resultado**: Um dicionário "pacote" contendo todas as bases, alíquotas, valores e CSTs.
5. **Persistência**: O serviço grava os dados no banco.

## Matriz de Decisão de Regime

| Imposto | Regime Normal (3) | Simples Nacional (1/2)  |
| ------- | ----------------- | ----------------------- |
| ICMS    | CST 00, 10, 20... | CSOSN 101, 102...       |
| IPI     | CST 50, 51...     | Geralmente N/A ou 49/99 |
| PIS/COF | CST 01, 02...     | CST 49 ou 99            |
| IBS/CBS | Full (2026+)      | Transição/Diferenciado  |

## Arquivos Relacionados

- **`CFOP/services/services.py`**: MotorFiscal, Calculadoras e ResolverCST.
- **`CFOP/services/auxiliares.py`**: ResolverAliquotaPorRegime.
- **`Notas_Fiscais/services/calculo_impostos_service.py`**: ResolverIncidencia e Serviço de Aplicação.
- **`CFOP/tests/test_resolvers.py`**: Testes unitários dos novos componentes.

## Testes

Foram criados testes unitários em `CFOP/tests/test_services.py` e `CFOP/tests/test_resolvers.py` cobrindo:

- Cálculo de impostos (IPI, ICMS, PIS/COFINS).
- Lógica de decisão de CST/CSOSN.
- Resolução de alíquotas por regime.
- Integração do Motor Fiscal.
