;(() => {
  const byId = (id) => document.getElementById(id)
  const getSlug = () => {
    const el = document.getElementById('financeiro-pedido')
    const tpl = el?.dataset?.slug || ''
    if (tpl) return tpl
    try {
      const p = location.pathname.split('/')
      return p.length > 2 ? p[2] : localStorage.getItem('slug') || ''
    } catch (e) {
      return localStorage.getItem('slug') || ''
    }
  }
  const getCSRF = () => {
    const m = document.cookie.match(/csrftoken=([^;]+)/)
    return m ? m[1] : ''
  }
  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem('access')
    const headers = Object.assign({}, options.headers || {})
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch(url, Object.assign({}, options, { headers }))
  }
  const fmtBRL = (v) => {
    const n = Number(v || 0)
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  const mount = () => {
    const root = document.getElementById('financeiro-pedido')
    if (!root) return
    const slug = getSlug()
    let nume = root.dataset.pediNume
    let forn = root.dataset.pediForn
    let tota = root.dataset.pediTota

    nume = nume || document.getElementById('id_pedi_nume')?.value || ''
    forn = forn || document.getElementById('id_pedi_forn')?.value || ''
    tota = tota || document.getElementById('id_pedi_tota')?.value || ''

    const parcelasEl = byId('fin-parcelas')
    const dataBaseEl = byId('fin-data-base')
    const formaEl = byId('fin-forma')
    const btnGerar = byId('fin-btn-gerar')
    const btnConsultar = byId('fin-btn-consultar')
    const btnRemover = byId('fin-btn-remover')
    const btnAtualizar = byId('fin-btn-atualizar')
    const edits = new Map()
    const body = byId('fin-titulos-body')
    const totalEl = byId('fin-total')
    const resSub = byId('fin-resumo-subtotal')
    const resDesc = byId('fin-resumo-desconto')
    const resTot = byId('fin-resumo-total')
    const resRest = byId('fin-resumo-restante')
    const entradaEl = byId('fin-entrada')
    const formaOpts = [
      { v: '00', l: 'DUPLICATA' },
      { v: '01', l: 'CHEQUE' },
      { v: '02', l: 'PROMISSÓRIA' },
      { v: '03', l: 'RECIBO' },
      { v: '50', l: 'CHEQUE PRÉ' },
      { v: '51', l: 'CARTÃO CRÉDITO' },
      { v: '52', l: 'CARTÃO DÉBITO' },
      { v: '53', l: 'BOLETO' },
      { v: '54', l: 'DINHEIRO' },
      { v: '55', l: 'DEPÓSITO' },
      { v: '56', l: 'À VISTA' },
      { v: '60', l: 'PIX' },
    ]

    if (dataBaseEl && !dataBaseEl.value) {
      const d = new Date()
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(
        2,
        '0'
      )}-${String(d.getDate()).padStart(2, '0')}`
      dataBaseEl.value = iso
    }

    const syncResumo = () => {
      let sub = document.getElementById('id_pedi_topr')?.value
      let des = document.getElementById('id_pedi_desc')?.value
      let tot = document.getElementById('id_pedi_tota')?.value
      if (sub == null) sub = root.dataset.pediTopr || 0
      if (des == null) des = root.dataset.pediDesc || 0
      if (tot == null || tot === '') tot = root.dataset.pediTota || 0
      if (resSub) resSub.textContent = fmtBRL(sub)
      if (resDesc) resDesc.textContent = fmtBRL(des)
      if (resTot) resTot.textContent = fmtBRL(tot)
      const entrada = Number(entradaEl?.value || 0)
      const restante = Math.max(Number(tot || 0) - entrada, 0)
      if (resRest) resRest.textContent = fmtBRL(restante)
    }
    syncResumo()
    ;['id_pedi_topr', 'id_pedi_desc', 'id_pedi_tota'].forEach((id) => {
      const el = document.getElementById(id)
      el?.addEventListener('input', syncResumo)
      el?.addEventListener('change', syncResumo)
    })
    entradaEl?.addEventListener('input', syncResumo)
    entradaEl?.addEventListener('change', syncResumo)

    // Ajuste UX: default de forma conforme tipo financeiro selecionado
    try {
      const tipoFinSelect = document.getElementById('id_pedi_fina')
      const mapFormaPorTipo = {
        // se necessário, mapeia tipos para formas padrão
        // 'AVISTA': '56', 'APRAZO': '53'
      }
      tipoFinSelect?.addEventListener('change', () => {
        const tipo = (tipoFinSelect.value || '').toUpperCase()
        const padrao = mapFormaPorTipo[tipo]
        if (padrao && formaEl) formaEl.value = padrao
      })
    } catch (e) {}

    const consultar = async () => {
      if (!nume) {
        alert('Salve o pedido para consultar os títulos.')
        return
      }
      const url = `/api/${slug}/pedidos/consultar-titulos-pedido/${encodeURIComponent(
        nume
      )}/`
      const resp = await authFetch(url, { method: 'GET' })
      const data = await resp.json()
      const titulos = data.titulos || []
      body.innerHTML = ''
      titulos.forEach((t) => {
        const tr = document.createElement('tr')
        const editBtn =
          String(t.aberto || '').toUpperCase() === 'A'
            ? `<button type="button" class="btn btn-sm btn-outline-secondary fin-edit" data-parcela="${t.parcela}"><i class="bi bi-pencil"></i></button>`
            : ''
        tr.innerHTML = `
          <td>${t.parcela} ${editBtn}</td>
          <td class="text-end">R$ ${Number(t.valor || 0).toFixed(2)}</td>
          <td>${t.vencimento || ''}</td>
          <td data-forma="${t.forma_pagamento || ''}">${
          t.forma_pagamento || ''
        }</td>
          <td>${String(t.status || '').toUpperCase()}</td>
        `
        tr.dataset.aberto = t.aberto || ''
        tr.dataset.valor = t.valor || ''
        tr.dataset.vencimento = t.vencimento || ''
        tr.dataset.forma = t.forma_pagamento || ''
        body.appendChild(tr)
      })
      const total = Number(data.total || 0)
      totalEl.textContent = `R$ ${total.toFixed(2)}`
      const totPedido = Number(
        document.getElementById('id_pedi_tota')?.value ||
          root.dataset.pediTota ||
          0
      )
      const restante = Math.max(totPedido - total, 0)
      if (resRest) resRest.textContent = fmtBRL(restante)
      btnAtualizar?.classList.remove('d-none')
      if (btnAtualizar) btnAtualizar.disabled = true
      edits.clear()
    }

    const gerar = async () => {
      if (!nume) {
        alert('Salve o pedido para gerar os títulos.')
        return
      }
      if (!forn) {
        alert('Selecione o cliente antes de gerar os títulos.')
        return
      }
      tota = document.getElementById('id_pedi_tota')?.value || tota
      const parcelas = Math.max(Number(parcelasEl.value || 1), 1)
      const forma = (formaEl.value || '').trim()
      const entrada = Math.max(Number(entradaEl?.value || 0), 0)
      if (entrada > Number(tota || 0)) {
        alert('Entrada não pode ser maior que o total.')
        return
      }
      const url = `/api/${slug}/pedidos/gerar-titulos-pedido/`
      const payload = {
        pedi_nume: Number(nume),
        pedi_forn: Number(forn),
        pedi_tota: String(tota),
        entrada: String(entrada),
        pedi_form_rece: forma,
        parcelas: parcelas,
        data_base: (dataBaseEl.value || '').trim(),
      }
      const resp = await authFetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF(),
        },
        body: JSON.stringify(payload),
      })
      if (!resp.ok) {
        let msg = 'Erro ao gerar títulos'
        try {
          const data = await resp.json()
          msg = data?.detail || msg
        } catch (e) {
          const txt = await resp.text()
          if (txt) msg = txt
        }
        alert(msg)
        return
      }
      await consultar()
    }

    const remover = async () => {
      if (!nume) {
        alert('Salve o pedido para remover os títulos.')
        return
      }
      const url = `/api/${slug}/pedidos/remover-titulos-pedido/`
      const resp = await authFetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF(),
        },
        body: JSON.stringify({ pedi_nume: Number(nume) }),
      })
      if (!resp.ok) {
        const txt = await resp.text()
        alert(txt || 'Erro ao remover títulos')
        return
      }
      body.innerHTML = ''
      totalEl.textContent = ''
    }

    btnConsultar?.addEventListener('click', consultar)
    btnGerar?.addEventListener('click', gerar)
    btnRemover?.addEventListener('click', remover)

    body.addEventListener('click', (e) => {
      const btn = e.target.closest('.fin-edit')
      if (!btn) return
      const parcela = Number(btn.dataset.parcela)
      const tr = btn.closest('tr')
      if (String(tr.dataset.aberto || '').toUpperCase() !== 'A') {
        alert('Título não pode ser editado.')
        return
      }
      const tdValor = tr.children[1]
      const tdVenc = tr.children[2]
      const tdForma = tr.children[3]
      const valorAtual = Number(tr.dataset.valor || 0)
      const vencAtual = tr.dataset.vencimento || tdVenc.textContent || ''
      const formaAtual =
        tr.dataset.forma || tdForma.dataset.forma || tdForma.textContent || ''
      tdValor.innerHTML = `<input type="number" step="0.01" class="form-control form-control-sm text-end" value="${String(
        valorAtual
      )}">`
      tdVenc.innerHTML = `<input type="date" class="form-control form-control-sm" value="${(
        vencAtual || ''
      ).slice(0, 10)}">`
      tdForma.innerHTML = `<select class="form-select form-select-sm">${formaOpts
        .map(
          (o) =>
            `<option value="${o.v}" ${o.v === formaAtual ? 'selected' : ''}>${
              o.v
            }</option>`
        )
        .join('')}</select>`
      btnAtualizar?.classList.remove('d-none')
      const inputValor = tdValor.querySelector('input')
      const inputVenc = tdVenc.querySelector('input')
      const inputForma = tdForma.querySelector('select')
      const storeEdit = () => {
        const v = Number(inputValor.value || 0)
        const d = inputVenc.value || vencAtual
        const f = inputForma.value || formaAtual
        edits.set(parcela, { valor: v, vencimento: d, forma_pagamento: f })
        btnAtualizar?.classList.remove('d-none')
        if (btnAtualizar) btnAtualizar.disabled = false
      }
      inputValor.addEventListener('change', storeEdit)
      inputValor.addEventListener('input', storeEdit)
      inputVenc.addEventListener('change', storeEdit)
      inputForma.addEventListener('change', storeEdit)
    })

    btnAtualizar?.addEventListener('click', async () => {
      if (!nume) return
      if (edits.size === 0) {
        alert('Nenhuma alteração pendente')
        return
      }
      for (const [parcela, ch] of edits.entries()) {
        const url = `/api/${slug}/pedidos/atualizar-titulo-pedido/`
        const resp = await authFetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRF(),
          },
          body: JSON.stringify({
            pedi_nume: Number(nume),
            parcela,
            valor: String(ch.valor),
            vencimento: ch.vencimento,
            forma_pagamento: ch.forma_pagamento,
          }),
        })
        if (!resp.ok) {
          const txt = await resp.text()
          alert(txt || 'Falha ao atualizar título')
          return
        }
      }
      edits.clear()
      btnAtualizar?.classList.add('d-none')
      await consultar()
    })
  }

  document.addEventListener('DOMContentLoaded', mount)
})()
