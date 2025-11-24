from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Titulospagar

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
        for k, v in dados.items():
            setattr(titulo, k, v)
        titulo.save(using=banco)
        return titulo

def excluir_titulo_pagar(titulo: Titulospagar, *, banco: str) -> None:
    with transaction.atomic(using=banco):
        titulo.delete(using=banco)