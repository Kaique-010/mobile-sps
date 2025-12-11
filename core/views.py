from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
import json
from Entidades.models import Entidades
from Pedidos.models import PedidoVenda, Itenspedidovenda, PedidosGeral
from Pisos.models import Pedidospisos, Itenspedidospisos
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q
from django.db import connections
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from core.utils import get_licenca_db_config, get_db_from_slug
from core.middleware import get_licenca_slug
from OrdemdeServico.models import Ordemservico, Ordemservicopecas, Ordemservicoservicos     
import logging

logger = logging.getLogger(__name__)

def _get_slug(request):
    try:
        s = get_licenca_slug()
    except Exception:
        s = None
    if not s:
        try:
            s = request.session.get('slug')
        except Exception:
            s = None
    return (s or '').strip().lower()

def bad_request(request, exception=None):
    try:
        logger.error("[handler400] path=%s err=%s", getattr(request, 'path', None), str(exception))
    except Exception:
        pass
    try:
        accept = request.META.get('HTTP_ACCEPT', '')
    except Exception:
        accept = ''
    try:
        path = request.path or ''
    except Exception:
        path = ''
    if path.startswith('/api/') or 'application/json' in accept:
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'Bad Request',
            'code': 'SESSION_INVALID',
            'next': '/web/selecionar-empresa/'
        }, status=401)
    try:
        return redirect('web_login')
    except Exception:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/web/login/')

def identificar_tipo_cliente(request):
    s = _get_slug(request)
    if not s:
        return 'default'
    pisos_keys = ['indusparquet', 'indus', 'uliana', 'pgpisos', 'pisos', 'JULIANO DE SOUZA MONTEIRO E CIA LTDA']
    logger.info(f"[identificar_tipo_cliente] slug: {s}")
    os_keys = ['eletrocometa', 'eletro', 'cometa']
    if any(k in s for k in pisos_keys):
        return 'pisos'
    if any(k in s for k in os_keys):
        return 'os'
    return 'default'

