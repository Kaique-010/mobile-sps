Arquitetura da Solução

- Camadas
  - Domínio: `Notas_Fiscais/models.py` define as tabelas principais: `nf_nota`, `nf_nota_item`, `nf_item_imposto`, `nf_transporte`, `nf_nota_evento` e relacionamentos com `Entidades`, `Filiais`, `Produtos`.
  - Serviços: regras de negócio em `Notas_Fiscais/services/*` para criação, atualização, cálculo de impostos, transporte e eventos.
  - Aplicação: integração com PyNFe e SEFAZ em `Notas_Fiscais/aplicacao/*` (montagem de DTO, construção do XML e emissão).
  - Infraestrutura: acesso a certificado e adaptação de comunicação com SEFAZ em `Notas_Fiscais/infrastructure/*`.
  - APIs: endpoints REST em `Notas_Fiscais/REST/*` e endpoint de emissão direta em `Notas_Fiscais/api/*`.

- Modelagem de Dados
  - `nf_nota` (`Nota`): cabeçalho da nota; chave composta lógico-única por `empresa+filial+modelo+serie+numero`; relaciona `emitente:Filiais` e `destinatario:Entidades`.
  - `nf_nota_item` (`NotaItem`): itens vinculados a `nf_nota`; relaciona `produto:Produtos`; índices em `nota` e `produto`.
  - `nf_item_imposto` (`NotaItemImposto`): impostos por item (ICMS/IPI/PIS/COFINS/FCP e suportes para CBS/IBS); relação 1–1 com `nf_nota_item`.
  - `nf_transporte` (`Transporte`): dados de frete/veículo; relação 1–1 com `nf_nota`.
  - `nf_nota_evento` (`NotaEvento`): eventos (cancelamento, autorização, CC-e, etc.); relação N–1 com `nf_nota`.
  - Legado: `nfevv` (`NotaFiscal`) e `infvv` (`Infvv`) são tabelas legadas (não gerenciadas) usadas para leitura/ETL.

- Relacionamentos
  - `Nota` 1–N `NotaItem` e 1–N `NotaEvento`.
  - `NotaItem` 1–1 `NotaItemImposto`.
  - `Nota` 1–1 `Transporte`.
  - `Nota` N–1 `Filiais` (emitente) e N–1 `Entidades` (destinatário).

- Regras de Negócio
  - Criação/Atualização de Nota: `NotaService` normaliza dados, valida participantes e persiste itens e impostos opcionais.
  - Impostos: `CalculoImpostosService` usa `CFOP.services.MotorFiscal` para resolver CFOP, NCM, alíquotas e calcular tributos, preenchendo `nf_item_imposto`.
  - Transporte: `TransporteService` normaliza e atualiza dados de frete com `update_or_create`.
  - Eventos: `EventoService` registra eventos e `NotaService.transmitir/cancelar` atualiza `status` e metadados.
  - Emissão: `EmissaoService` calcula impostos, monta DTO (`dominio.builder`), constrói NFe (`construir_nfe_pynfe`), assina e transmite via `SefazAdapter`.

- Endpoints
  - REST (`router`): `notas`, `notas-eventos`, autocompletes de entidades e produtos.
  - Emissão direta: `api/emitir/<slug>/<nota_id>/` para integração externa.

- Fluxo de Dados
  - Entrada: payload REST → `NotaService` → `ItensService` → persistência em `nf_nota`, `nf_nota_item`, `nf_item_imposto` e `nf_transporte`.
  - Cálculo: `CalculoImpostosService` aplica alíquotas e bases por item.
  - Emissão: `EmissaoService` → DTO → PyNFe → assinatura A1 → envio SEFAZ → atualização de `nf_nota` e registro de evento.

- Dependências do Sistema
  - Django, Django REST Framework, PyNFe, `python-decouple`, PostgreSQL, app CFOP, Produtos, Entidades, Licencas.
  - Certificado A1 em `Filiais.empr_cert_digi` e senha em `Filiais.empr_senh_cert`.

- Configurações Necessárias
  - Banco: `core/licencas.json` define `slug` e parâmetros; variáveis `SLUG_DB_USER/SLUG_DB_PASSWORD` via `decouple`.
  - Ambiente SEFAZ: `Nota.ambiente` (1 produção, 2 homologação); `Filiais.empr_ambi_nfe` pode orientar defaults.
  - Rotas: incluídas em `core/api_router.py` sob `/api/<slug>/notasfiscais/`.

