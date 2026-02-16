from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Titulosreceber
from decimal import Decimal
from calendar import monthrange
from datetime import date


def _validar_campos_obrigatorios(dados):
    obrigatorios = ['titu_empr','titu_fili','titu_clie','titu_titu','titu_seri','titu_parc','titu_emis','titu_venc','titu_valo']
    erros = {}
    for campo in obrigatorios:
        if dados.get(campo) in [None, '', []]:
            erros[campo] = ['Campo obrigatório.']
    if erros:
        raise ValidationError(erros)

def criar_titulo_receber(*, banco: str, dados: dict, empresa_id: int, filial_id: int) -> Titulosreceber:
    if not dados.get('titu_empr'):
        dados['titu_empr'] = empresa_id
    if not dados.get('titu_fili'):
        dados['titu_fili'] = filial_id
    _validar_campos_obrigatorios(dados)
    with transaction.atomic(using=banco):
        existe = Titulosreceber.objects.using(banco).filter(
            titu_empr=dados['titu_empr'] or empresa_id,
            titu_fili=dados['titu_fili'] or filial_id,
            titu_clie=dados['titu_clie'],
            titu_titu=dados['titu_titu'],
            titu_seri=dados['titu_seri'],
            titu_parc=dados['titu_parc'],
            titu_emis=dados['titu_emis'],
            titu_venc=dados['titu_venc'],
        ).exists()
        if existe:
            raise ValidationError({'detail': ['Título já existe.']})
        dados.setdefault('titu_aber', 'A')
        obj = Titulosreceber.objects.using(banco).create(**dados)
        return obj

def atualizar_titulo_receber(titulo: Titulosreceber, *, banco: str, dados: dict) -> Titulosreceber:
    _validar_campos_obrigatorios({**{
        'titu_empr': getattr(titulo, 'titu_empr', None),
        'titu_fili': getattr(titulo, 'titu_fili', None),
        'titu_clie': titulo.titu_clie,
        'titu_titu': titulo.titu_titu,
        'titu_seri': titulo.titu_seri,
        'titu_parc': titulo.titu_parc,
        'titu_emis': titulo.titu_emis,
        'titu_venc': titulo.titu_venc,
        'titu_valo': titulo.titu_valo,
    }, **dados})
    with transaction.atomic(using=banco):
        # PATCH: atualizar somente campos não-chave, usando filtro pela chave composta
        chaves = {'titu_empr','titu_fili','titu_clie','titu_titu','titu_seri','titu_parc'}
        updates = {k: v for k, v in dados.items() if k not in chaves}
        if updates:
            (Titulosreceber.objects
                .using(banco)
                .filter(
                    titu_empr=getattr(titulo, 'titu_empr'),
                    titu_fili=getattr(titulo, 'titu_fili'),
                    titu_clie=titulo.titu_clie,
                    titu_titu=titulo.titu_titu,
                    titu_seri=titulo.titu_seri,
                    titu_parc=titulo.titu_parc,
                )
                .update(**updates)
            )
        # Recarrega objeto atualizado
        return (Titulosreceber.objects
                .using(banco)
                .filter(
                    titu_empr=getattr(titulo, 'titu_empr'),
                    titu_fili=getattr(titulo, 'titu_fili'),
                    titu_clie=titulo.titu_clie,
                    titu_titu=titulo.titu_titu,
                    titu_seri=titulo.titu_seri,
                    titu_parc=titulo.titu_parc,
                )
                .first())

def excluir_titulo_receber(titulo: Titulosreceber, *, banco: str) -> None:
    with transaction.atomic(using=banco):
        titulo.delete(using=banco)


def gera_parcelas_a_receber(titulo: Titulosreceber, *, banco: str) -> None:
    def _add_months(d: date, m: int) -> date:
        y = d.year + (d.month - 1 + m) // 12
        mo = (d.month - 1 + m) % 12 + 1
        last = monthrange(y, mo)[1]
        day = d.day if d.day <= last else last
        return date(y, mo, day)
    with transaction.atomic(using=banco):
        n = int(str(titulo.titu_parc))
        total = Decimal(str(titulo.titu_valo or 0))
        base = (total / Decimal(n)).quantize(Decimal('0.01'))
        dif = total - (base * n)
        venc_base = titulo.titu_venc
        valor_1 = base if n > 1 else base + dif
        titulo.titu_parc = '1'
        titulo.titu_venc = venc_base
        titulo.titu_valo = valor_1
        titulo.save(using=banco)
        for i in range(2, n + 1):
            v = base if i < n else base + dif
            Titulosreceber.objects.using(banco).create(
                titu_empr=titulo.titu_empr,
                titu_fili=titulo.titu_fili,
                titu_clie=titulo.titu_clie,
                titu_titu=titulo.titu_titu,
                titu_seri=titulo.titu_seri,
                titu_parc=str(i),
                titu_emis=titulo.titu_emis,
                titu_venc=_add_months(venc_base, i - 1),
                titu_valo=v,
                titu_aber=titulo.titu_aber or 'A',
                titu_form_reci=titulo.titu_form_reci,
                titu_tipo=titulo.titu_tipo,
            )
