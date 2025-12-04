from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
import json
from Entidades.models import Entidades
from Pedidos.models import PedidoVenda, Itenspedidovenda
from Pisos.models import Pedidospisos, Itenspedidospisos
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q
from django.db import connections
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from core.utils import get_licenca_db_config, get_db_from_slug
import logging

logger = logging.getLogger(__name__)

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


def home(request):
    try:
        banco = get_licenca_db_config(request) or 'default'
        logger.info(f"[home] banco: {banco}")
    except Exception:
        banco = 'default'
    # Fallback: se banco for 'default', tentar usar slug salvo em sessão
    if banco == 'default':
        try:
            slug_sess = request.session.get('slug')
            if slug_sess:
                banco = get_db_from_slug(slug_sess) or banco
                logger.info(f"[home] banco via sessão.slug: {banco}")
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

    vendedor_selecionado = (request.GET.get('vendedor') or '').strip()
    vendedores_qs = Entidades.objects.using(banco).filter(enti_tipo_enti='VE')
    logger.info(f"[home] vendedores_qs: {vendedores_qs}")
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

    pedidos_qs = PedidoVenda.objects.using(banco).filter(pedi_canc=False, pedi_data__gte=ini, pedi_data__lte=fim)
    mods = getattr(request, 'modulos_disponiveis', []) or []
    usa_pisos = any(str(m).strip().lower() == 'pisos' for m in mods)
    pedidopisos = None
    tabela_pisos_ok = False
    if usa_pisos:
        try:
            tabela_pisos_ok = 'pedidospisos' in connections[banco].introspection.table_names()
        except Exception:
            tabela_pisos_ok = False
        if tabela_pisos_ok:
            pedidopisos = Pedidospisos.objects.using(banco).filter(pedi_data__gte=ini, pedi_data__lte=fim).exclude(pedi_stat=1)
    if empresa_id is not None:
        pedidos_qs = pedidos_qs.filter(pedi_empr=empresa_id)
        
    if empresa_id is not None and pedidopisos is not None:
        pedidopisos = pedidopisos.filter(pedi_empr=empresa_id)
    
    if filial_id is not None:
        pedidos_qs = pedidos_qs.filter(pedi_fili=filial_id)
    if filial_id is not None and pedidopisos is not None:
        pedidopisos = pedidopisos.filter(pedi_fili=filial_id)
    
    if vendedor_selecionado:
        try:
            vend_ids = list(
                Entidades.objects.using(banco)
                .filter(enti_tipo_enti='VE', enti_nome__iexact=vendedor_selecionado)
                .values_list('enti_clie', flat=True)
            )
            if vend_ids:
                pedidos_qs = pedidos_qs.filter(pedi_vend__in=[str(v) for v in vend_ids])
                if pedidopisos is not None:
                    pedidopisos = pedidopisos.filter(pedi_vend__in=[str(v) for v in vend_ids])
            else:
                pedidos_qs = pedidos_qs.none()
                pedidopisos = pedidopisos.none() if pedidopisos is not None else None
        except Exception:
            pedidos_qs = pedidos_qs.none()
            pedidopisos = pedidopisos.none() if pedidopisos is not None else None

    total_valor = pedidos_qs.aggregate(v=Sum('pedi_tota')).get('v') or 0
    total_valor_pisos = (pedidopisos.aggregate(v=Sum('pedi_tota')).get('v') if pedidopisos is not None else 0) or 0
    
    qtd_pedidos = pedidos_qs.count()
    qtd_pedidos_pisos = pedidopisos.count() if pedidopisos is not None else 0
    ticket_medio = (float(total_valor) / qtd_pedidos) if qtd_pedidos else 0.0
    ticket_medio_pisos = (float(total_valor_pisos) / qtd_pedidos_pisos) if qtd_pedidos_pisos else 0.0

    numeros = list(pedidos_qs.values_list('pedi_nume', flat=True))
    numeros_pisos = list(pedidopisos.values_list('pedi_nume', flat=True)) if pedidopisos is not None else []
    itens_qs = Itenspedidovenda.objects.using(banco).filter(iped_pedi__in=[str(n) for n in numeros])
    itens_qs_pisos = Itenspedidospisos.objects.using(banco).filter(item_pedi__in=[int(n) for n in numeros_pisos]) if numeros_pisos else Itenspedidospisos.objects.none()
    custo_expr = ExpressionWrapper(F('iped_cust') * F('iped_quan'), output_field=DecimalField(max_digits=15, decimal_places=4))
    
    total_custo = itens_qs.aggregate(c=Sum(custo_expr)).get('c') or 0
    total_custo_pisos = 0
    lucro_valor = (float(total_valor) - float(total_custo)) if total_valor else 0.0
    lucro_valor_pisos = 0.0
    lucro_percent = (lucro_valor / float(total_valor) * 100.0) if total_valor else 0.0
    lucro_percent_pisos = 0.0    
    itens_contagem = itens_qs.count()
    itens_contagem_pisos = itens_qs_pisos.count()

    # 'usa_pisos' já definido acima e só será verdadeiro se houver módulo e tabela disponível

    kpis_normal = {
        'total_valor': float(total_valor),
        'lucro_percent': float(lucro_percent),
        'ticket_medio': float(ticket_medio),
        'qtd_pedidos': int(qtd_pedidos),
        'itens_contagem': int(itens_contagem),
    }
    kpis_pisos = {
        'total_valor': float(total_valor_pisos),
        'lucro_percent': float(lucro_percent_pisos),
        'ticket_medio': float(ticket_medio_pisos),
        'qtd_pedidos': int(qtd_pedidos_pisos),
        'itens_contagem': int(itens_contagem_pisos),
    }

    context = {
        'vendedores': vendedores_qs,
        'vendedor_selecionado': vendedor_selecionado,
        'labels': json.dumps([]),
        'total_pedidos': json.dumps([]),
        'total_valor_pedido': json.dumps([]),
        'data_inicio': di,
        'data_fim': df,
        'usa_pisos': usa_pisos,
        'kpis': (kpis_pisos if usa_pisos else kpis_normal),
        'kpis_normal': kpis_normal,
        'kpis_pisos': kpis_pisos,
    }
    return render(request, 'home.html', context)


