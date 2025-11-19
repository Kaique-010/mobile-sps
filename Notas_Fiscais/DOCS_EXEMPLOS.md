# Exemplos de Uso

## API – Listar Notas

```bash
curl -X GET "http://localhost:8000/notas-fiscais/notas/?empresa=1&filial=1"
```

## API – Criar Nota

```bash
curl -X POST "http://localhost:8000/notas-fiscais/notas/" \
  -H "Content-Type: application/json" \
  -d '{
    "modelo": "55",
    "serie": "1",
    "numero": 1001,
    "tipo_operacao": 1,
    "finalidade": 1,
    "ambiente": 2,
    "destinatario": 123,
    "itens": [
      {
        "produto": 456,
        "quantidade": 2.0,
        "unitario": 50.0,
        "desconto": 0,
        "cfop": "5102",
        "ncm": "12345678",
        "cest": null,
        "cst_icms": "00",
        "cst_pis": "01",
        "cst_cofins": "01"
      }
    ],
    "impostos": [
      {
        "icms_base": 100.00,
        "icms_aliquota": 18.00,
        "icms_valor": 18.00
      }
    ],
    "transporte": {
      "modalidade_frete": 9,
      "transportadora": null,
      "placa_veiculo": "ABC1D23",
      "uf_veiculo": "SP"
    }
  }'
```

## API – Atualizar Nota

```bash
curl -X PUT "http://localhost:8000/notas-fiscais/notas/1/" \
  -H "Content-Type: application/json" \
  -d '{
    "modelo": "55",
    "serie": "1",
    "numero": 1001,
    "tipo_operacao": 1,
    "destinatario": 123,
    "itens": [
      {
        "produto": 456,
        "quantidade": 3.0,
        "unitario": 45.0,
        "desconto": 0,
        "cfop": "5102",
        "ncm": "12345678",
        "cest": null,
        "cst_icms": "00",
        "cst_pis": "01",
        "cst_cofins": "01"
      }
    ]
  }'
```

## API – Cancelar Nota

```bash
curl -X POST "http://localhost:8000/notas-fiscais/notas/1/cancelar/" \
  -H "Content-Type: application/json" \
  -d '{
    "descricao": "Cancelamento por erro de emissão"
  }'
```

## Views Web

- Lista: `notas/nota_list.html` via `NotaListView` (`Notas_Fiscais/Web/Views/nota/nota_list.py:1`).
- Formulário de criação/edição: `notas/nota_form.html` via `NotaCreateView` e `NotaUpdateView`.