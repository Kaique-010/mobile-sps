from django.db import transaction, models
from django.core.exceptions import ValidationError
from .models import Bapatitulos, Titulospagar
from Lancamentos_Bancarios.models import Lctobancario
from Entidades.models import Entidades
from Lancamentos_Bancarios.utils import get_next_lcto_number
from adiantamentos.services import AdiantamentosService
from CentrodeCustos.models import Centrodecustos
from decimal import Decimal
from calendar import monthrange
from datetime import date
import logging
logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _validar_campos_obrigatorios(dados: dict) -> None:
    obrigatorios = [
        'titu_empr', 'titu_fili', 'titu_forn', 'titu_titu',
        'titu_seri', 'titu_parc', 'titu_emis', 'titu_venc', 'titu_valo',
    ]
    erros = {campo: ['Campo obrigatório.'] for campo in obrigatorios if dados.get(campo) in [None, '', []]}
    if erros:
        raise ValidationError(erros)


def _add_months(d: date, m: int) -> date:
    y  = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    day = min(d.day, monthrange(y, mo)[1])
    return date(y, mo, day)


def _resolver_banco_pagamento(titulo: Titulospagar, *, banco: str, dados: dict):
    """
    Retorna o banco/caixa a ser usado na baixa.
    Prioridade: dados['banco'] > titulo.bapa_banc > caixa padrão da empresa.
    """
    if dados.get('banco') is not None:
        banco_id = int(dados['banco'])
        existe = Entidades.objects.using(banco).filter(
            enti_empr=titulo.titu_empr,
            enti_clie=banco_id,
        ).exists()
        if not existe:
            raise ValueError("Banco/caixa informado não existe para esta empresa.")
        return banco_id

    ultima_baixa = (
        Bapatitulos.objects.using(banco)
        .filter(
            bapa_empr=titulo.titu_empr,
            bapa_fili=titulo.titu_fili,
            bapa_forn=titulo.titu_forn,
            bapa_titu=titulo.titu_titu,
            bapa_seri=titulo.titu_seri,
            bapa_parc=titulo.titu_parc,
        )
        .exclude(bapa_banc__isnull=True)
        .order_by('-bapa_sequ')
        .first()
    )
    if ultima_baixa and ultima_baixa.bapa_banc is not None:
        return int(ultima_baixa.bapa_banc)

    caixa = (
        Entidades.objects.using(banco)
        .filter(enti_empr=titulo.titu_empr, enti_tien='C')
        .order_by('enti_clie')
        .first()
    )
    logger.info(f"Caixa padrão encontrado: {caixa}")
    if not caixa or caixa.enti_clie is None:
        raise ValueError("Nenhum caixa padrão configurado para esta empresa.")
    return int(caixa.enti_clie)


def _resolver_centro_custo_pagamento(titulo: Titulospagar, *, banco: str, dados: dict) -> int | None:
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


def _calcular_valor_ja_pago(titulo: Titulospagar, *, banco: str) -> Decimal:
    """Retorna o total já pago em baixas anteriores (apenas para títulos parciais)."""
    if titulo.titu_aber != 'P':
        return Decimal('0')

    agg = Bapatitulos.objects.using(banco).filter(
        bapa_empr=titulo.titu_empr,
        bapa_fili=titulo.titu_fili,
        bapa_forn=titulo.titu_forn,
        bapa_titu=titulo.titu_titu,
        bapa_seri=titulo.titu_seri,
        bapa_parc=titulo.titu_parc,
    ).aggregate(
        total_valo_pago=models.Sum('bapa_valo_pago'),
        total_sub_tota=models.Sum('bapa_sub_tota'),
    )
    return Decimal(str(agg['total_valo_pago'] or agg['total_sub_tota'] or 0))


def _calcular_valor_total_baixas(titulo: Titulospagar, *, banco: str) -> Decimal:
    """Retorna o total pago em TODAS as baixas do título (usado após excluir uma baixa)."""
    agg = Bapatitulos.objects.using(banco).filter(
        bapa_empr=titulo.titu_empr,
        bapa_fili=titulo.titu_fili,
        bapa_forn=titulo.titu_forn,
        bapa_titu=titulo.titu_titu,
        bapa_seri=titulo.titu_seri,
        bapa_parc=titulo.titu_parc,
    ).aggregate(
        total_valo_pago=models.Sum('bapa_valo_pago'),
        total_sub_tota=models.Sum('bapa_sub_tota'),
    )
    return Decimal(str(agg['total_valo_pago'] or agg['total_sub_tota'] or 0))