@csrf_exempt
@require_http_methods(["POST"])
def warm_cache_endpoint(request):
    """Endpoint para aquecer cache manualmente"""
    try:
        from core.cache_warming import warm_modules_cache
        
        warmed_count = warm_modules_cache()
        
        return JsonResponse({
            'success': True,
            'message': f'Cache aquecido para {warmed_count} licenças',
            'warmed_licenses': warmed_count
        })
        
    except Exception as e:
        logger.error(f"Erro no warming manual: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'ok'})

def index(request):
    return render(request, 'index.html')
def home(request, slug=None, empresa=None, filial=None):
    try:
        if slug:
            request.session['slug'] = slug
    except Exception:
        pass
    try:
        if empresa is not None:
            request.session['empresa_id'] = int(empresa)
            request.session.modified = True
        if filial is not None:
            request.session['filial_id'] = int(filial)
            request.session.modified = True
    except Exception:
        pass
    if not slug:
        try:
            sess_slug = request.session.get('slug')
        except Exception:
            sess_slug = None
        if sess_slug:
            return redirect('home_slug', slug=sess_slug)
    try:
        banco = get_licenca_db_config(request) or 'default'
        logger.debug(f"[home] banco: {banco}")
    except Exception:
        banco = 'default'
    # Fallbacks: tentar slug atual do middleware, depois sessão
    try:
        slug_client = slug or get_licenca_slug()
    except Exception:
        slug_client = slug
    if banco == 'default':
        try:
            slug_cur = slug_client
        except Exception:
            slug_cur = None
        if slug_cur:
            try:
                banco = get_db_from_slug(slug_cur) or banco
                try:
                    request.session['slug'] = slug_cur
                except Exception:
                    pass
                logger.debug(f"[home] banco via middleware.slug: {banco}")
            except Exception:
                pass
    if banco == 'default':
        try:
            slug_sess = request.session.get('slug')
            if not slug_client and slug_sess:
                slug_client = slug_sess
            if slug_sess:
                banco = get_db_from_slug(slug_sess) or banco
                logger.debug(f"[home] banco via sessão.slug: {banco}")
        except Exception:
            pass

    empresa_id = request.session.get('empresa_id')
    try:
        empresa_id = int(empresa_id) if empresa_id is not None else None
    except Exception:
        empresa_id = None
    filial_id = request.session.get('filial_id')
    try:
        filial_id = int(filial_id) if filial_id is not None else None
    except Exception:
        filial_id = None
    try:
        logger.debug("[TRACE][HOME] slug=%s banco=%s empresa=%s filial=%s path=%s", request.session.get('slug'), banco, empresa_id, filial_id, request.path)
    except Exception:
        pass

    vendedor_selecionado = (request.GET.get('vendedor') or '').strip()
    vendedores_qs = Entidades.objects.using(banco).filter(enti_tipo_enti='VE')
    logger.debug(f"[home] vendedores_qs: {vendedores_qs}")
    if empresa_id is not None:
        vendedores_qs = vendedores_qs.filter(enti_empr=empresa_id)
    else:
        vendedores_qs = vendedores_qs.filter(enti_empr=-1)
    vendedores_qs = vendedores_qs.order_by('enti_nome')

    di = (request.GET.get('data_inicio') or '').strip()
    df = (request.GET.get('data_fim') or '').strip()
    try:
        ini = datetime.strptime(di, '%Y-%m-%d').date() if di else (datetime.today().date() - timedelta(days=30))
    except Exception:
        ini = datetime.today().date() - timedelta(days=30)
    try:
        fim = datetime.strptime(df, '%Y-%m-%d').date() if df else datetime.today().date()
    except Exception:
        fim = datetime.today().date()

    dashboard_tipo = identificar_tipo_cliente(request)
    template_name = 'home.html'
    total_valor = 0
    qtd_pedidos = 0
    ticket_medio = 0.0
    lucro_percent = 0.0
    itens_contagem = 0
    clientes_distintos = 0

    if dashboard_tipo == 'pisos':
        pedidos_qs = Pedidospisos.objects.using(banco).filter(pedi_data__gte=ini, pedi_data__lte=fim)
        if empresa_id is not None:
            pedidos_qs = pedidos_qs.filter(pedi_empr=empresa_id)
        if filial_id is not None:
            pedidos_qs = pedidos_qs.filter(pedi_fili=filial_id)
        if vendedor_selecionado:
            try:
                vend_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_tipo_enti='VE', enti_nome__iexact=vendedor_selecionado)
                    .values_list('enti_clie', flat=True)
                )
                if vend_ids:
                    pedidos_qs = pedidos_qs.filter(pedi_vend__in=[str(v) for v in vend_ids])
                else:
                    pedidos_qs = pedidos_qs.none()
            except Exception:
                pedidos_qs = pedidos_qs.none()
        total_valor = pedidos_qs.aggregate(v=Sum('pedi_tota')).get('v') or 0
        qtd_pedidos = pedidos_qs.count()
        ticket_medio = (float(total_valor) / qtd_pedidos) if qtd_pedidos else 0.0
        numeros = list(pedidos_qs.values_list('pedi_nume', flat=True))
        itens_qs = Itenspedidospisos.objects.using(banco).filter(item_pedi__in=[str(n) for n in numeros])
        itens_contagem = itens_qs.count()
        try:
            clientes_distintos = pedidos_qs.exclude(pedi_clie__isnull=True).values('pedi_clie').distinct().count()
        except Exception:
            clientes_distintos = 0
        template_name = 'Home/home_pisos.html'
    elif dashboard_tipo == 'os':
        pedidos_qs = Ordemservico.objects.using(banco).filter(orde_data_aber__gte=ini, orde_data_aber__lte=fim)
        if empresa_id is not None:
            pedidos_qs = pedidos_qs.filter(orde_empr=empresa_id)
        if filial_id is not None:
            pedidos_qs = pedidos_qs.filter(orde_fili=filial_id)
        total_valor = pedidos_qs.aggregate(v=Sum('orde_tota')).get('v') or 0
        qtd_pedidos = pedidos_qs.count()
        ticket_medio = (float(total_valor) / qtd_pedidos) if qtd_pedidos else 0.0
        total_pecas = Ordemservicopecas.objects.using(banco).filter(peca_orde__in=pedidos_qs.values_list('orde_nume', flat=True)).count()
        total_servicos = Ordemservicoservicos.objects.using(banco).filter(serv_orde__in=pedidos_qs.values_list('orde_nume', flat=True)).count()
        itens_contagem = qtd_pedidos + total_pecas + total_servicos
        try:
            clientes_distintos = pedidos_qs.exclude(orde_enti__isnull=True).values('orde_enti').distinct().count()
        except Exception:
            clientes_distintos = 0
        template_name = 'Home/home_os.html'
    else:
        pedidos_qs = PedidoVenda.objects.using(banco).filter(pedi_canc=False, pedi_data__gte=ini, pedi_data__lte=fim)
        if empresa_id is not None:
            pedidos_qs = pedidos_qs.filter(pedi_empr=empresa_id)
        if filial_id is not None:
            pedidos_qs = pedidos_qs.filter(pedi_fili=filial_id)
        if vendedor_selecionado:
            try:
                vend_ids = list(
                    Entidades.objects.using(banco)
                    .filter(enti_tipo_enti='VE', enti_nome__iexact=vendedor_selecionado)
                    .values_list('enti_clie', flat=True)
                )
                if vend_ids:
                    pedidos_qs = pedidos_qs.filter(pedi_vend__in=[str(v) for v in vend_ids])
                else:
                    pedidos_qs = pedidos_qs.none()
            except Exception:
                pedidos_qs = pedidos_qs.none()
        total_valor = pedidos_qs.aggregate(v=Sum('pedi_tota')).get('v') or 0
        qtd_pedidos = pedidos_qs.count()
        ticket_medio = (float(total_valor) / qtd_pedidos) if qtd_pedidos else 0.0
        numeros = list(pedidos_qs.values_list('pedi_nume', flat=True))
        itens_qs = Itenspedidovenda.objects.using(banco).filter(iped_pedi__in=[str(n) for n in numeros])
        custo_expr = ExpressionWrapper(F('iped_cust') * F('iped_quan'), output_field=DecimalField(max_digits=15, decimal_places=4))
        total_custo = itens_qs.aggregate(c=Sum(custo_expr)).get('c') or 0
        lucro_valor = (float(total_valor) - float(total_custo)) if total_valor else 0.0
        lucro_percent = (lucro_valor / float(total_valor) * 100.0) if total_valor else 0.0
        itens_contagem = itens_qs.count()

    context = {
        'vendedores': vendedores_qs,
        'vendedor_selecionado': vendedor_selecionado,
        'labels': json.dumps([]),
        'total_pedidos': json.dumps([]),
        'total_valor_pedido': json.dumps([]),
        'data_inicio': di,
        'data_fim': df,
        'dashboard_variant': dashboard_tipo,
        'slug': slug_client or (request.session.get('slug') or ''),
        'kpis': {
            'total_valor': float(total_valor),
            'lucro_percent': float(lucro_percent),
            'ticket_medio': float(ticket_medio),
            'qtd_pedidos': int(qtd_pedidos),
            'itens_contagem': int(itens_contagem),
            'clientes_distintos': int(clientes_distintos),
        },
    }
    return render(request, template_name, context)



