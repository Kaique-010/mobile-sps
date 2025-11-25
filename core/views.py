from django.http import JsonResponse
from django.shortcuts import render
import json
from Entidades.models import Entidades
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

    vendedor_selecionado = (request.GET.get('vendedor') or '').strip()
    vendedores_qs = Entidades.objects.using(banco).filter(enti_tipo_enti='VE')
    logger.info(f"[home] vendedores_qs: {vendedores_qs}")
    if empresa_id is not None:
        vendedores_qs = vendedores_qs.filter(enti_empr=empresa_id)
    else:
        vendedores_qs = vendedores_qs.filter(enti_empr=-1)
    vendedores_qs = vendedores_qs.order_by('enti_nome')

    labels = []
    total_pedidos = []
    total_valor_pedido = []
    context = {
        'vendedores': vendedores_qs,
        'vendedor_selecionado': vendedor_selecionado,
        'labels': json.dumps(labels),
        'total_pedidos': json.dumps(total_pedidos),
        'total_valor_pedido': json.dumps(total_valor_pedido),
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),
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
