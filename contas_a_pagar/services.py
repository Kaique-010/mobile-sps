from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Titulospagar
from decimal import Decimal
from calendar import monthrange
from datetime import date

def _validar_campos_obrigatorios(dados):
    obrigatorios = ['titu_empr','titu_fili','titu_forn','titu_titu','titu_seri','titu_parc','titu_emis','titu_venc','titu_valo']
    erros = {}
    for campo in obrigatorios:
        if dados.get(campo) in [None, '', []]:
            erros[campo] = ['Campo obrigatório.']
    if erros:
        raise ValidationError(erros)

def criar_titulo_pagar(*, banco: str, dados: dict) -> Titulospagar:
    _validar_campos_obrigatorios(dados)
    with transaction.atomic(using=banco):
        existe = Titulospagar.objects.using(banco).filter(
            titu_empr=dados['titu_empr'],
            titu_fili=dados['titu_fili'],
            titu_forn=dados['titu_forn'],
            titu_titu=dados['titu_titu'],
            titu_seri=dados['titu_seri'],
            titu_parc=dados['titu_parc'],
            titu_emis=dados['titu_emis'],
            titu_venc=dados['titu_venc'],
        ).exists()
        if existe:
            raise ValidationError({'detail': ['Título já existe.']})
        dados.setdefault('titu_aber', 'A')
        obj = Titulospagar.objects.using(banco).create(**dados)
        return obj

def atualizar_titulo_pagar(titulo: Titulospagar, *, banco: str, dados: dict) -> Titulospagar:
    _validar_campos_obrigatorios({**{
        'titu_empr': getattr(titulo, 'titu_empr', None),
        'titu_fili': getattr(titulo, 'titu_fili', None),
        'titu_forn': titulo.titu_forn,
        'titu_titu': titulo.titu_titu,
        'titu_seri': titulo.titu_seri,
        'titu_parc': titulo.titu_parc,
        'titu_emis': titulo.titu_emis,
        'titu_venc': titulo.titu_venc,
        'titu_valo': titulo.titu_valo,
    }, **dados})
    with transaction.atomic(using=banco):
        imutaveis = {'titu_empr','titu_fili','titu_forn','titu_titu','titu_seri','titu_parc'}
        atualizaveis = {k: v for k, v in dados.items() if k not in imutaveis}
        if not atualizaveis:
            return titulo
        # Atualiza diretamente via QuerySet usando a chave composta real do banco
        Titulospagar.objects.using(banco).filter(
            titu_empr=titulo.titu_empr,
            titu_fili=titulo.titu_fili,
            titu_forn=titulo.titu_forn,
            titu_titu=titulo.titu_titu,
            titu_seri=titulo.titu_seri,
            titu_parc=titulo.titu_parc,
        ).update(**atualizaveis)
        # Refresca a instância para refletir as alterações
        for k, v in atualizaveis.items():
            setattr(titulo, k, v)
        return titulo

def excluir_titulo_pagar(titulo: Titulospagar, *, banco: str) -> None:
    with transaction.atomic(using=banco):
        titulo.delete(using=banco)

def gera_parcelas_a_pagar(titulo: Titulospagar, *, banco: str) -> None:
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
            Titulospagar.objects.using(banco).create(
                titu_empr=titulo.titu_empr,
                titu_fili=titulo.titu_fili,
                titu_forn=titulo.titu_forn,
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
