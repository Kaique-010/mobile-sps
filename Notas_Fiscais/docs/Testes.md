Plano de Testes

- Testes de Endpoints
  - Listagem: `GET /api/<slug>/notasfiscais/notas-fiscais/notas/?empresa=<id>&filial=<id>` deve retornar 200 e itens conforme filtros.
  - Detalhe: `GET /api/<slug>/notasfiscais/notas-fiscais/notas/{id}/` retorna 200 e inclui `itens`, `impostos`, `transporte`.
  - Criação: `POST /api/<slug>/notasfiscais/notas-fiscais/notas/` retorna 201 com nota persistida.
  - Cancelamento: `POST /api/<slug>/notasfiscais/notas-fiscais/notas/{id}/cancelar/` atualiza `status=101` e cria `nota_evento`.
  - Transmissão (painel): `POST /api/<slug>/notasfiscais/notas-fiscais/notas/{id}/transmitir/` atualiza `status=100` e metadados.

- Carga e Performance
  - Consultas com filtros e paginação; monitorar tempo e uso de `select_related/prefetch_related` no `NotaViewSet.get_queryset`.
  - Índices: validar uso de índices em `nf_nota_item(nota, produto)` e tabelas de apoio (CFOP/NCM).

- Consistência dos Dados
  - Integridade referencial: `NotaItem` sempre vinculado a `Nota` e `Produtos`; `NotaItemImposto` 1–1 com `NotaItem`.
  - Campos obrigatórios: itens com `quantidade > 0`, `unitario > 0`, `produto` informado.
  - Chave única lógica: combinação `empresa+filial+modelo+serie+numero` não se repete.

- ETL
  - Leituras do legado (`nfevv`, `infvv`) só leitura (`managed=False`).
  - Exigir consistência em transformação para `nf_*` quando aplicável.

