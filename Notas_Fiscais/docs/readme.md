Notas Fiscais

Descrição

- Módulo de Notas Fiscais (NF-e 55 / NFC-e 65) com camadas de Domínio, Serviços, Aplicação (PyNFe/SEFAZ), Infraestrutura, APIs REST e páginas Web.

Arquitetura

- Domínio: `Notas_Fiscais/models.py` define tabelas `nf_nota`, `nf_nota_item`, `nf_item_imposto`, `nf_transporte`, `nf_nota_evento`.
- Serviços: `Notas_Fiscais/services/*` implementam criação/atualização, cálculo fiscal, transporte e eventos. Função `gravar` registra rascunho.
- Aplicação: `Notas_Fiscais/aplicacao/*` monta DTO (`dominio/builder.py`), constrói XML PyNFe e transmite via SEFAZ.
- Infraestrutura: certificado A1 e comunicação SEFAZ em `Notas_Fiscais/infrastructure/*`.
- APIs: `Notas_Fiscais/REST/*` para operações CRUD/eventos e `Notas_Fiscais/api/*` para emissão direta.
- Web: `Notas_Fiscais/Web/*` e `templates_spsWeb/notas/*` com listagem, detalhe e emissão com autocomplete.

Componentes Principais

- `NotaService`: criar/atualizar/cancelar/transmitir/inutilizar/gravar.
- `CalculoImpostosService`: resolve CFOP/NCM/alíquotas e grava impostos de itens.
- `EmissaoService`: integra PyNFe, assina e envia para SEFAZ.
- `sefaz_adapter`: serializa XML, assina A1 e autoriza.

Fluxo de Trabalho

1. Criação: via REST ou Web, chama `NotaService.criar` e `NotaService.gravar` (rascunho).
2. Cálculo: `CalculoImpostosService` preenche impostos por item.
3. Emissão: `EmissaoService.emitir(nota_id)` → XML assinado → SEFAZ → status/ chave/protocolo.
4. Eventos: cancelamento/inutilização registram em `nf_nota_evento` e atualizam status.

Configuração

- Banco: mapa/licenças em `core/licenca_context.py` e `core/licencas.json`.
- Certificado: `Filiais.empr_cert_digi` e `Filiais.empr_senh_cert` da empresa/filial.
- Rotas API: `core/api_router.py` expõe `/api/<slug>/notasfiscais/`.

Execução

- Emissão de teste: `python manage.py emitir_notas_teste --empresa <E> --filial <F>`.
- Web: abra `/web/<slug>/notas-fiscais/` para listar/emitir/cancelar/inutilizar.

Testes

- `python manage.py test Notas_Fiscais`.
