from django.http import JsonResponse
from django.shortcuts import render
import json
from Entidades.models import Entidades
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
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
    # Carrega vendedores e mantém seleção enviada por GET
    vendedor_selecionado = (request.GET.get('vendedor') or '').strip()
    vendedores_qs = Entidades.objects.filter(enti_tipo_enti='VE').order_by('enti_nome')

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
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id') or request.POST.get('empresa')
        filial_id = request.POST.get('filial_id') or request.POST.get('filial')
        empresa_nome = request.POST.get('empresa_nome')
        filial_nome = request.POST.get('filial_nome')

        if not empresa_id or not filial_id:
            # Para chamadas AJAX, retornar JSON 400
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
        if empresa_nome:
            request.session['empresa_nome'] = empresa_nome
        if filial_nome:
            request.session['filial_nome'] = filial_nome

        # Em chamadas AJAX, retornar JSON de sucesso com URL de redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'redirect': '/web/home/'})
        # Feedback opcional via messages pode ser adicionado aqui
        from django.shortcuts import redirect
        return redirect('home')

    return render(request, 'Licencas/selecionar_empresa_filial.html')