Manual de Uso

- Executar a Integração
  - Criar notas via REST em `/api/<slug>/notasfiscais/notas-fiscais/notas/` com payload contendo cabeçalho, destinatário (`enti_clie`) e itens.
  - Emitir diretamente uma nota existente em `/api/<slug>/notasfiscais/notas-fiscais/emitir/<slug>/<nota_id>/`.
  - Alternativa: comando `python manage.py emitir_notas_teste` para emissão dos modelos 55 e 65 com dados reais.

- Parâmetros Configuráveis
  - `modelo`: `55` NF-e ou `65` NFC-e.
  - `ambiente`: `1` produção ou `2` homologação.
  - `tipo_operacao`: `0` entrada, `1` saída.
  - `finalidade`: `1` normal, `2` complementar, `3` ajuste, `4` devolução.
  - Transporte: `modalidade_frete`, `transportadora`, `placa_veiculo`, `uf_veiculo`.

- Procedimentos para Ajustes Futuros
  - CFOP/NCM: ajustar `CFOP.models` e tabelas de mapeamento/aliquotas; overrides em `NCM_CFOP_DIF`.
  - Cálculo: refinar `CalculoImpostosService` para novas regras (CBS/IBS/FCP) e cenários de ST/DIFAL.
  - DTO/Emissão: ampliar `dominio.builder` e `construir_nfe_pynfe` para novos campos (ex.: informações adicionais, adicionais de frete).
  - Eventos: criar endpoints específicos para CC-e, cancelamento com justificativa e inutilização.

- Solução de Problemas Comuns
  - Erro de certificado: conferir `Filiais.empr_cert_digi` e `empr_senh_cert`.
  - CFOP/NCM inválidos: validar existência em `CFOP` e `Produtos.prod_ncm`; revisar `MapaCFOP`.
  - Falha de conexão SEFAZ: verificar rede, ambiente correto e dependências do PyNFe.
  - Status divergente: garantir que cancelamento usa `101` e autorização `100`.

- Exemplos Práticos
  - Criação de NF-e 55
    - `POST /api/<slug>/notasfiscais/notas-fiscais/notas/`
    - Corpo mínimo: `{"modelo":"55","serie":"001","numero":123,"tipo_operacao":1,"finalidade":1,"ambiente":2,"destinatario":<enti_clie>,"itens":[{"produto":"<prod_codi>","quantidade":"1","unitario":"100.00","desconto":"0","cfop":"5102","ncm":"<ncm>","cst_icms":"000","cst_pis":"01","cst_cofins":"01"}]}`
  - Emissão de nota existente
    - `GET /api/<slug>/notasfiscais/notas-fiscais/emitir/<slug>/<nota_id>/`