def web_login(request):
    """Página de login web que usa as APIs de Licenças."""
    return render(request, 'Licencas/login.html')


@ensure_csrf_cookie
def selecionar_empresa(request):
    # Tentar capturar slug do Referer caso não esteja na sessão
    try:
        if not request.session.get('slug'):
            from urllib.parse import urlparse
            ref = request.META.get('HTTP_REFERER', '')
            p = urlparse(ref).path.strip('/').split('/')
            if len(p) >= 3 and p[0] == 'web' and p[1] == 'home':
                cand = (p[2] or '').strip()
                if cand:
                    request.session['slug'] = cand
                    logger.info(f"[selecionar_empresa] slug via Referer: {cand}")
    except Exception:
        pass

    # -----------------------------
    # GET → só renderiza
    # -----------------------------
    if request.method == 'GET':
        return render(request, 'Licencas/selecionar_empresa_filial.html')

    # -----------------------------
    # POST
    # -----------------------------
    # dentro de selecionar_empresa — substitua a seção POST existente por isto
    try:
        empresa_id = request.POST.get('empresa_id') or request.POST.get('empresa')
        filial_id = request.POST.get('filial_id') or request.POST.get('filial')
        empresa_nome = request.POST.get('empresa_nome')
        filial_nome = request.POST.get('filial_nome')
        slug_post = (request.POST.get('slug') or '').strip()

        logger.info("[selecionar_empresa] POST recebido: empresa_id=%s filial_id=%s empresa_nome=%s filial_nome=%s HEADERS=%s COOKIES=%s",
                    empresa_id, filial_id, empresa_nome, filial_nome,
                    {k:v for k,v in request.headers.items() if k.lower().startswith('x-')},
                    request.META.get('HTTP_COOKIE'))

        if not empresa_id or not filial_id:
            logger.warning("[selecionar_empresa] POST incompleto - ids ausentes")
            return render(request, 'Licencas/selecionar_empresa_filial.html', {
                'error': 'Empresa e filial são obrigatórias.'
            })

        try:
            empresa_id_int = int(empresa_id)
            filial_id_int = int(filial_id)
        except ValueError:
            logger.exception("[selecionar_empresa] IDs inválidos na seleção de empresa/filial")
            return render(request, 'Licencas/selecionar_empresa_filial.html', {
                'error': 'IDs inválidos.'
            })

        # --- atualiza sessão ---
        # preserva chaves críticas (usua_codi, docu, slug) e atualiza empresa/filial
        keep = {
            'usua_codi': request.session.get('usua_codi'),
            'docu': request.session.get('docu'),
            'slug': request.session.get('slug')
        }

        request.session['empresa_id'] = empresa_id_int
        request.session['filial_id'] = filial_id_int
        if slug_post:
            request.session['slug'] = slug_post

        # nomes (sua lógica)
        ...
        # (mantém o bloco que busca empresa_nome/filial_nome)

        if empresa_nome:
            request.session['empresa_nome'] = empresa_nome
        if filial_nome:
            request.session['filial_nome'] = filial_nome

        # garantir que sessão foi modificada e persistida imediatamente
        request.session.modified = True
        try:
            saved = False
            for _ in range(2):
                try:
                    request.session.save()
                    saved = True
                    break
                except RuntimeError as e:
                    if "session was deleted" in str(e) or "session was deleted before the request completed" in str(e):
                        try:
                            request.session.cycle_key()
                        except Exception:
                            pass
                        continue
                    raise
            if not saved:
                logger.exception("[selecionar_empresa] falha ao salvar session")
        except Exception as e:
            logger.exception("[selecionar_empresa] falha ao salvar session: %s", e)

        logger.info("[selecionar_empresa] Sessão atualizada OK: emp=%s (%s) fil=%s (%s) session_snapshot=%s",
                    empresa_id_int, empresa_nome, filial_id_int, filial_nome,
                    {k: request.session.get(k) for k in ['usua_codi','docu','slug','empresa_id','filial_id']})
        try:
            prev_slug = keep.get('slug')
            cur_slug = request.session.get('slug')
            if prev_slug != cur_slug:
                logger.debug("[selecionar_empresa] SLUG trocado: %s -> %s", prev_slug, cur_slug)
        except Exception:
            pass

        # REDIRECT — usa slug salvo
        slug_cur = request.session.get('slug')
        if slug_cur:
            emp = request.session.get('empresa_id')
            fil = request.session.get('filial_id')
            if emp is not None and fil is not None:
                try:
                    return redirect('home_slug_context', slug=slug_cur, empresa=int(emp), filial=int(fil))
                except Exception as e:
                    logger.exception("[selecionar_empresa] redirect home_slug_context falhou: %s", e)
                    return redirect('home_slug', slug=slug_cur)
            return redirect('home_slug', slug=slug_cur)
        return redirect('home')

    except Exception as exc:
        logger.exception("Erro inesperado em selecionar_empresa: %s", exc)
        return render(request, 'Licencas/selecionar_empresa_filial.html', {
            'error': 'Erro interno ao salvar seleção.'
        })