def _next_bapa_sequ(banco: str) -> int:
    ultimo = Bapatitulos.objects.using(banco).order_by('-bapa_sequ').first()
    return (ultimo.bapa_sequ + 1) if ultimo else 1


def _atualizar_status_titulo(titulo: Titulospagar, novo_status: str, *, banco: str) -> None:
    Titulospagar.objects.using(banco).filter(
        titu_empr=titulo.titu_empr,
        titu_fili=titulo.titu_fili,
        titu_forn=titulo.titu_forn,
        titu_titu=titulo.titu_titu,
        titu_seri=titulo.titu_seri,
        titu_parc=titulo.titu_parc,
        titu_emis=titulo.titu_emis,
        titu_venc=titulo.titu_venc,
    ).update(titu_aber=novo_status)


def _gerar_lancamento_bancario(titulo: Titulospagar, baixa: Bapatitulos, *, banco: str) -> Lctobancario:
    """
    Cria um lançamento bancário de saída vinculado à baixa.
    Recebe o objeto baixa para garantir consistência com o que foi gravado.
    """
    if not baixa.bapa_banc:
        raise ValueError("Baixa sem banco definido — não é possível gerar lançamento bancário.")
    logger.info(f"Gerando lançamento bancário para baixa {baixa.bapa_sequ}")
    return Lctobancario.objects.using(banco).create(
        laba_ctrl=get_next_lcto_number(baixa.bapa_empr, baixa.bapa_fili, banco),
        laba_empr=baixa.bapa_empr,
        laba_fili=baixa.bapa_fili,
        laba_banc=int(baixa.bapa_banc),
        laba_data=baixa.bapa_dpag,
        laba_cecu=baixa.bapa_cecu,
        laba_valo=baixa.bapa_sub_tota or baixa.bapa_pago,
        laba_hist=baixa.bapa_hist,
        laba_dbcr='D',
        laba_enti=baixa.bapa_forn,
        laba_cheq=baixa.bapa_cheq,
    )
    


# ---------------------------------------------------------------------------
# CRUD de Títulos a Pagar
# ---------------------------------------------------------------------------

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
        return Titulospagar.objects.using(banco).create(**dados)


def atualizar_titulo_pagar(titulo: Titulospagar, *, banco: str, dados: dict) -> Titulospagar:
    _validar_campos_obrigatorios({
        'titu_empr': titulo.titu_empr,
        'titu_fili': titulo.titu_fili,
        'titu_forn': titulo.titu_forn,
        'titu_titu': titulo.titu_titu,
        'titu_seri': titulo.titu_seri,
        'titu_parc': titulo.titu_parc,
        'titu_emis': titulo.titu_emis,
        'titu_venc': titulo.titu_venc,
        'titu_valo': titulo.titu_valo,
        **dados,
    })
    with transaction.atomic(using=banco):
        imutaveis = {'titu_empr', 'titu_fili', 'titu_forn', 'titu_titu', 'titu_seri', 'titu_parc'}
        atualizaveis = {k: v for k, v in dados.items() if k not in imutaveis}
        if not atualizaveis:
            return titulo
        Titulospagar.objects.using(banco).filter(
            titu_empr=titulo.titu_empr,
            titu_fili=titulo.titu_fili,
            titu_forn=titulo.titu_forn,
            titu_titu=titulo.titu_titu,
            titu_seri=titulo.titu_seri,
            titu_parc=titulo.titu_parc,
        ).update(**atualizaveis)
        for k, v in atualizaveis.items():
            setattr(titulo, k, v)
        return titulo


def excluir_titulo_pagar(titulo: Titulospagar, *, banco: str) -> None:
    with transaction.atomic(using=banco):
        titulo.delete(using=banco)


def gera_parcelas_a_pagar(titulo: Titulospagar, *, banco: str) -> None:
    with transaction.atomic(using=banco):
        n      = int(str(titulo.titu_parc))
        total  = Decimal(str(titulo.titu_valo or 0))
        base   = (total / Decimal(n)).quantize(Decimal('0.01'))
        dif    = total - (base * n)
        venc_base = titulo.titu_venc

        titulo.titu_parc = '1'
        titulo.titu_venc = venc_base
        titulo.titu_valo = base if n > 1 else base + dif
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


