from datetime import date

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from core.registry import get_licenca_db_config
from Entidades.models import Entidades
from contas_a_receber.models import Titulosreceber

from ...models import Carteira
from ...services.boleto_online_factory import get_online_boleto_service


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


def _resolve_bank_code(entidade_banco):
    return str(getattr(entidade_banco, 'enti_banc', '') or '').strip()


class BoletoOnlineView(View):
    template_name = 'Boletos/online_registros.html'

    def _ctx(self, request):
        db = get_licenca_db_config(request) or 'default'
        empresa = request.session.get('empresa_id')
        filial = request.session.get('filial_id')

        entidade_id = request.GET.get('entidade_banco')
        carteira_id = request.GET.get('carteira')
        cliente_id = request.GET.get('cliente')

        entidades_banco_qs = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tien='B').order_by('enti_nome')

        entidade_banco = None
        bank_code = None
        if entidade_id:
            entidade_banco = entidades_banco_qs.filter(enti_clie=entidade_id).first()
            bank_code = _resolve_bank_code(entidade_banco)

        carteiras_qs = Carteira.objects.using(db).filter(cart_empr=empresa)
        if filial:
            carteiras_qs = carteiras_qs.filter(cart_fili=filial)
        if bank_code:
            carteiras_qs = carteiras_qs.filter(cart_banc=bank_code)
        if carteira_id:
            carteiras_qs = carteiras_qs.filter(cart_codi=carteira_id)

        clientes_qs = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tipo_enti__in=['CL', 'AM']).order_by('enti_nome')

        titulos = Titulosreceber.objects.using(db).filter(titu_empr=empresa, titu_aber='A', titu_form_reci='53')
        if filial:
            titulos = titulos.filter(titu_fili=filial)
        if bank_code and entidade_id:
            titulos = titulos.filter(Q(titu_cobr_banc=bank_code) | Q(titu_cobr_banc=entidade_id))
        if carteira_id:
            titulos = titulos.filter(titu_cobr_cart=carteira_id)
        if cliente_id:
            titulos = titulos.filter(titu_clie=cliente_id)

        pendentes = titulos.filter(titu_noss_nume__isnull=True)[:200]
        enviados = titulos.exclude(titu_noss_nume__isnull=True)[:200]

        return {
            'slug': self.kwargs.get('slug'),
            'entidades_banco': entidades_banco_qs[:200],
            'entidade_banco': entidade_banco,
            'bank_code': bank_code or '',
            'carteiras': carteiras_qs.order_by('cart_codi')[:200],
            'clientes': clientes_qs[:200],
            'pendentes': pendentes,
            'enviados': enviados,
            'filtro': {'entidade_banco': entidade_id or '', 'carteira': carteira_id or '', 'cliente': cliente_id or ''},
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

        if not entidade_id:
            return JsonResponse({'ok': False, 'erro': 'entidade_banco_obrigatoria'}, status=400)
        if not carteira_id:
            return JsonResponse({'ok': False, 'erro': 'carteira_obrigatoria'}, status=400)

        entidade_banco = Entidades.objects.using(db).filter(enti_empr=empresa, enti_tien='B', enti_clie=entidade_id).first()
        if not entidade_banco:
            return JsonResponse({'ok': False, 'erro': 'entidade_banco_nao_encontrada'}, status=404)

        bank_code = _resolve_bank_code(entidade_banco)
        if not bank_code:
            return JsonResponse({'ok': False, 'erro': 'codigo_banco_invalido_na_entidade'}, status=400)

        carteira_qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=bank_code, cart_codi=carteira_id)
        if filial:
            carteira_qs = carteira_qs.filter(cart_fili=filial)
        carteira = carteira_qs.first()
        if not carteira:
            return JsonResponse({'ok': False, 'erro': 'carteira_nao_encontrada_para_entidade'}, status=404)

        service, service_error = get_online_boleto_service(bank_code, carteira)

        results = []
        for item in selected:
            try:
                titu, seri, parc, clie = item.split('|')
            except ValueError:
                continue
            titulo = Titulosreceber.objects.using(db).filter(
                titu_empr=empresa, titu_titu=titu, titu_seri=seri, titu_parc=parc, titu_clie=clie
            ).first()
            if not titulo:
                continue


            if str(getattr(titulo, 'titu_form_reci', '') or '') != '53':
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_nao_e_boleto_forma_53'})
                continue

            if cliente_filter and str(titulo.titu_clie) != str(cliente_filter):
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_fora_do_cliente_filtrado'})
                continue

            if titulo.titu_cobr_banc in (None, ''):
                titulo.titu_cobr_banc = bank_code
            elif str(titulo.titu_cobr_banc) not in (str(bank_code), str(entidade_id)):
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': 'titulo_com_banco_diferente_do_selecionado'})
                continue

            if titulo.titu_cobr_cart in (None, ''):
                titulo.titu_cobr_cart = carteira_id
            elif str(titulo.titu_cobr_cart) != str(carteira_id):
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
                else:
                    retorno = service.alterar_boleto(titulo.titu_noss_nume, payload={
                        'dataVencimento': request.POST.get('nova_data_vencimento')
                    })

                results.append({'titulo': titulo.titu_titu, 'ok': True, 'retorno': retorno})
            except service_error as exc:
                results.append({'titulo': titulo.titu_titu, 'ok': False, 'erro': str(exc)})

        return JsonResponse({'ok': True, 'results': results})
