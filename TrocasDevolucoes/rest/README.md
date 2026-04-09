# API REST — Trocas e Devoluções

## Base URL
`/api/<slug>/trocas-devolucoes/`

## Endpoints

### Listar
- `GET /api/<slug>/trocas-devolucoes/devolucoes/`
- Filtros suportados:
  - `tdvl_empr`
  - `tdvl_fili`
  - `tdvl_pdor`
  - `tdvl_stat`

### Criar
- `POST /api/<slug>/trocas-devolucoes/devolucoes/`
- Payload:

```json
{
  "tdvl_empr": 1,
  "tdvl_fili": 1,
  "tdvl_pdor": 1024,
  "tdvl_clie": "1001",
  "tdvl_vend": "10",
  "tdvl_data": "2026-04-09",
  "tdvl_tipo": "DEVO",
  "tdvl_stat": "0",
  "tdvl_tode": "150.00",
  "tdvl_tore": "0.00",
  "tdvl_safi": "-150.00",
  "tdvl_obse": "Cliente devolveu por avaria",
  "itens": [
    {
      "itdv_pdor": 1024,
      "itdv_itor": 1,
      "itdv_pror": "PROD001",
      "itdv_qtor": "2.00000",
      "itdv_vlor": "150.00",
      "itdv_moti": "AVARIA"
    }
  ]
}
```

### Detalhar
- `GET /api/<slug>/trocas-devolucoes/devolucoes/<tdvl_nume>/`

### Atualizar
- `PUT/PATCH /api/<slug>/trocas-devolucoes/devolucoes/<tdvl_nume>/`

## Guia para o front-end

1. **Tela de listagem**
   - buscar via `GET` com filtros por empresa/filial/status.
2. **Tela de criação**
   - enviar cabeçalho + array de itens em um único `POST`.
3. **Edição**
   - carregar registro por `GET detail` e salvar por `PUT/PATCH`.
4. **Padrão de nomes**
   - os campos seguem padrão `prefixo_4letras` (ex: `tdvl_empr`, `itdv_pror`).
