import datetime
from decimal import Decimal
from barcode import get_barcode_class
from barcode.writer import ImageWriter
from reportlab.lib.utils import ImageReader

def _pad(v, size):
    s = str(v or '')
    s = ''.join(ch for ch in s if ch.isdigit())
    return s.zfill(size)[:size]

def _fator_vencimento(data):
    base = datetime.date(1997, 10, 7)
    if not data:
        return '0000'
    if isinstance(data, datetime.datetime):
        data = data.date()
    dias = (data - base).days
    return str(dias % 10000).zfill(4)

def _mod11(num):
    pesos = [2,3,4,5,6,7,8,9]
    s = 0
    p = 0
    for ch in reversed(num):
        s += int(ch) * pesos[p]
        p = (p + 1) % len(pesos)
    r = s % 11
    if r == 0 or r == 1:
        return '0'
    if r == 10:
        return '1'
    return str(11 - r)

def _mod10(num):
    total = 0
    fator = 2
    for ch in reversed(str(num)):
        s = int(ch) * fator
        total += (s // 10) + (s % 10)
        fator = 1 if fator == 2 else 2
    dv = (10 - (total % 10)) % 10
    return str(dv)

def build_barcode_data(banco_cfg, titulo):
    banco = _pad(banco_cfg.get('codigo_banco'), 3)
    moeda = '9'
    fator = _fator_vencimento(getattr(titulo, 'titu_venc', None))
    valor = str(int(Decimal(str(getattr(titulo, 'titu_valo', 0))) * 100)).zfill(10)
    agencia = _pad(banco_cfg.get('agencia'), 4)
    conta = _pad(banco_cfg.get('conta'), 8)
    carteira = _pad(banco_cfg.get('carteira'), 2)
    nosso = _pad(getattr(titulo, 'titu_noss_nume', ''), 11)
    campo_livre = agencia + conta + nosso + carteira
    sem_dv = banco + moeda + fator + valor + campo_livre
    dv = _mod11(sem_dv)
    codigo_barras = banco + moeda + dv + fator + valor + campo_livre
    return codigo_barras

def linha_digitavel_from_barcode(codigo_barras):
    banco = codigo_barras[0:3]
    moeda = codigo_barras[3]
    dv_geral = codigo_barras[4]
    fator = codigo_barras[5:9]
    valor = codigo_barras[9:19]
    campo = codigo_barras[19:44]
    c1 = banco + moeda + campo[0:5]
    c2 = campo[5:15]
    c3 = campo[15:25]
    c1dv = _mod10(c1)
    c2dv = _mod10(c2)
    c3dv = _mod10(c3)
    return f"{c1}{c1dv} {c2}{c2dv} {c3}{c3dv} {dv_geral} {fator}{valor}"

def render_barcode_image(codigo_barras):
    ITF = get_barcode_class('itf')
    b = ITF(codigo_barras, writer=ImageWriter())
    img = b.render(writer_options={
        'module_width': 0.4,
        'module_height': 12.0,
        'font_size': 10,
        'text_distance': 1,
        'quiet_zone': 2.0,
    })
    return img

def validate_caixa_config(banco_cfg):
    errors = []
    cod = str(banco_cfg.get('codigo_banco') or '')
    if cod != '104':
        return {'ok': True, 'errors': []}
    ag = _pad(banco_cfg.get('agencia'), 4)
    ct = _pad(banco_cfg.get('conta'), 8)
    dv = str(banco_cfg.get('dv') or '')
    cart = str(banco_cfg.get('carteira') or '')
    if len(ag) < 4:
        errors.append('agencia_invalida')
    if len(ct) < 6:
        errors.append('conta_invalida')
    if not dv.isdigit():
        errors.append('dv_invalido')
    if not cart:
        errors.append('carteira_obrigatoria')
    return {'ok': len(errors)==0, 'errors': errors}

def validate_boleto(cedente, sacado, banco_cfg, titulo):
    missing = []
    if not cedente.get('nome'): missing.append('cedente.nome')
    if not cedente.get('documento'): missing.append('cedente.documento')
    if not sacado.get('nome'): missing.append('sacado.nome')
    if not banco_cfg.get('codigo_banco'): missing.append('banco.codigo')
    if not banco_cfg.get('agencia'): missing.append('banco.agencia')
    if not banco_cfg.get('conta'): missing.append('banco.conta')
    if not getattr(titulo, 'titu_titu', None): missing.append('titulo.numero')
    if not getattr(titulo, 'titu_venc', None): missing.append('titulo.vencimento')
    if not getattr(titulo, 'titu_valo', None): missing.append('titulo.valor')
    codigo = build_barcode_data(banco_cfg, titulo)
    ok_len = len(codigo) == 44
    dv_ok = codigo[4] == _mod11(codigo[:4] + codigo[5:])
    return {
        'missing': missing,
        'barcode': {
            'codigo': codigo,
            'len_ok': ok_len,
            'dv_ok': dv_ok,
        }
    }