from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

VERIFY_TOKEN = "spartacus_whatsapp"
WHATSAPP_TOKEN = "EAAQgPjzxzfkBQGrnrbtrHYkOt32JZAxkGhmFNlS5eBWelW80swgkHXfoWQVOWbzafFRy6mkRHNV6l7Fs3PC4hVZCcVERSDWoqYI618ZAddXh6h8c6LVJq4xD8MeEqYwrMqlxJg4B7nIhkwZCr0Rw4Xpt9GnfNyrA22HSHicA5ZChokd29Ap7OoFPe66CflXVt2lnLGyv2ZCFeM2pApvphznrSbJdHJ7SOeYEIFPAz9ZCsao8xFuFUc6MoBHV2egP8Hfbxs8QfEdmQ1LI0Ip8BzDHl0L"   # da Meta
PHONE_NUMBER_ID = "S762237033644517"  # da Meta

# ====== Enviar mensagem pelo WhatsApp ======
def enviar_whatsapp(to, texto):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": texto},
    }
    requests.post(url, json=payload, headers=headers)


# ====== Webhook ======
@csrf_exempt
def whatsapp_webhook(request):

    # ---------- GET: verificação inicial ----------
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge)

        return HttpResponse("Erro de verificação", status=403)

    # ---------- POST: mensagens vindas do WhatsApp ----------
    if request.method == "POST":
        data = json.loads(request.body)

        try:
            mensagem = data["entry"][0]["changes"][0]["value"]["messages"][0]
            telefone = mensagem["from"]
            texto = mensagem.get("text", {}).get("body", "")
        except Exception:
            return HttpResponse("OK")

        # Seu agente
        from Assistente_Spart.agenteReact import processar_mensagem

        resposta = processar_mensagem(
            texto,
            contexto={
                "banco": "default",
                "empresa_id": "1",
                "filial_id": "1"
            }
        )

        enviar_whatsapp(telefone, resposta["output"])
        return HttpResponse("OK")

    return HttpResponse("Método não permitido", status=405)


