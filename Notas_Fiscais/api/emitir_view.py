

from django.http import JsonResponse, HttpResponse
from ..aplicacao.emissao_service import EmissaoService
from core.utils import get_db_from_slug
from core.dominio_handler import tratar_erro
from rest_framework.response import Response as DRFResponse
from ..models import Nota
from ..utils.sefaz_messages import get_sefaz_message
import logging
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
import html as html_module


try:
    from brazilfiscalreport.danfe import Danfe
except ImportError:
    Danfe = None

logger = logging.getLogger(__name__)



def _nfce_40col_html(xml_content: str, largura: int = 40) -> str:
    """
    Gera HTML para impressão de NFC-e no formato cupom 80mm (visual 40 colunas).
    Layout profissional com QR Code escaneável via qrcode.js.
    """
 
    # ── helpers de parsing ────────────────────────────────────────────
    def _strip_ns(tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag
 
    def _find_first(elem, names):
        if elem is None:
            return None
        want = set(names)
        for e in elem.iter():
            if _strip_ns(getattr(e, "tag", "")) in want:
                return e
        return None
 
    def _find_all(elem, name):
        if elem is None:
            return []
        return [e for e in elem.iter() if _strip_ns(getattr(e, "tag", "")) == name]
 
    def _find_text(elem, name, default=""):
        e = _find_first(elem, [name])
        if e is None:
            return default
        return (e.text or "").strip() or default
 
    def _digits(s: str) -> str:
        return "".join(ch for ch in str(s or "") if ch.isdigit())
 
    def _fmt_money(v) -> str:
        try:
            d = Decimal(str(v or "0").replace(",", "."))
        except (InvalidOperation, ValueError):
            d = Decimal("0")
        return f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
 
    def _fmt_qty(v) -> str:
        try:
            d = Decimal(str(v or "0").replace(",", "."))
            # Sem casas desnecessárias se for inteiro
            if d == d.to_integral_value():
                return f"{d:.0f}"
            return f"{d:.3f}".rstrip("0")
        except (InvalidOperation, ValueError):
            return "0"
 
    def _fmt_date(dh: str) -> str:
        """Converte '2026-03-26T14:32:10-03:00' → '26/03/2026  14:32'"""
        if not dh:
            return ""
        dh = dh.replace("T", " ")[:16]
        try:
            date_part, time_part = dh.split(" ")
            y, m, d = date_part.split("-")
            return f"{d}/{m}/{y}  {time_part}"
        except Exception:
            return dh
 
    def _fmt_cnpj(s: str) -> str:
        d = _digits(s)
        if len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return s
 
    def _fmt_cpf(s: str) -> str:
        d = _digits(s)
        if len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        return s
 
    def _fmt_ie(s: str) -> str:
        return s  # manter como está
 
    def _fmt_chave(s: str) -> str:
        """Formata chave 44 dígitos em grupos de 4"""
        d = _digits(s) or s
        grupos = [d[i:i+4] for i in range(0, len(d), 4)]
        mid = len(grupos) // 2
        return " ".join(grupos[:mid]) + "<br>" + " ".join(grupos[mid:])
 
    def _e(s: str) -> str:
        """Escapa HTML"""
        return html_module.escape(str(s or ""))
 
    # ── parse XML ─────────────────────────────────────────────────────
    root = ET.fromstring(xml_content.encode("utf-8", errors="ignore"))
 
    inf_nfe = next(
        (e for e in root.iter() if _strip_ns(getattr(e, "tag", "")) == "infNFe"),
        None,
    )
 
    ide   = _find_first(inf_nfe, ["ide"])
    emit  = _find_first(inf_nfe, ["emit"])
    dest  = _find_first(inf_nfe, ["dest"])
    total = _find_first(inf_nfe, ["total"])
    pag   = _find_first(inf_nfe, ["pag"])
    supl  = _find_first(root, ["infNFeSupl"])
 
    # emitente
    x_nome     = _find_text(emit, "xNome")
    x_fant     = _find_text(emit, "xFant")
    cnpj_emit  = _digits(_find_text(emit, "CNPJ"))
    ie_emit    = _find_text(emit, "IE")
    end_emit   = _find_first(emit, ["enderEmit"])
    end_lgr    = _find_text(end_emit, "xLgr")
    end_nro    = _find_text(end_emit, "nro")
    end_bairro = _find_text(end_emit, "xBairro")
    end_mun    = _find_text(end_emit, "xMun")
    end_uf     = _find_text(end_emit, "UF")
    end_cep    = _digits(_find_text(end_emit, "CEP"))
    fone_emit  = _digits(_find_text(emit, "fone"))
 
    # identificação
    dh_emi = _find_text(ide, "dhEmi")
    n_nf   = _find_text(ide, "nNF")
    serie  = _find_text(ide, "serie")
    tp_amb = _find_text(ide, "tpAmb")
 
    # destinatário
    cpf_dest   = _digits(_find_text(dest, "CPF"))
    cnpj_dest  = _digits(_find_text(dest, "CNPJ"))
    x_nome_dest = _find_text(dest, "xNome")
 
    # totais
    icms_tot = _find_first(total, ["ICMSTot"])
    v_nf    = _find_text(icms_tot, "vNF")
    v_desc  = _find_text(icms_tot, "vDesc", "0")
    v_bc    = _find_text(icms_tot, "vBC",   "0")
 
    # chave
    chave = ""
    if inf_nfe is not None:
        nfe_id = (inf_nfe.attrib.get("Id") or "").strip()
        chave = nfe_id[3:] if nfe_id.startswith("NFe") else nfe_id
 
    # suplemento
    qr_code  = _find_text(supl, "qrCode")
    url_chave = _find_text(supl, "urlChave")
 
    # ── dados auxiliares ──────────────────────────────────────────────
    nome_exibido = _e(x_fant or x_nome or "")
 
    end_linha1 = _e(", ".join(p for p in [end_lgr, end_nro] if p))
    end_linha2 = _e(", ".join(p for p in [end_bairro, end_mun, end_uf] if p))
    if end_cep and len(end_cep) == 8:
        end_linha2 += _e(f" — CEP {end_cep[:5]}-{end_cep[5:]}")
 
    fone_fmt = ""
    if fone_emit:
        f = fone_emit
        if len(f) == 11:
            fone_fmt = f"({f[:2]}) {f[2:7]}-{f[7:]}"
        elif len(f) == 10:
            fone_fmt = f"({f[:2]}) {f[2:6]}-{f[6:]}"
 
    amb_label = "PRODUÇÃO" if tp_amb == "1" else "HOMOLOGAÇÃO"
    amb_class = "prod" if tp_amb == "1" else "hom"
 
    doc_dest = cpf_dest or cnpj_dest
    doc_dest_fmt = ""
    if cpf_dest:
        doc_dest_fmt = _fmt_cpf(cpf_dest)
    elif cnpj_dest:
        doc_dest_fmt = _fmt_cnpj(cnpj_dest)
 
    # ── itens ─────────────────────────────────────────────────────────
    dets = _find_all(inf_nfe, "det")
    items_html = ""
    qtd_total_itens = 0
    for det in dets:
        prod  = _find_first(det, ["prod"])
        c_prod = _e(_find_text(prod, "cProd"))
        x_prod = _e(_find_text(prod, "xProd"))
        q_com  = _find_text(prod, "qCom", "0")
        v_un   = _find_text(prod, "vUnCom", "0")
        v_prod = _find_text(prod, "vProd", "0")
        u_com  = _e(_find_text(prod, "uCom", "UN"))
 
        try:
            qtd_total_itens += Decimal(str(q_com).replace(",", "."))
        except Exception:
            pass
 
        items_html += f"""
        <div class="item">
          <div class="item-nome">{c_prod} {x_prod}</div>
          <div class="item-row">
            <span class="item-calc">{_e(_fmt_qty(q_com))} {u_com} × R$ {_e(_fmt_money(v_un))}</span>
            <span class="item-total">R$ {_e(_fmt_money(v_prod))}</span>
          </div>
        </div>
        <hr class="sep-items">"""
 
    # ── pagamentos ────────────────────────────────────────────────────
    PAG_LABELS = {
        "01": "Dinheiro", "02": "Cheque", "03": "Cartão de Crédito",
        "04": "Cartão de Débito", "05": "Crédito Loja", "10": "Vale Alimentação",
        "11": "Vale Refeição", "12": "Vale Presente", "13": "Vale Combustível",
        "15": "Boleto", "17": "PIX", "90": "Sem Pagamento",
        "99": "Outros",
    }
    det_pags = _find_all(pag, "detPag")
    pags_html = ""
    v_pag_total = Decimal("0")
    for dp in det_pags:
        t_pag = _find_text(dp, "tPag")
        v_pag = _find_text(dp, "vPag", "0")
        label = PAG_LABELS.get(t_pag, f"Forma {t_pag}")
        try:
            v_pag_total += Decimal(str(v_pag).replace(",", "."))
        except Exception:
            pass
        pags_html += f"""
        <div class="pag-row">
          <span>{_e(label)}</span>
          <span>R$ {_e(_fmt_money(v_pag))}</span>
        </div>"""
 
    # troco
    troco_html = ""
    try:
        troco = v_pag_total - Decimal(str(v_nf or "0").replace(",", "."))
        if troco > 0:
            troco_html = f"""
        <div class="pag-row troco">
          <span>Troco</span>
          <span>R$ {_e(_fmt_money(str(troco)))}</span>
        </div>"""
    except Exception:
        pass
 
    # ── QR Code (JS) ─────────────────────────────────────────────────
    qr_target = qr_code or url_chave or chave
    qr_script = ""
    qr_block  = ""
    if qr_target:
        qr_json   = qr_target.replace("\\", "\\\\").replace("`", "\\`")
        qr_script = f"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
  (function(){{
    var el = document.getElementById('qr-container');
    if(!el || typeof QRCode === 'undefined') return;
    new QRCode(el, {{
      text: `{qr_json}`,
      width: 160, height: 160,
      colorDark: '#000000', colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.M
    }});
  }})();
</script>"""
 
        url_exib = _e(url_chave or "")
        url_row  = (
            f'<div class="consulta-url">{url_exib}</div>'
            if url_exib else ""
        )
        qr_block = f"""
      <hr class="sep">
      <div class="secao-title">Consulte sua NFC-e</div>
      <div class="qr-area">
        <div id="qr-container"></div>
        {url_row}
      </div>"""
 
    # ── chave formatada ───────────────────────────────────────────────
    chave_html = ""
    if chave:
        chave_html = f"""
      <hr class="sep">
      <div class="secao-title">Chave de Acesso</div>
      <div class="chave-bloco">{_fmt_chave(chave)}</div>"""
 
    # ── HTML final ───────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NFC-e Nº {_e(n_nf)}</title>
  <style>
    @page {{
      size: 80mm auto;
      margin: 0;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 11px;
      color: #111;
      background: #fff;
      padding: 10px 12px 24px;
      width: 302px;
      margin: 0 auto;
      line-height: 1.55;
    }}
 
    /* cabeçalho */
    .empresa-nome {{
      font-size: 13.5px;
      font-weight: 700;
      text-align: center;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 2px;
    }}
    .empresa-info {{
      font-size: 10px;
      text-align: center;
      color: #333;
      line-height: 1.5;
    }}
 
    /* separadores */
    .sep {{
      border: none;
      border-top: 1px dashed #999;
      margin: 7px 0;
    }}
    .sep-solid {{
      border: none;
      border-top: 1px solid #444;
      margin: 7px 0;
    }}
    .sep-items {{
      border: none;
      border-top: 1px dotted #ccc;
      margin: 4px 0;
    }}
 
    /* identificação da NFC-e */
    .nfce-titulo {{
      font-size: 13px;
      font-weight: 700;
      text-align: center;
      letter-spacing: 2px;
      margin: 3px 0 2px;
    }}
    .nfce-info {{
      font-size: 10px;
      text-align: center;
      color: #444;
    }}
    .badge-amb {{
      display: inline-block;
      border: 1.5px solid #444;
      border-radius: 2px;
      font-size: 9px;
      font-weight: 700;
      padding: 1px 6px;
      letter-spacing: 1px;
      color: #222;
      margin-top: 2px;
    }}
    .badge-amb.hom {{
      border-color: #b00;
      color: #b00;
    }}
 
    /* destinatário */
    .secao-title {{
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: #555;
      text-transform: uppercase;
      margin-bottom: 2px;
    }}
    .dest-row {{
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
    }}
 
    /* cabeçalho dos itens */
    .itens-header {{
      display: grid;
      grid-template-columns: 1fr auto;
      font-size: 9px;
      font-weight: 700;
      color: #555;
      letter-spacing: 0.4px;
      text-transform: uppercase;
      padding: 0 0 3px;
      border-bottom: 1px solid #888;
      margin-bottom: 4px;
    }}
 
    /* item */
    .item {{ margin-bottom: 1px; }}
    .item-nome {{
      font-size: 10.5px;
      font-weight: 600;
      color: #111;
      margin-bottom: 1px;
    }}
    .item-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }}
    .item-calc {{
      font-size: 10px;
      color: #555;
      padding-left: 4px;
    }}
    .item-total {{
      font-size: 10.5px;
      font-weight: 700;
    }}
 
    /* resumo */
    .resumo-row {{
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
      color: #333;
      margin: 1px 0;
    }}
    .total-linha {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin: 4px 0;
    }}
    .total-label {{
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .total-valor {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
 
    /* pagamentos */
    .pag-row {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      margin: 1px 0;
    }}
    .troco {{
      font-weight: 700;
      border-top: 1px dashed #ccc;
      padding-top: 3px;
      margin-top: 2px;
    }}
 
    /* chave e QR */
    .chave-bloco {{
      font-size: 9px;
      color: #333;
      text-align: center;
      line-height: 1.7;
      letter-spacing: 0.2px;
      word-break: break-all;
    }}
    .qr-area {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      margin: 4px 0;
    }}
    #qr-container img, #qr-container canvas {{
      display: block;
    }}
    .consulta-url {{
      font-size: 8.5px;
      color: #555;
      text-align: center;
      word-break: break-all;
    }}
 
    /* rodapé */
    .rodape {{
      font-size: 10px;
      text-align: center;
      color: #555;
      margin-top: 8px;
    }}
 
    /* impressão */
    @media print {{
      body {{
        width: 80mm;
        padding: 6px 10px 20px;
      }}
    }}
  </style>
</head>
<body onload="window.print()">
 
  <!-- CABEÇALHO EMITENTE -->
  <div class="empresa-nome">{nome_exibido}</div>
  <div class="empresa-info">
    CNPJ: {_e(_fmt_cnpj(cnpj_emit))}<br>
    {"IE: " + _e(_fmt_ie(ie_emit)) + "<br>" if ie_emit else ""}
    {_e(end_linha1)}<br>
    {_e(end_linha2)}
    {"<br>Tel: " + _e(fone_fmt) if fone_fmt else ""}
  </div>
 
  <hr class="sep-solid">
 
  <!-- IDENTIFICAÇÃO NFC-e -->
  <div class="nfce-titulo">NFC-e</div>
  <div class="nfce-info">
    Nº {_e(n_nf)} &nbsp;|&nbsp; Série {_e(serie)}<br>
    {_e(_fmt_date(dh_emi))}
  </div>
  <div style="text-align:center;margin-top:4px">
    <span class="badge-amb {amb_class}">{_e(amb_label)}</span>
  </div>
 
  {f'''<hr class="sep">
  <div class="secao-title">Consumidor</div>
  <div class="dest-row">
    <span>{_e(doc_dest_fmt) or "Não Identificado"}</span>
    {"<span>" + _e(x_nome_dest) + "</span>" if x_nome_dest else ""}
  </div>''' if doc_dest or x_nome_dest else ""}
 
  <hr class="sep">
 
  <!-- ITENS -->
  <div class="itens-header">
    <span>Descrição</span>
    <span>Total</span>
  </div>
 
  {items_html}
 
  <!-- TOTAIS -->
  <div class="resumo-row">
    <span>Qtd. itens</span>
    <span>{len(dets)}</span>
  </div>
  <div class="resumo-row">
    <span>Desconto</span>
    <span>R$ {_e(_fmt_money(v_desc))}</span>
  </div>
 
  <hr class="sep-solid" style="margin:6px 0">
  <div class="total-linha">
    <span class="total-label">TOTAL</span>
    <span class="total-valor">R$ {_e(_fmt_money(v_nf))}</span>
  </div>
 
  <hr class="sep" style="margin:6px 0">
 
  <!-- PAGAMENTOS -->
  {pags_html}
  {troco_html}
 
  <!-- CHAVE DE ACESSO -->
  {chave_html}
 
  <!-- QR CODE -->
  {qr_block}
 
  <hr class="sep">
  <div class="rodape">✦ Obrigado pela preferência ✦</div>
 
</body>
{qr_script}
</html>"""

def emitir_nota(request, slug, nota_id):
    try:
        db = get_db_from_slug(slug)
        service = EmissaoService(slug, db)
        resposta = service.emitir(nota_id)
        
        # Enriquece a resposta com mensagem amigável
        status = resposta.get("status")
        motivo_original = resposta.get("motivo")
        mensagem_amigavel = get_sefaz_message(status, motivo_original)
        
        # Se status for None ou 0, talvez não seja erro da SEFAZ, mas interno
        if status:
            resposta["mensagem"] = mensagem_amigavel
            # Se não for autorizado (100) nem processamento (103, 105), pode ser erro
            # Status de sucesso/processamento: 100, 101, 102, 103, 105
            if str(status) not in ('100', '101', '102', '103', '105'):
                resposta["erro"] = mensagem_amigavel
                return JsonResponse(resposta, status=400)

        return JsonResponse(resposta)
    except Exception as e:
        logger.exception("Falha ao emitir nota (slug=%s nota_id=%s)", slug, nota_id)
        drf_response = tratar_erro(e)
        if isinstance(drf_response, DRFResponse):
            data = drf_response.data
            status_code = drf_response.status_code
            if isinstance(data, dict):
                msg = (
                    data.get("mensagem")
                    or data.get("detalhes")
                    or data.get("erro")
                    or str(e)
                )
                data["mensagem"] = msg
        else:
            data = {"erro": "erro_interno", "mensagem": str(e)}
            status_code = 500
        return JsonResponse(data, status=status_code)


def imprimir_danfe(request, slug, nota_id):
    try:
        db = get_db_from_slug(slug)
        nota = Nota.objects.using(db).get(id=nota_id)

        xml_content = nota.xml_autorizado or nota.xml_assinado
        
        if not xml_content:
             return JsonResponse({"erro": "Nota não possui XML gerado para impressão."}, status=400)

        if isinstance(xml_content, (bytes, bytearray)):
            xml_content = xml_content.decode("utf-8", errors="ignore")

        if str(getattr(nota, "modelo", "") or "").strip() == "65":
            html = _nfce_40col_html(xml_content)
            return HttpResponse(html, content_type="text/html; charset=utf-8")

        if Danfe is None:
            return JsonResponse({"erro": "Biblioteca de impressão não instalada (BrazilFiscalReport)"}, status=500)

        danfe = Danfe(xml_content)
        pdf_str = danfe.output(dest="S")
        if isinstance(pdf_str, (bytes, bytearray)):
            pdf_bytes = bytes(pdf_str)
        else:
            pdf_bytes = pdf_str.encode("latin-1")
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="NFe_{nota.numero}.pdf"'
        return response

    except Exception as e:
        # Tratamento de erro simplificado para o endpoint de impressão
        return JsonResponse({"erro": "Falha ao gerar PDF", "detalhes": str(e)}, status=500)
