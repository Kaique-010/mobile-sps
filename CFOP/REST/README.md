## API CFOP (REST) — Como o Front deve consumir

Rotas: [urls.py](file:///d:/mobile-sps/CFOP/REST/urls.py#L1-L10)  
Serializer: [serializers.py](file:///d:/mobile-sps/CFOP/REST/serializers.py#L1-L91)  
ViewSet: [viewsets.py](file:///d:/mobile-sps/CFOP/REST/viewsets.py#L1-L108)

### Base URL

A rota do app é incluída em `/api/<slug>/cfop/`.

Endpoints gerados pelo router:

- `GET /api/<slug>/cfop/`
- `POST /api/<slug>/cfop/`
- `GET /api/<slug>/cfop/<cfop_id>/`
- `PUT /api/<slug>/cfop/<cfop_id>/`
- `PATCH /api/<slug>/cfop/<cfop_id>/`
- `DELETE /api/<slug>/cfop/<cfop_id>/`

Compatibilidade (legado):

- `GET /api/<slug>/cfop/cfop/`
- `POST /api/<slug>/cfop/cfop/`
- `GET /api/<slug>/cfop/cfop/<cfop_id>/`
- `PUT /api/<slug>/cfop/cfop/<cfop_id>/`
- `PATCH /api/<slug>/cfop/cfop/<cfop_id>/`
- `DELETE /api/<slug>/cfop/cfop/<cfop_id>/`

### Contexto de empresa

O backend tenta descobrir a empresa assim:

1. Query param `empresa_id`
2. Header `X-Empresa`
3. Session `empresa_id`
4. Header `Empresa_id`

Na prática, para o front, use sempre:

- `X-Empresa: <numero>`

ou, se preferir via query string:

- `?empresa_id=<numero>`

### Formato de dados (resposta padrão)

O CFOP sempre volta no formato agrupado em 2 listas:

- `campos_padrao`: campos “normais” do CFOP
- `incidencias`: flags/booleans de incidência/geração/base/totalização

Exemplo (`GET /api/<slug>/cfop/<id>/`):

```json
{
  "cfop_id": 123,
  "campos_padrao": [
    {
      "campo": "cfop_empr",
      "valor": 1,
      "label": "Empresa",
      "help_text": "ID da empresa vinculada"
    },
    {
      "campo": "cfop_codi",
      "valor": "5102",
      "label": "Código CFOP",
      "help_text": "Código fiscal de operação (ex: 5102). Deve ter 4 dígitos."
    },
    {
      "campo": "cfop_desc",
      "valor": "Venda de mercadoria",
      "label": "Descrição",
      "help_text": "Descrição da operação"
    }
  ],
  "incidencias": [
    {
      "campo": "cfop_exig_ipi",
      "valor": false,
      "label": "Exige IPI",
      "help_text": "Calcula e destaca IPI na nota"
    },
    {
      "campo": "cfop_exig_icms",
      "valor": true,
      "label": "Exige ICMS",
      "help_text": "Calcula e destaca ICMS na nota"
    },
    {
      "campo": "cfop_exig_pis_cofins",
      "valor": true,
      "label": "Exige PIS/COFINS",
      "help_text": "Calcula e destaca PIS/COFINS na nota"
    },
    {
      "campo": "cfop_exig_cbs",
      "valor": false,
      "label": "Exige CBS",
      "help_text": "Calcula CBS (Reforma Tributária)"
    },
    {
      "campo": "cfop_exig_ibs",
      "valor": false,
      "label": "Exige IBS",
      "help_text": "Calcula IBS (Reforma Tributária)"
    },
    {
      "campo": "cfop_gera_st",
      "valor": false,
      "label": "Gera ST",
      "help_text": "Calcula Substituição Tributária"
    },
    {
      "campo": "cfop_gera_difal",
      "valor": false,
      "label": "Gera DIFAL",
      "help_text": "Calcula Diferencial de Alíquota"
    },
    {
      "campo": "cfop_icms_base_inclui_ipi",
      "valor": false,
      "label": "Base ICMS inclui IPI",
      "help_text": "Adiciona valor do IPI na base do ICMS"
    },
    {
      "campo": "cfop_st_base_inclui_ipi",
      "valor": false,
      "label": "Base ST inclui IPI",
      "help_text": "Adiciona valor do IPI na base do ST"
    },
    {
      "campo": "cfop_ipi_tota_nf",
      "valor": false,
      "label": "IPI compõe Total NF",
      "help_text": "Soma o valor do IPI ao total da nota"
    },
    {
      "campo": "cfop_st_tota_nf",
      "valor": false,
      "label": "ST compõe Total NF",
      "help_text": "Soma o valor do ST ao total da nota"
    }
  ]
}
```

Observações:

- `label` e `help_text` são metadados para UI (texto de campo / dica).
- `valor` em `incidencias` é sempre boolean.
- O backend sempre retorna todas as incidências definidas no serializer, mesmo que `false`.

### Listagem com busca (lista “completa”)

`GET /api/<slug>/cfop/?q=<texto>`

- Filtra por `cfop_codi` ou `cfop_desc` (icontains).
- Quando `X-Empresa` (ou `empresa_id`) é informado, filtra por `cfop_empr`.
- Retorna o mesmo formato agrupado (cada item tem `cfop_id`, `campos_padrao`, `incidencias`).

### Listagem para select/autocomplete (lista “leve”)

`GET /api/<slug>/cfop/?select=1&q=<texto>`

Retorno (máximo 20):

```json
[
  { "value": "123", "label": "5102 • Venda de mercadoria" },
  { "value": "124", "label": "6102 • Venda interestadual" }
]
```

Use este endpoint quando você só precisa alimentar um select/autocomplete.

### Criar CFOP

`POST /api/<slug>/cfop/`

Você pode enviar de 2 jeitos:

1. Formato agrupado (recomendado para o front, pois espelha o retorno):

```json
{
  "campos_padrao": [
    { "campo": "cfop_codi", "valor": "5102" },
    { "campo": "cfop_desc", "valor": "Venda de mercadoria" }
  ],
  "incidencias": [
    { "campo": "cfop_exig_icms", "valor": true },
    { "campo": "cfop_exig_ipi", "valor": false }
  ]
}
```

2. Formato “flat” (campos direto no JSON, útil para debug/integração):

```json
{
  "cfop_codi": "5102",
  "cfop_desc": "Venda de mercadoria",
  "cfop_exig_icms": true,
  "cfop_exig_ipi": false
}
```

Como `cfop_empr` é definido:

- Se você enviar `X-Empresa` (ou `empresa_id`), o backend força `cfop_empr` para esse valor.
- Se não enviar, você pode incluir `cfop_empr` em `campos_padrao` ou no formato flat.

### Atualizar CFOP (PUT/PATCH)

`PUT /api/<slug>/cfop/<id>/` (substituição)  
`PATCH /api/<slug>/cfop/<id>/` (parcial)

Aceita os mesmos 2 formatos do POST (agrupado ou flat).

Regras:

- Se `X-Empresa` (ou `empresa_id`) vier, o backend força `cfop_empr` para esse valor.
- Flags em `incidencias` aceitam `true/false` ou strings comuns (`"true"`, `"false"`, `"1"`, `"0"`).