# ========== VERIFICAÇÃO (GET) ==========
def webhook_verify(request):
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return HttpResponse(challenge)
    return HttpResponse("Erro de verificação", status=403)

# ========== RECEBIMENTO (POST) ==========
@csrf_exempt
def webhook_receive(request):
    dados = json.loads(request.body.decode("utf-8"))

    try:
        mensagens = dados["entry"][0]["changes"][0]["value"].get("messages", [])
    except:
        return JsonResponse({"status": "sem mensagens"})

    for msg in mensagens:
        if msg.get("type") == "text":
            texto = msg["text"]["body"]
            user_number = msg["from"]

            resposta = agenteReact.invoke({"input": texto})
            resposta_final = resposta["output_text"]

            enviar_whatsapp(user_number, resposta_final)

    return JsonResponse({"status": "ok"})

# ========== ENVIO ==========
def enviar_whatsapp(to, texto):
    url = f"https://graph.facebook.com18.0/{WHATS_PHONE_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": texto}
    }

    headers = {
        "Authorization": f"Bearer {WHATS_TOKEN}",
        "Content-Type": "application/json"
    }

    requests.post(url, headers=headers, json=payload)




from onboarding.services import mark_step_done, get_onboarding_state

def complete_onboarding_step(request, step, slug=None):
    banco = 'default'
    try:
        banco = get_licenca_db_config(request) or banco
    except Exception:
        try:
            slug_sess = request.session.get('slug')
            if slug_sess:
                banco = get_db_from_slug(slug_sess) or banco
        except Exception:
            pass
    empresa_id = request.session.get('empresa_id')
    logger.info(
        "[complete_onboarding_step] Sessão atualizada: empresa_id=%s",
        request.session.get('empresa_id')
    )
    try:
        if empresa_id:
            mark_step_done(request.user, empresa_id, step, db_alias=banco)
    except Exception:
        pass
    next_url = reverse('home')
    try:
        state = get_onboarding_state(request.user, empresa_id, db_alias=banco)
        nxt = state.get('next_step') if state else None
        if nxt:
            ns = nxt.get('slug')
            if ns == 'empresa':
                next_url = reverse('empresas_web', kwargs={'slug': slug}) if slug else reverse('empresas_web_default')
            elif ns == 'filial':
                next_url = reverse('filiais_web', kwargs={'slug': slug}) if slug else reverse('empresas_web_default')
            elif ns == 'cfop':
                next_url = reverse('cfop_list_web', kwargs={'slug': slug}) if slug else reverse('empresas_web_default')
            elif ns == 'series':
                next_url = reverse('series_list_web', kwargs={'slug': slug}) if slug else reverse('empresas_web_default')
    except Exception:
        pass
    return redirect(next_url)


