# views.py
from django.http import JsonResponse
from django.views.generic import TemplateView
from ...models import CFOPFiscal, CFOP, MapaCFOP

def cfop_autocomplete(request, slug=None):
    q = request.GET.get("q", "").strip()

    qs = CFOPFiscal.objects.all()

    if q:
        qs = qs.filter(
            cfop_codi__icontains=q
        ) | qs.filter(
            cfop_desc__icontains=q
        )

    return JsonResponse({
        "results": [
            {"value": c.cfop_codi, "label": f"{c.cfop_codi} - {c.cfop_desc}"}
            for c in qs[:30]
        ]
    })


def cfop_sugerir(request, slug=None):
    tipo = (request.GET.get('tipo') or '').strip()
    uf_orig = (request.GET.get('uf_origem') or '').strip()
    uf_dest = (request.GET.get('uf_destino') or '').strip()
    data = []
    if tipo and uf_orig and uf_dest:
        qs = MapaCFOP.objects.all().select_related('cfop')
        qs = qs.filter(tipo_oper=tipo, uf_origem=uf_orig, uf_destino=uf_dest)
        for m in qs[:10]:
            data.append({
                'value': m.cfop.cfop_codi,
                'label': f"{m.cfop.cfop_codi} - {m.cfop.cfop_desc}"
            })
    return JsonResponse({'results': data})


class CFOPWizardView(TemplateView):
    template_name = 'CFOP/cfop_wizard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = kwargs.get('slug')
        return ctx