def web_login(request):
    """Página de login web que usa as APIs de Licenças."""
    return render(request, 'Licencas/login.html')


@ensure_csrf_cookie
def selecionar_empresa(request):
    """Página para seleção de empresa e filial após login.
    GET: Renderiza formulário.
    POST: Salva empresa/filial na sessão e redireciona para a Home.
    """
    # Persistir slug da licença na sessão para uso na Home sem slug
    try:
        parts = request.path.strip('/').split('/')
        slug = parts[1] if len(parts) > 1 else None
        if slug:
            request.session['slug'] = slug
            logger.info(f"[selecionar_empresa] slug salvo na sessão: {slug}")
    except Exception:
        pass# Persistir slug da licença na sessão para uso na Home sem slug
    try:
        parts = request.path.strip('/').split('/')
        slug = parts[1] if len(parts) > 1 else None
        if slug:
            request.session['slug'] = slug
            logger.info(f"[selecionar_empresa] slug salvo na sessão: {slug}")
    except Exception:
        pass

    if request.method == 'POST':
        try:
            empresa_id = request.POST.get('empresa_id') or request.POST.get('empresa')
            filial_id = request.POST.get('filial_id') or request.POST.get('filial')
            empresa_nome = request.POST.get('empresa_nome')
            filial_nome = request.POST.get('filial_nome')

            logger.info(
                "[selecionar_empresa] POST recebido: empresa_id=%s filial_id=%s empresa_nome=%s filial_nome=%s",
                empresa_id, filial_id, empresa_nome, filial_nome
            )

            if not empresa_id or not filial_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Empresa e filial são obrigatórias.'}, status=400)
                return render(request, 'Licencas/selecionar_empresa_filial.html', {
                    'error': 'Empresa e filial são obrigatórias.'
                })

            # Persistir na sessão com validação
            try:
                empresa_id_int = int(empresa_id)
                filial_id_int = int(filial_id)
            except (TypeError, ValueError) as exc:
                logger.exception("IDs inválidos na seleção de empresa/filial: empresa=%s filial=%s", empresa_id, filial_id)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'IDs inválidos para empresa/filial.'}, status=400)
                return render(request, 'Licencas/selecionar_empresa_filial.html', {
                    'error': 'IDs inválidos para empresa/filial.'
                })

            request.session['empresa_id'] = empresa_id_int
            request.session['filial_id'] = filial_id_int

            # Popular nomes na sessão caso não venham do POST
            if not empresa_nome or not filial_nome:
                try:
                    # Importar utilitário e modelos localmente para evitar dependência global
                    from core.utils import get_licenca_db_config
                    from Licencas.models import Empresas, Filiais
                    banco = get_licenca_db_config(request) or 'default'
                    if not empresa_nome:
                        emp_obj = (
                            Empresas.objects.using(banco)
                            .filter(empr_codi=empresa_id_int)
                            .only('empr_nome')
                            .first()
                        )
                        empresa_nome = getattr(emp_obj, 'empr_nome', None) if emp_obj else None
                    if not filial_nome:
                        fil_obj = (
                            Filiais.objects.using(banco)
                            .filter(empr_empr=empresa_id_int, empr_codi=filial_id_int)
                            .only('empr_nome')
                            .first()
                        )
                        filial_nome = getattr(fil_obj, 'empr_nome', None) if fil_obj else None
                except Exception as e:
                    logger.warning("[selecionar_empresa] Falha ao obter nomes pelo banco da licença: %s", e)

            if empresa_nome:
                request.session['empresa_nome'] = empresa_nome
            if filial_nome:
                request.session['filial_nome'] = filial_nome

            logger.info(
                "[selecionar_empresa] Sessão atualizada: empresa_id=%s (%s) filial_id=%s (%s)",
                request.session.get('empresa_id'), request.session.get('empresa_nome'),
                request.session.get('filial_id'), request.session.get('filial_nome')
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': '/web/home/'})
            from django.shortcuts import redirect
            return redirect('home')
        except Exception as exc:
            logger.exception("Erro inesperado em selecionar_empresa: %s", exc)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Erro interno ao salvar seleção.'}, status=500)
            return render(request, 'Licencas/selecionar_empresa_filial.html', {
                'error': 'Erro interno ao salvar seleção.'
            })

    return render(request, 'Licencas/selecionar_empresa_filial.html')


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
