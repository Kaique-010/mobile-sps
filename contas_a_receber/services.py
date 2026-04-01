from django.db import transaction, models
from django.core.exceptions import ValidationError
from .models import Titulosreceber, Baretitulos
from decimal import Decimal
from calendar import monthrange
from datetime import date
from Entidades.models import Entidades
from Lancamentos_Bancarios.models import Lctobancario
from Lancamentos_Bancarios.utils import get_next_lcto_number
from adiantamentos.services import AdiantamentosService
from CentrodeCustos.models import Centrodecustos


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


def _resolver_banco_recebimento(titulo: Titulosreceber, *, banco: str, dados: dict) -> int:
    if dados.get('banco') is not None:
        banco_id = int(dados['banco'])
        existe = Entidades.objects.using(banco).filter(
            enti_empr=titulo.titu_empr,
            enti_clie=banco_id,
        ).exists()
        if not existe:
            raise ValueError("Banco/caixa informado não existe para esta empresa.")
        return banco_id

    ultima = (
        Baretitulos.objects.using(banco)
        .filter(
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc,
        )
        .exclude(bare_banc__isnull=True)
        .order_by('-bare_sequ')
        .first()
    )
    if ultima and ultima.bare_banc is not None:
        return int(ultima.bare_banc)

    caixa = (
        Entidades.objects.using(banco)
        .filter(enti_empr=titulo.titu_empr, enti_tien='C')
        .order_by('enti_clie')
        .first()
    )
    if not caixa:
        raise ValueError("Nenhum caixa padrão configurado para esta empresa.")
    return int(caixa.enti_clie)


def _resolver_centro_custo_recebimento(titulo: Titulosreceber, *, banco: str, dados: dict) -> int | None:
    if dados.get('centro_custo') is not None:
        cecu_redu = int(dados['centro_custo'])
        existe = Centrodecustos.objects.using(banco).filter(
            cecu_empr=titulo.titu_empr,
            cecu_redu=cecu_redu,
        ).exists()
        if not existe:
            raise ValueError("Centro de custo informado não existe para esta empresa.")
        return cecu_redu
    return int(titulo.titu_cecu) if titulo.titu_cecu is not None else None


def _calcular_valor_ja_recebido(titulo: Titulosreceber, *, banco: str) -> Decimal:
    if titulo.titu_aber != 'P':
        return Decimal('0')

    agg = Baretitulos.objects.using(banco).filter(
        bare_empr=titulo.titu_empr,
        bare_fili=titulo.titu_fili,
        bare_clie=titulo.titu_clie,
        bare_titu=titulo.titu_titu,
        bare_seri=titulo.titu_seri,
        bare_parc=titulo.titu_parc,
    ).aggregate(
        total_valo_pago=models.Sum('bare_valo_pago'),
        total_sub_tota=models.Sum('bare_sub_tota'),
    )
    return Decimal(str(agg['total_valo_pago'] or agg['total_sub_tota'] or 0))


def _calcular_valor_total_baixas(titulo: Titulosreceber, *, banco: str) -> Decimal:
    agg = Baretitulos.objects.using(banco).filter(
        bare_empr=titulo.titu_empr,
        bare_fili=titulo.titu_fili,
        bare_clie=titulo.titu_clie,
        bare_titu=titulo.titu_titu,
        bare_seri=titulo.titu_seri,
        bare_parc=titulo.titu_parc,
    ).aggregate(
        total_valo_pago=models.Sum('bare_valo_pago'),
        total_sub_tota=models.Sum('bare_sub_tota'),
    )
    return Decimal(str(agg['total_valo_pago'] or agg['total_sub_tota'] or 0))


def _next_bare_sequ(banco: str) -> int:
    ultimo = Baretitulos.objects.using(banco).order_by('-bare_sequ').first()
    return (ultimo.bare_sequ + 1) if ultimo else 1


