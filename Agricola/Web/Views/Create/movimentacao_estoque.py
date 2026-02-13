from django.urls import reverse_lazy
from .base import BaseCreateView
from Agricola.models import MovimentacaoEstoque
from Agricola.Web.forms import MovimentacaoEstoqueForm
from Agricola.service.produto_agro_service import MovimentacaoEstoqueService
from Agricola.service.financeiro_service import AgricolaFinanceiroService
import json
from django.db import transaction
from django.shortcuts import redirect
from django.contrib import messages
from core.utils import get_licenca_db_config

class MovimentacaoEstoqueCreateView(BaseCreateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    template_name = 'Agricola/movimentacao_estoque_form.html'
    def get_success_url(self):
        from django.urls import reverse
        return reverse('AgricolaWeb:movimentacao_estoque_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'

    def post(self, request, *args, **kwargs):
        if "movimentacoes_json" in request.POST and request.POST.get("movimentacoes_json"):
            try:
                items = json.loads(request.POST.get("movimentacoes_json"))
                
                # Get DB name correctly
                banco = get_licenca_db_config(request) or 'default'
                db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')

                with transaction.atomic(using=db_name):
                    self.registrar_inumeras_movimentacoes(items, db_name)
                
                messages.success(request, f"{len(items)} movimentações registradas com sucesso.")
                return redirect(self.get_success_url())
                
            except Exception as e:
                messages.error(request, f"Erro ao processar movimentações: {str(e)}")
                # Initialize self.object to None to avoid AttributeError in get_context_data
                self.object = None
                return self.render_to_response(self.get_context_data(form=self.get_form()))

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        
        # Safe access to tenant fields
        self.object.movi_estq_empr = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        self.object.movi_estq_fili = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        
        # Ensure user is set if required by model
        if hasattr(self.request.user, 'username'):
             self.object.movi_estq_usua = self.request.user.username
        else:
             self.object.movi_estq_usua = str(self.request.user)
             
        # Get DB name
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        self.object.save(using=db_name)
        
        # Gerar financeiro se necessário
        try:
            AgricolaFinanceiroService.gerar_titulo_movimentacao(self.object, using=db_name)
        except Exception as e:
            # Log error but don't fail the request? Or show warning?
            # User wants to generate financial, so failure might be important.
            # But the movement is already saved.
            messages.warning(self.request, f"Movimentação salva, mas erro ao gerar financeiro: {e}")

        return super().form_valid(form)
    
    def registrar_inumeras_movimentacoes(self, movimentacoes, db_name):
        from decimal import Decimal
        # Retrieve tenant info once
        empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        
        # Retrieve user info once
        if hasattr(self.request.user, 'username'):
             usuario = self.request.user.username
        else:
             usuario = str(self.request.user)

        for movimentacao in movimentacoes:
            # Prepare data with system fields
            data = movimentacao.copy()
            data["movi_estq_empr"] = empresa
            data["movi_estq_fili"] = filial
            data["movi_estq_usua"] = usuario
            
            # Handle numeric conversions
            if data.get("movi_estq_quant"):
                data["movi_estq_quant"] = Decimal(str(data["movi_estq_quant"]))
            
            if data.get("movi_estq_cust_unit"):
                data["movi_estq_cust_unit"] = Decimal(str(data["movi_estq_cust_unit"]))
            else:
                data["movi_estq_cust_unit"] = None

            # Calculate total cost
            if data.get("movi_estq_cust_unit") and data.get("movi_estq_quant"):
                data["movi_estq_cust_tota"] = data["movi_estq_quant"] * data["movi_estq_cust_unit"]
            
            # Remove helper fields if they exist
            data.pop('fazeText', None)
            data.pop('prodText', None)
            data.pop('entiText', None) # Remove entity text helper if exists

            # Handle empty financial fields
            if not data.get("movi_estq_enti"):
                data["movi_estq_enti"] = None
            
            if not data.get("movi_estq_venc"):
                data["movi_estq_venc"] = None
                
            if not data.get("movi_estq_form_paga"):
                data["movi_estq_form_paga"] = None

            created_mov = MovimentacaoEstoqueService.registrar_movimentacao(
                data=data,
                using=db_name,
            )
            
            # Gerar financeiro
            AgricolaFinanceiroService.gerar_titulo_movimentacao(created_mov, using=db_name)