# ---------------------------------------------------------------------------
# Baixa de Título
# ---------------------------------------------------------------------------

def baixar_titulo_pagar(
    titulo: Titulospagar,
    *,
    banco: str,
    dados: dict,
) -> tuple[Bapatitulos, Lctobancario | None]:
    """
    Executa a baixa completa de um título a pagar.

    Responsabilidades (todas aqui, zero na view):
      1. Validar estado do título
      2. Calcular valores: juros, multa, desconto, líquido e acumulado
      3. Determinar tipo da baixa: T (total) ou P (parcial)
      4. Consumir adiantamento se forma_pagamento == 'A'
      5. Criar registro Bapatitulos
      6. Atualizar titu_aber no Titulospagar
      7. Gerar lançamento bancário se forma_pagamento == 'B' e banco informado

    Retorna: (baixa, lancamento | None)
    Levanta: ValueError para regras de negócio violadas.
    """
    with transaction.atomic(using=banco):

        # 1. Guarda de estado
        if titulo.titu_aber == 'T':
            raise ValueError("Título já está totalmente baixado.")

        # 2. Cálculo de valores
        valor_titulo   = Decimal(str(titulo.titu_valo or 0))
        valor_pago     = Decimal(str(dados['valor_pago']))
        valor_juros    = Decimal(str(dados.get('valor_juros') or 0))
        valor_multa    = Decimal(str(dados.get('valor_multa') or 0))
        valor_desconto = Decimal(str(dados.get('valor_desconto') or 0))
        valor_liquido  = valor_pago + valor_juros + valor_multa - valor_desconto

        # 3. Acumulado (inclui baixas parciais anteriores)
        valor_ja_pago     = _calcular_valor_ja_pago(titulo, banco=banco)
        valor_acumulado   = valor_ja_pago + valor_liquido
        tipo_baixa        = 'T' if valor_acumulado >= valor_titulo else 'P'

        # 4. Adiantamento
        adiantamento_usado = None
        if dados.get('forma_pagamento') == 'A':
            adiantamento_usado = AdiantamentosService.usar_adiantamento_by_context(
                empresa=titulo.titu_empr,
                filial=titulo.titu_fili,
                entidade=titulo.titu_forn,
                tipo='P',
                valor=valor_pago,
                using=banco,
                referencia={
                    'modulo': 'contas_a_pagar',
                    'titu': titulo.titu_titu,
                    'seri': titulo.titu_seri,
                    'parc': titulo.titu_parc,
                },
            )

        # 5. Criar baixa
        banco_resolvido = _resolver_banco_pagamento(titulo, banco=banco, dados=dados)
        cecu_resolvido = _resolver_centro_custo_pagamento(titulo, banco=banco, dados=dados)

        baixa = Bapatitulos.objects.using(banco).create(
            bapa_sequ     =_next_bapa_sequ(banco),
            bapa_ctrl     =titulo.titu_ctrl or 0,
            bapa_empr     =titulo.titu_empr,
            bapa_fili     =titulo.titu_fili,
            bapa_forn     =titulo.titu_forn,
            bapa_titu     =titulo.titu_titu,
            bapa_seri     =titulo.titu_seri,
            bapa_parc     =titulo.titu_parc,
            bapa_dpag     =dados['data_pagamento'],
            bapa_apag     =valor_titulo,
            bapa_vmul     =valor_multa,
            bapa_vjur     =valor_juros,
            bapa_vdes     =valor_desconto,
            bapa_pago     =valor_liquido,
            bapa_valo_pago=valor_pago,
            bapa_sub_tota =valor_liquido,
            bapa_topa     =tipo_baixa,
            bapa_form     =dados.get('forma_pagamento', 'B'),
            bapa_banc     =banco_resolvido,
            bapa_cheq     =dados.get('cheque'),
            bapa_hist     =dados.get('historico') or f'Baixa do título {titulo.titu_titu}',
            bapa_emis     =titulo.titu_emis,
            bapa_venc     =titulo.titu_venc,
            bapa_cont     =titulo.titu_cont,
            bapa_cecu     =cecu_resolvido,
            bapa_even     =titulo.titu_even,
            bapa_port     =titulo.titu_port,
            bapa_situ     =titulo.titu_situ,
            bapa_id_adto  = int(adiantamento_usado.adia_docu) if adiantamento_usado else None,
        )

        # 6. Atualizar status do título
        _atualizar_status_titulo(titulo, tipo_baixa, banco=banco)

        # 7. Lançamento bancário (pagamento via banco/caixa)
        lancamento = None
        if baixa.bapa_form == 'B':
            lancamento = _gerar_lancamento_bancario(titulo, baixa, banco=banco)
            Bapatitulos.objects.using(banco).filter(
                bapa_sequ=baixa.bapa_sequ,
                bapa_empr=baixa.bapa_empr,
                bapa_fili=baixa.bapa_fili,
                bapa_forn=baixa.bapa_forn,
                bapa_titu=baixa.bapa_titu,
                bapa_seri=baixa.bapa_seri,
                bapa_parc=baixa.bapa_parc,
            ).update(
                bapa_ctrl_banc=lancamento.laba_ctrl,
                bapa_sequ_banc=lancamento.laba_ctrl,
            )

        return baixa, lancamento


