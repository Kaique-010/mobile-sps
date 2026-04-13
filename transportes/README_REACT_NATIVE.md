# API Transportes (CT-e e MDF-e) para React Native

Este guia descreve como consumir as rotas REST de emissão de **CT-e** e **MDF-e** no app React Native.

## Base URL

As rotas ficam no módulo `transportes` usando DRF Router.

```text
/api/{slug}/transportes/api/
```

Exemplo:

```text
https://seu-dominio.com/api/minha-licenca/transportes/api/
```

> O backend resolve multi-banco pelo slug da licença e usa o padrão de roteamento por banco.

---

## Autenticação

As rotas exigem usuário autenticado (`IsAuthenticated`).
Envie `Authorization` no padrão já adotado no app (Token/JWT/Session).

---

## Endpoints principais

## CT-e

### 1) Listar CT-es

`GET /ctes/`

### 2) Criar rascunho

`POST /ctes/`

### 3) Atualizar CT-e

`PATCH /ctes/{id}/`

### 4) Emitir CT-e (finalizado)

`POST /ctes/{id}/emitir/`

Retorno esperado:

```json
{
  "status": "autorizado|recebido|processando|rejeitado",
  "mensagem": "...",
  "protocolo": "...",
  "recibo": "..."
}
```

### 5) Calcular impostos do CT-e

`GET /ctes/{id}/calcular-impostos/?cfop={cfop_id}`

---

## MDF-e

### 1) Listar MDF-es

`GET /mdfes/`

### 2) Criar MDF-e

`POST /mdfes/`

### 3) Atualizar MDF-e

`PATCH /mdfes/{id}/`

### 4) Emitir MDF-e (finalizado)

`POST /mdfes/{id}/emitir/`

> Esta rota usa o serviço de emissão e gera XML assinado + chave.

Alternativa equivalente:

`POST /mdfes/{id}/gerar-xml/`

### 5) Encerrar MDF-e manualmente (finalizado com service)

`POST /mdfes/{id}/encerrar/`

Payload opcional:

```json
{
  "uf": "SP",
  "cmun": "3550308"
}
```

### 6) Encerrar MDF-e automático (finalizado com service)

`POST /mdfes/{id}/encerrar-automatico/`

### 7) Gerenciar documentos vinculados ao MDF-e

- `GET /mdfes/{id}/documentos/`
- `POST /mdfes/{id}/documentos/`

Payload POST:

```json
{
  "documentos": [
    {
      "tipo_doc": "CTE",
      "chave": "...44-digitos...",
      "cmun_descarga": "3550308",
      "xmun_descarga": "SAO PAULO"
    }
  ]
}
```

---

## Exemplo React Native (fetch)

```ts
const API_BASE = 'https://seu-dominio.com/api/minha-licenca/transportes/api';

export async function emitirCte(id: number, token: string) {
  const response = await fetch(`${API_BASE}/ctes/${id}/emitir/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Erro ao emitir CT-e: ${response.status}`);
  }

  return response.json();
}

export async function emitirMdfe(id: number, token: string) {
  const response = await fetch(`${API_BASE}/mdfes/${id}/emitir/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Erro ao emitir MDF-e: ${response.status}`);
  }

  return response.json();
}

export async function encerrarMdfe(id: number, token: string, payload?: { uf?: string; cmun?: string }) {
  const response = await fetch(`${API_BASE}/mdfes/${id}/encerrar/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload || {}),
  });

  if (!response.ok) {
    throw new Error(`Erro ao encerrar MDF-e: ${response.status}`);
  }

  return response.json();
}
```

---

## Fluxo sugerido no app

1. Criar CT-e/MDF-e.
2. Preencher dados necessários por `PATCH`.
3. Para MDF-e, enviar documentos no endpoint `/documentos/`.
4. Emitir (`/emitir/`).
5. Para MDF-e após viagem, encerrar (`/encerrar/` ou `/encerrar-automatico/`).

---

## Códigos de retorno

- `200`: operação processada com sucesso.
- `400`: payload inválido.
- `401/403`: falha de autenticação/permissão.
- `500`: erro interno (ver campo `error`).
