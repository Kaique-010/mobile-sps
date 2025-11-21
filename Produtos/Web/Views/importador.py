import requests
import csv
import math
from datetime import datetime
from decimal import Decimal
from Produtos.models import Ncm
from ...models import NcmAliquota
from core.utils import get_licenca_db_config

def _get_decimal(row, *keys):
    for k in keys:
        v = row.get(k)
        if v is not None:
            s = str(v).strip().replace(',', '.')
            try:
                return Decimal(s)
            except Exception:
                continue
    return Decimal('0')

def importar_ibpt_automatico(request=None, empresa_id=None, timeout=15, csv_url=None, csv_text=None, csv_path=None):
    banco = get_licenca_db_config(request) if request is not None else 'default'
    if empresa_id is None and request is not None:
        try:
            empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        except Exception:
            empresa_id = None
    try:
        empresa_id = int(empresa_id) if empresa_id is not None else 1
    except Exception:
        empresa_id = 1

    agora = datetime.now()
    ano = agora.year
    trimestre = math.ceil(agora.month / 3)

    text = None
    if csv_text:
        text = csv_text
    elif csv_path:
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            with open(csv_path, 'r', encoding='latin-1', errors='ignore') as f:
                text = f.read()
    else:
        url = csv_url or f"https://ibpt.com.br/tabela/arquivos/TABELA_IBPT_{ano}_TRIMESTRE_{trimestre:02d}.csv"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        try:
            text = resp.text
        except Exception:
            text = resp.content.decode('latin-1', errors='ignore')

    linhas = text.splitlines()
    reader = csv.DictReader(linhas, delimiter=';')

    total = 0

    for row in reader:
        ncm_code = (row.get("NCM") or row.get("ncm") or '').replace('.', '').strip()
        if not ncm_code:
            continue
        ncm_obj = Ncm.objects.using(banco).filter(ncm_codi=ncm_code).first()
        if not ncm_obj:
            continue

        aliq_ipi = _get_decimal(row, "Nacional IPI", "IPI", "Aliq IPI")
        aliq_pis = _get_decimal(row, "PIS", "Aliq PIS")
        aliq_cofins = _get_decimal(row, "COFINS", "Aliq COFINS")
        aliq_cbs = _get_decimal(row, "CBS")
        aliq_ibs = _get_decimal(row, "IBS")

        defaults = {
            'nali_empr': empresa_id,
            'nali_aliq_ipi': aliq_ipi or Decimal('0'),
            'nali_aliq_pis': aliq_pis or Decimal('0'),
            'nali_aliq_cofins': aliq_cofins or Decimal('0'),
            'nali_aliq_cbs': aliq_cbs or Decimal('0'),
            'nali_aliq_ibs': aliq_ibs or Decimal('0'),
        }
        aliq, created = NcmAliquota.objects.using(banco).get_or_create(
            nali_ncm=ncm_obj,
            defaults=defaults
        )
        if not created:
            for k, v in defaults.items():
                setattr(aliq, k, v)
            aliq.save(using=banco)
        total += 1

    return total