# ---------------------------------------------------------------------------
# Exclusão de Baixa
# ---------------------------------------------------------------------------

def excluir_baixa_titulo(
    titulo: Titulospagar,
    baixa_id: int,
    *,
    banco: str,
) -> dict:
    """
    Exclui uma baixa específica de um título e recalcula seu status.

    Responsabilidades (todas aqui):
      1. Localizar a baixa garantindo que pertence ao título
      2. Estornar adiantamento se forma == 'A'
      3. Excluir o registro Bapatitulos
      4. Recalcular e atualizar titu_aber com base nas baixas restantes

    Retorna: dict com baixa_excluida e novo_status_titulo.
    Levanta: Bapatitulos.DoesNotExist se a baixa não for encontrada.
    """
    with transaction.atomic(using=banco):

        # 1. Localizar baixa vinculada ao título
        baixa = Bapatitulos.objects.using(banco).get(
            bapa_sequ=baixa_id,
            bapa_empr=titulo.titu_empr,
            bapa_fili=titulo.titu_fili,
            bapa_forn=titulo.titu_forn,
            bapa_titu=titulo.titu_titu,
            bapa_seri=titulo.titu_seri,
            bapa_parc=titulo.titu_parc,
        )

        # 2. Estornar adiantamento se necessário
        valor_baixa = baixa.bapa_valo_pago or baixa.bapa_sub_tota or Decimal('0')
        if baixa.bapa_form in ('A', 'P') and valor_baixa > 0:
            AdiantamentosService.estornar_adiantamento_by_context(
                empresa=titulo.titu_empr,
                filial=titulo.titu_fili,
                entidade=titulo.titu_forn,
                tipo='P',
                valor=valor_baixa,
                using=banco,
            )

        if baixa.bapa_ctrl_banc:
            filtros = {
                'laba_empr': baixa.bapa_empr,
                'laba_fili': baixa.bapa_fili,
                'laba_ctrl': int(baixa.bapa_ctrl_banc),
            }
            if baixa.bapa_banc is not None:
                filtros['laba_banc'] = int(baixa.bapa_banc)
            Lctobancario.objects.using(banco).filter(**filtros).delete()
            logger.info(f"Lançamento bancário {baixa.bapa_ctrl_banc} excluído para baixa {baixa.bapa_sequ}")

        # 3. Excluir baixa
        baixa.delete()

        # 4. Recalcular status do título
        total_restante = _calcular_valor_total_baixas(titulo, banco=banco)
        valor_titulo   = Decimal(str(titulo.titu_valo or 0))

        if total_restante <= 0:
            novo_status = 'A'           # Nenhuma baixa restante → Aberto
        elif total_restante >= valor_titulo:
            novo_status = 'T'           # Cobre o valor total → Total
        else:
            novo_status = 'P'           # Cobre parcialmente → Parcial

        _atualizar_status_titulo(titulo, novo_status, banco=banco)

        return {
            'baixa_excluida': baixa_id,
            'novo_status_titulo': novo_status,
        }
