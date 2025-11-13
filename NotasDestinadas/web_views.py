from django.views.generic import ListView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Licencas.models import Filiais
from .models import NotaFiscalEntrada
from django.db.models import Q

class NotasDestinadasListView(ListView):
    model = NotaFiscalEntrada
    template_name = 'NotasDestinadas/destinadas_lista.html'
    context_object_name = 'notas'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = NotaFiscalEntrada.objects.using(self.db_alias).all()
        cnpj = self.request.GET.get('cnpj')
        if not cnpj and self.empresa_id and self.filial_id:
            filial = Filiais.objects.using(self.db_alias).filter(empr_empr=int(self.filial_id), empr_codi=int(self.empresa_id)).first()
            if filial:
                cnpj = filial.empr_docu
        if cnpj:
            import re
            digits = re.sub(r"\D", "", str(cnpj))
            masked = f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}" if len(digits)==14 else digits
            qs = qs.filter(Q(destinatario_cnpj__in=[digits, masked])).exclude(Q(emitente_cnpj__in=[digits, masked]))
        qs = qs.order_by('-data_emissao','-numero_nota_fiscal')
        return qs