def _atualizar_status_titulo(titulo: Titulosreceber, novo_status: str, *, banco: str) -> None:
    Titulosreceber.objects.using(banco).filter(
        titu_empr=titulo.titu_empr,
        titu_fili=titulo.titu_fili,
        titu_clie=titulo.titu_clie,
        titu_titu=titulo.titu_titu,
        titu_seri=titulo.titu_seri,
        titu_parc=titulo.titu_parc,
        titu_emis=titulo.titu_emis,
        titu_venc=titulo.titu_venc,
    ).update(titu_aber=novo_status)


def _gerar_lancamento_bancario_recebimento(
    titulo: Titulosreceber,
    baixa: Baretitulos,
    *,
    banco: str,
) -> Lctobancario:
    if baixa.bare_banc is None:
        raise ValueError("Baixa sem banco definido — não é possível gerar lançamento bancário.")

    return Lctobancario.objects.using(banco).create(
        laba_ctrl=get_next_lcto_number(titulo.titu_empr, titulo.titu_fili, banco),
        laba_empr=titulo.titu_empr,
        laba_fili=titulo.titu_fili,
        laba_banc=int(baixa.bare_banc),
        laba_data=baixa.bare_dpag,
        laba_cecu=baixa.bare_cecu,
        laba_valo=baixa.bare_sub_tota or baixa.bare_pago,
        laba_hist=baixa.bare_hist,
        laba_dbcr='C',
        laba_enti=titulo.titu_clie,
        laba_cheq=baixa.bare_cheq,
    )


def baixar_titulo_receber(
    titulo: Titulosreceber,
    *,
    banco: str,
    dados: dict,
    usuario_id: int | None = None,
) -> tuple[Baretitulos, Lctobancario | None]:
    with transaction.atomic(using=banco):
        if titulo.titu_aber == 'T':
            raise ValueError("Título já está totalmente baixado.")

        valor_titulo = Decimal(str(titulo.titu_valo or 0))
        valor_recebido = Decimal(str(dados['valor_recebido']))
        valor_juros = Decimal(str(dados.get('valor_juros') or 0))
        valor_multa = Decimal(str(dados.get('valor_multa') or 0))
        valor_desconto = Decimal(str(dados.get('valor_desconto') or 0))
        valor_liquido = valor_recebido + valor_juros + valor_multa - valor_desconto

        valor_ja_recebido = _calcular_valor_ja_recebido(titulo, banco=banco)
        valor_acumulado = valor_ja_recebido + valor_liquido
        tipo_baixa = 'T' if valor_acumulado >= valor_titulo else 'P'

        adiantamento_usado = None
        if dados.get('forma_pagamento') == 'A':
            adiantamento_usado = AdiantamentosService.usar_adiantamento_by_context(
                empresa=titulo.titu_empr,
                filial=titulo.titu_fili,
                entidade=titulo.titu_clie,
                tipo='R',
                valor=valor_recebido,
                using=banco,
                referencia={
                    'modulo': 'contas_a_receber',
                    'titu': titulo.titu_titu,
                    'seri': titulo.titu_seri,
                    'parc': titulo.titu_parc,
                },
            )

        banco_resolvido = _resolver_banco_recebimento(titulo, banco=banco, dados=dados)
        cecu_resolvido = _resolver_centro_custo_recebimento(titulo, banco=banco, dados=dados)

        baixa = Baretitulos.objects.using(banco).create(
            bare_sequ=_next_bare_sequ(banco),
            bare_ctrl=titulo.titu_ctrl or 0,
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc,
            bare_dpag=dados['data_recebimento'],
            bare_apag=valor_titulo,
            bare_vmul=valor_multa,
            bare_vjur=valor_juros,
            bare_vdes=valor_desconto,
            bare_pago=valor_liquido,
            bare_valo_pago=valor_recebido,
            bare_sub_tota=valor_liquido,
            bare_topa=tipo_baixa,
            bare_form=dados.get('forma_pagamento', 'D'),
            bare_banc=banco_resolvido,
            bare_cheq=dados.get('cheque'),
            bare_hist=dados.get('historico') or f'Baixa do título {titulo.titu_titu}',
            bare_emis=titulo.titu_emis,
            bare_venc=titulo.titu_venc,
            bare_cont=titulo.titu_cont,
            bare_cecu=cecu_resolvido,
            bare_even=titulo.titu_even,
            bare_port=titulo.titu_port,
            bare_situ=titulo.titu_situ,
            bare_id_adto=int(adiantamento_usado.adia_docu) if adiantamento_usado else None,
            bare_usua_baix=usuario_id,
            bare_data_baix=dados['data_recebimento'],
        )

        _atualizar_status_titulo(titulo, tipo_baixa, banco=banco)

        lancamento = None
        if baixa.bare_form == 'B':
            lancamento = _gerar_lancamento_bancario_recebimento(titulo, baixa, banco=banco)
            Baretitulos.objects.using(banco).filter(
                bare_sequ=baixa.bare_sequ,
                bare_empr=baixa.bare_empr,
                bare_fili=baixa.bare_fili,
                bare_clie=baixa.bare_clie,
                bare_titu=baixa.bare_titu,
                bare_seri=baixa.bare_seri,
                bare_parc=baixa.bare_parc,
            ).update(
                bare_ctrl_banc=lancamento.laba_ctrl,
                bare_lote_banc=lancamento.laba_lote,
                bare_sequ_banc=lancamento.laba_ctrl,
            )

        return baixa, lancamento


