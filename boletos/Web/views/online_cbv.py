from datetime import date, datetime
import logging

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from core.registry import get_licenca_db_config
from Entidades.models import Entidades
from contas_a_receber.models import Titulosreceber

from ...models import Carteira
from ...services.boleto_online_factory import get_online_boleto_service


logger = logging.getLogger(__name__)

SAFE_MIN_DATE = date(2010, 1, 1)
SAFE_MAX_DATE = date(2100, 12, 31)


def _extract(data, *paths):
    for path in paths:
        cur = data
        ok = True
        for key in path.split('.'):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ''):
            return cur
    return None


def _normalize_bank_code(raw_value):
    raw = str(raw_value or '').strip()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None, None
    code_str = digits[:3].zfill(3)
    try:
        code_int = int(code_str)
    except ValueError:
        return None, None
    return code_str, code_int


def _mask(value):
    v = str(value or '').strip()
    if not v:
        return ''
    if len(v) <= 6:
        return f'{v[:2]}***{v[-1:]}'
    return f'{v[:4]}***{v[-2:]}'


class BoletoOnlineView(View):
    template_name = 'Boletos/online_registros.html'

    def _ctx(self, request):
        db = get_licenca_db_config(request) or 'default'
        empresa = request.session.get('empresa_id')
        filial = request.session.get('filial_id')

        entidade_id = request.GET.get('entidade_banco')
        carteira_id = request.GET.get('carteira')
        cliente_id = request.GET.get('cliente')
        data_ini_raw = request.GET.get('data_ini')
        data_fim_raw = request.GET.get('data_fim')
        def _parse_date(v):
            s = str(v or '').strip()
            if not s:
                return None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                try:
                    d = datetime.strptime(s, fmt).date()
                    if d.year < 1900 or d.year > 2100:
                        return None
                    return d
                except Exception:
                    continue
            return None
        data_ini = _parse_date(data_ini_raw)
        data_fim = _parse_date(data_fim_raw)
        if data_ini and data_fim and data_ini > data_fim:
            data_ini, data_fim = data_fim, data_ini
        if data_ini and data_ini < SAFE_MIN_DATE:
            data_ini = SAFE_MIN_DATE
        if data_fim and data_fim > SAFE_MAX_DATE:
            data_fim = SAFE_MAX_DATE

        entidades_banco_qs = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tien='B').order_by('enti_nome')

        entidade_banco = None
        bank_code_str = None
        bank_code_int = None
        try:
            entidade_id_int = int(entidade_id) if entidade_id else None
        except (TypeError, ValueError):
            entidade_id_int = None
        if entidade_id:
            entidade_banco = entidades_banco_qs.filter(enti_clie=entidade_id).first()
            bank_code_str, bank_code_int = _normalize_bank_code(getattr(entidade_banco, 'enti_banc', None))

        carteiras_qs = Carteira.objects.using(db).filter(cart_empr=empresa)
        if filial:
            carteiras_qs = carteiras_qs.filter(cart_fili=filial)
        if entidade_id_int is not None:
            carteiras_qs = carteiras_qs.filter(cart_banc=entidade_id_int)
        if carteira_id:
            carteiras_qs = carteiras_qs.filter(cart_codi=carteira_id)

        clientes_qs = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tipo_enti__in=['CL', 'AM']).order_by('enti_nome')

        titulos = Titulosreceber.objects.using(db).filter(titu_empr=empresa, titu_aber='A', titu_form_reci='53')
        if filial:
            titulos = titulos.filter(titu_fili=filial)
        if entidade_id_int is not None:
            banc_q = Q(titu_cobr_banc__isnull=True) | Q(titu_cobr_banc=entidade_id_int)
            if bank_code_int is not None:
                banc_q = banc_q | Q(titu_cobr_banc=bank_code_int)
            titulos = titulos.filter(banc_q)
        if carteira_id:
            try:
                carteira_id_int = int(carteira_id)
            except (TypeError, ValueError):
                carteira_id_int = None
            if carteira_id_int is not None:
                titulos = titulos.filter(Q(titu_cobr_cart__isnull=True) | Q(titu_cobr_cart=carteira_id_int))
        if cliente_id:
            titulos = titulos.filter(titu_clie=cliente_id)
        # Exclusão preventiva de datas inválidas (ex.: anos BC que quebram o driver)
        titulos = titulos.filter(Q(titu_venc__isnull=True) | Q(titu_venc__gte=SAFE_MIN_DATE))
        if data_ini and data_fim:
            titulos = titulos.filter(titu_venc__range=(data_ini, data_fim))
        elif data_ini:
            titulos = titulos.filter(titu_venc__gte=data_ini)
        elif data_fim:
            titulos = titulos.filter(titu_venc__lte=data_fim)
        titulos = titulos.only(
            'titu_titu',
            'titu_parc',
            'titu_seri',
            'titu_clie',
            'titu_venc',
            'titu_valo',
            'titu_cobr_banc',
            'titu_cobr_cart',
            'titu_noss_nume',
            'titu_linh_digi',
            'titu_url_bole',
            'titu_aber',
            'titu_form_reci',
            'titu_empr',
            'titu_fili',
        )

        pendentes = titulos.filter(titu_noss_nume__isnull=True)[:200]
        enviados = titulos.exclude(titu_noss_nume__isnull=True)[:200]

        return {
            'slug': self.kwargs.get('slug'),
            'entidades_banco': entidades_banco_qs[:200],
            'entidade_banco': entidade_banco,
            'bank_code': bank_code_str or '',
            'carteiras': carteiras_qs.order_by('cart_codi')[:200],
            'clientes': clientes_qs[:200],
            'pendentes': pendentes,
            'enviados': enviados,
            'filtro': {'entidade_banco': entidade_id or '', 'carteira': carteira_id or '', 'cliente': cliente_id or '', 'data_ini': data_ini_raw or '', 'data_fim': data_fim_raw or ''},
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._ctx(request))

    def post(self, request, *args, **kwargs):
        db = get_licenca_db_config(request) or 'default'
        empresa = request.session.get('empresa_id')
        filial = request.session.get('filial_id')

        action = request.POST.get('action')
        carteira_id = request.POST.get('carteira')
        entidade_id = request.POST.get('entidade_banco')
        selected = request.POST.getlist('titulos[]')
        cliente_filter = request.POST.get('cliente')
        def _parse_date(v):
            s = str(v or '').strip()
            if not s:
                return None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                try:
                    d = datetime.strptime(s, fmt).date()
                    if d.year < 1900 or d.year > 2100:
                        return None
                    return d
                except Exception:
                    continue
            return None

        if not entidade_id:
            return JsonResponse({'ok': False, 'erro': 'entidade_banco_obrigatoria'}, status=400)
        if not carteira_id:
            return JsonResponse({'ok': False, 'erro': 'carteira_obrigatoria'}, status=400)

        entidade_banco = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tien='B', enti_clie=entidade_id).first()
        if not entidade_banco:
            return JsonResponse({'ok': False, 'erro': 'entidade_banco_nao_encontrada'}, status=404)

        bank_code_str, bank_code_int = _normalize_bank_code(getattr(entidade_banco, 'enti_banc', None))
        if bank_code_int is None or not bank_code_str:
            return JsonResponse({'ok': False, 'erro': 'codigo_banco_invalido_na_entidade'}, status=400)

        try:
            entidade_id_int = int(entidade_id)
        except (TypeError, ValueError):
            entidade_id_int = None
        if entidade_id_int is None:
            return JsonResponse({'ok': False, 'erro': 'entidade_banco_invalida'}, status=400)
        try:
            carteira_id_int = int(carteira_id)
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'carteira_invalida'}, status=400)

        carteira_qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=entidade_id_int, cart_codi=carteira_id_int)
        if filial:
            carteira_qs = carteira_qs.filter(cart_fili=filial)
        carteira = carteira_qs.first()
        if not carteira:
            return JsonResponse({'ok': False, 'erro': 'carteira_nao_encontrada_para_entidade'}, status=404)

        logger.info(
            "[boletos_online] ctx db=%s empresa=%s filial=%s entidade_id=%s banco_inst=%s carteira=(banco_entidade=%s,codi=%s,fili=%s) carteira_cfg=(ssl_lib=%s,client_id=%s,has_secret=%s,has_x_api_key=%s,scope=%s)",
            db,
            empresa,
            filial,
            entidade_id_int,
            bank_code_str,
            getattr(carteira, "cart_banc", None),
            getattr(carteira, "cart_codi", None),
            getattr(carteira, "cart_fili", None),
            str(getattr(carteira, "cart_webs_ssl_lib", "") or ""),
            _mask(getattr(carteira, "cart_webs_clie_id", "") or ""),
            bool(str(getattr(carteira, "cart_webs_clie_secr", "") or "").strip()),
            bool(str(getattr(carteira, "cart_webs_user_key", "") or "").strip()),
            str(getattr(carteira, "cart_webs_scop", "") or ""),
        )

        service, service_error = get_online_boleto_service(bank_code_str, carteira)

        results = []
        success_count = 0
        error_count = 0
        for item in selected:
            try:
                titu, seri, parc, clie = item.split('|')
            except ValueError:
                error_count += 1
                results.append({'titulo': item, 'ok': False, 'erro': 'selecao_invalida'})
                continue
            titulo = Titulosreceber.objects.using(db).filter(
                titu_empr=empresa, titu_titu=titu, titu_seri=seri, titu_parc=parc, titu_clie=clie
            ).first()
            if not titulo:
                error_count += 1
                results.append({'titulo': f'{titu}/{parc}', 'ok': False, 'erro': 'titulo_nao_encontrado'})
                continue


            if str(getattr(titulo, 'titu_form_reci', '') or '') != '53':
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_nao_e_boleto_forma_53'})
                continue

            if cliente_filter and str(titulo.titu_clie) != str(cliente_filter):
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_fora_do_cliente_filtrado'})
                continue

            if titulo.titu_cobr_banc is None:
                titulo.titu_cobr_banc = entidade_id_int
            elif entidade_id_int is not None and int(titulo.titu_cobr_banc) not in (entidade_id_int, bank_code_int):
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_com_banco_diferente_do_selecionado'})
                continue
            elif entidade_id_int is None and int(titulo.titu_cobr_banc) != bank_code_int:
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_com_banco_diferente_do_selecionado'})
                continue

            if titulo.titu_cobr_cart is None:
                titulo.titu_cobr_cart = carteira_id_int
            elif int(titulo.titu_cobr_cart) != carteira_id_int:
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_com_carteira_diferente_da_selecionada'})
                continue

            try:
                if action == 'registrar':
                    payload = {
                        'seuNumero': f'{titulo.titu_titu}/{titulo.titu_parc}',
                        'valor': float(titulo.titu_valo or 0),
                        'dataVencimento': titulo.titu_venc.isoformat() if titulo.titu_venc else date.today().isoformat(),
                        'pagador': {'codigo': str(titulo.titu_clie)},
                    }
                    retorno = service.registrar_boleto(payload)
                    titulo.titu_noss_nume = _extract(retorno, 'nossoNumero', 'codigoBarras.nossoNumero', 'beneficiario.tituloNossoNumero')
                    titulo.titu_linh_digi = _extract(retorno, 'linhaDigitavel', 'codigoBarras.linhaDigitavel')
                    titulo.titu_url_bole = _extract(retorno, 'linkBoleto', 'urlBoleto', 'pix.qrCode', 'pix.copiaECola')
                    titulo.save(using=db)
                elif action == 'consultar':
                    retorno = service.consultar_boleto(titulo.titu_noss_nume)
                elif action == 'baixar':
                    retorno = service.baixar_boleto(titulo.titu_noss_nume, payload={})
                elif action == 'cancelar':
                    retorno = service.alterar_boleto(titulo.titu_noss_nume, payload={'situacao': 'BAIXADO'})
                elif action == 'alterar':
                    nova = _parse_date(request.POST.get('nova_data_vencimento'))
                    if not nova:
                        error_count += 1
                        results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'data_invalida'})
                        continue
                    retorno = service.alterar_boleto(titulo.titu_noss_nume, payload={'dataVencimento': nova.isoformat()})
                else:
                    retorno = {'ok': True}

                success_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': True, 'retorno': retorno})
            except service_error as exc:
                error_count += 1
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': str(exc)})

        return JsonResponse({
            'ok': success_count > 0,
            'success': success_count,
            'errors': error_count,
            'results': results,
        })
