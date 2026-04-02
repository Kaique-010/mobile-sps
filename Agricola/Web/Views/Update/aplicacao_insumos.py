from django.urls import reverse_lazy
from django.shortcuts import redirect
from .base import BaseUpdateView
from core.utils import get_licenca_db_config
from Agricola.models import AplicacaoInsumos, Talhao
from Agricola.Web.forms import AplicacaoInsumosForm
from Agricola.service.parametros import ParametroAgricolaService
from Agricola.service.produto_agro_service import MovimentacaoEstoqueService

class AplicacaoInsumosUpdateView(BaseUpdateView):
    model = AplicacaoInsumos
    form_class = AplicacaoInsumosForm
    template_name = 'Agricola/aplicacao_insumos_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:aplicacao_insumos_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'apli_empr'
    filial_field = 'apli_fili'

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        original = self.get_object()
        obj = form.save(commit=False)
        obj.save(using=db_name)
        form.save_m2m()
        empresa = getattr(obj, 'apli_empr')
        filial = getattr(obj, 'apli_fili')
        controla_estoque = ParametroAgricolaService.get(empresa, filial, "controla_estoque", using=db_name)
        if controla_estoque:
            delta = obj.apli_quant - original.apli_quant
            if delta != 0:
                talhao = None
                try:
                    talhao = Talhao.objects.using(db_name).get(id=str(obj.apli_talh))
                except Talhao.DoesNotExist:
                    talhao = None
                fazenda_id = talhao.talh_faze if talhao else None
                usuario = getattr(self.request.user, 'username', None) or str(self.request.user) or "sistema"
                data_mov = {
                    "movi_estq_empr": str(empresa),
                    "movi_estq_fili": str(filial),
                    "movi_estq_faze": str(fazenda_id) if fazenda_id is not None else str(obj.apli_talh),
                    "movi_estq_prod": str(obj.apli_prod),
                    "movi_estq_quant": abs(delta),
                    "movi_estq_tipo": "saida" if delta > 0 else "entrada",
                    "movi_estq_usua": usuario,
                    "movi_estq_docu_refe": f"APLI{obj.id}",
                    "movi_estq_moti": "Ajuste de aplicação de insumos"
                }
                try:
                    MovimentacaoEstoqueService.registrar_movimentacao(data=data_mov, using=db_name)
                except Exception:
                    pass
        return redirect(self.get_success_url())