def excluir_baixa_receber(
    titulo: Titulosreceber,
    baixa_id: int,
    *,
    banco: str,
) -> dict:
    with transaction.atomic(using=banco):
        baixa = Baretitulos.objects.using(banco).get(
            bare_sequ=baixa_id,
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc,
        )

        valor_baixa = baixa.bare_valo_pago or baixa.bare_sub_tota or Decimal('0')
        if baixa.bare_form in ('A', 'P') and valor_baixa > 0:
            AdiantamentosService.estornar_adiantamento_by_context(
                empresa=titulo.titu_empr,
                filial=titulo.titu_fili,
                entidade=titulo.titu_clie,
                tipo='R',
                valor=valor_baixa,
                using=banco,
            )

        if baixa.bare_ctrl_banc:
            filtros = {
                'laba_empr': baixa.bare_empr,
                'laba_fili': baixa.bare_fili,
                'laba_ctrl': int(baixa.bare_ctrl_banc),
            }
            if baixa.bare_banc is not None:
                filtros['laba_banc'] = int(baixa.bare_banc)
            Lctobancario.objects.using(banco).filter(**filtros).delete()
            logger.info(f"Lançamento bancário {baixa.bare_ctrl_banc} excluído para baixa {baixa.bare_sequ}")

        baixa.delete()

        total_restante = _calcular_valor_total_baixas(titulo, banco=banco)
        valor_titulo = Decimal(str(titulo.titu_valo or 0))

        if total_restante <= 0:
            novo_status = 'A'
        elif total_restante >= valor_titulo:
            novo_status = 'T'
        else:
            novo_status = 'P'

        _atualizar_status_titulo(titulo, novo_status, banco=banco)

        return {
            'baixa_excluida': baixa_id,
            'novo_status_titulo': novo_status,
        }


def reabrir_titulo_receber_sem_baixa(
    titulo: Titulosreceber,
    *,
    banco: str,
) -> dict:
    with transaction.atomic(using=banco):
        existe_baixa = Baretitulos.objects.using(banco).filter(
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc,
        ).exists()
        if existe_baixa:
            raise ValueError("Este título possui baixas registradas; use a reabertura via exclusão de baixa.")

        _atualizar_status_titulo(titulo, 'A', banco=banco)
        return {'novo_status_titulo': 'A'}