def home_redirect_legacy(request, slug):
    try:
        try:
            docu = request.session.get('docu')
            expected = None
            if docu:
                from core.licenca_context import get_licencas_map
                expected = next((x['slug'] for x in get_licencas_map() if x.get('cnpj') == docu), None)
            if expected and expected != slug:
                emp = request.session.get('empresa_id')
                fil = request.session.get('filial_id')
                if emp is not None and fil is not None:
                    return redirect('home_slug_context', slug=expected, empresa=int(emp), filial=int(fil))
                return redirect('home_slug', slug=expected)
        except Exception:
            pass
        emp = request.session.get('empresa_id')
        fil = request.session.get('filial_id')
        if emp is not None and fil is not None:
            try:
                emp_i = int(emp)
                fil_i = int(fil)
                return redirect('home_slug_context', slug=slug, empresa=emp_i, filial=fil_i)
            except Exception:
                return redirect('home_slug', slug=slug)
        return redirect('home_slug', slug=slug)
    except Exception:
        return redirect('home')

def selecionar_empresa_redirect(request, empresa, filial):
    try:
        request.session['empresa_id'] = int(empresa)
        request.session['filial_id'] = int(filial)
        request.session.modified = True
        try:
            saved = False
            for _ in range(2):
                try:
                    request.session.save()
                    saved = True
                    break
                except RuntimeError as e:
                    if "session was deleted" in str(e) or "session was deleted before the request completed" in str(e):
                        try:
                            request.session.cycle_key()
                        except Exception:
                            pass
                        continue
                    raise
            if not saved:
                logger.exception("[selecionar_empresa_redirect] falha ao salvar sessão")
        except Exception:
            logger.exception("[selecionar_empresa_redirect] falha ao salvar sessão")
    except Exception:
        logger.exception("[selecionar_empresa_redirect] erro ao parse ids")
    ...


def selecionar_empresa_redirect_slug(request, slug, empresa, filial):
    try:
        request.session['slug'] = (slug or '').strip()
        request.session['empresa_id'] = int(empresa)
        request.session['filial_id'] = int(filial)
        request.session.modified = True
        try:
            saved = False
            for _ in range(2):
                try:
                    request.session.save()
                    saved = True
                    break
                except RuntimeError as e:
                    if "session was deleted" in str(e) or "session was deleted before the request completed" in str(e):
                        try:
                            request.session.cycle_key()
                        except Exception:
                            pass
                        continue
                    raise
            if not saved:
                logger.exception("[selecionar_empresa_redirect_slug] falha ao salvar sessão")
        except Exception:
            logger.exception("[selecionar_empresa_redirect_slug] falha ao salvar sessão")
    except Exception:
        logger.exception("[selecionar_empresa_redirect_slug] erro ao parse ids/slug")
    ...
