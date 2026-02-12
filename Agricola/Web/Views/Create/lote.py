from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from .base import BaseCreateView
from Agricola.models import LoteProdutos, ProdutoAgro
from Agricola.Web.forms import LoteProdutosForm
from Agricola.service.lote_service import LoteService
from core.utils import get_licenca_db_config
import re

class LoteCreateView(BaseCreateView):
    model = LoteProdutos
    form_class = LoteProdutosForm
    template_name = 'Agricola/parciais/lote_form.html'
    empresa_field = 'lote_empr'
    filial_field = 'lote_fili'

    def get_success_url(self):
        from django.urls import reverse
        return reverse(
            'AgricolaWeb:lote_list',
            kwargs={'slug': self.kwargs['slug']}
        )

    def execute_create(self, form, db_name):
        data = form.cleaned_data.copy()
        
        # injeta empresa/filial que o Base colocou na instância
        data["lote_empr"] = getattr(self.object, "lote_empr")
        data["lote_fili"] = getattr(self.object, "lote_fili")

        return LoteService.criar_lote(
            data=data,
            using=db_name
        )

class LoteFormHTMXView(View):
    def get(self, request, produto_id, slug=None):
        # Log inicial para debug
        print(f"[DEBUG] LoteFormHTMXView.get: path={request.path}, produto_id={produto_id}, slug_arg={slug}")
        
        # Estratégia de recuperação de slug em cascata
        # 1. Argumento da view (já capturado pelo URL conf)
        final_slug = slug

        # 2. Kwargs da view (injetado pelo setup)
        if not final_slug and hasattr(self, 'kwargs'):
            final_slug = self.kwargs.get('slug')

        # 3. Resolver match do request
        if not final_slug and request.resolver_match:
            final_slug = request.resolver_match.kwargs.get('slug')

        # 4. Regex na URL (Padrão /web/<slug>/...)
        if not final_slug:
            match = re.search(r'/web/([^/]+)/', request.path)
            if match:
                final_slug = match.group(1)

        # 5. Split manual (último recurso)
        if not final_slug:
            parts = request.path.split('/')
            if 'web' in parts:
                try:
                    idx = parts.index('web') + 1
                    if idx < len(parts) and parts[idx]:
                        final_slug = parts[idx]
                except:
                    pass

        # 6. Fallback absoluto para evitar erro 500 na renderização da URL
        if not final_slug:
            print("[WARN] Slug não encontrado em nenhuma etapa. Usando 'default'.")
            final_slug = 'default'

        print(f"[DEBUG] Slug resolvido: '{final_slug}'")

        try:
            # Configuração do banco de dados
            db_name = get_licenca_db_config(request) or 'default'
            
            # Busca do produto
            produto = get_object_or_404(ProdutoAgro.objects.using(db_name), pk=produto_id)
            
            # Instanciação do formulário
            form = LoteProdutosForm(initial={
                'lote_empr': produto.prod_empr_agro,
                'lote_fili': produto.prod_fili_agro,
                'lote_prod': produto.pk,
            })
            
            context = {
                'form': form, 
                'produto_id': produto_id, 
                'slug': final_slug
            }
            
            return render(request, 'Agricola/parciais/lote_form.html', context)
            
        except Exception as e:
            print(f"[ERROR] Erro ao renderizar modal de lote: {e}")
            import traceback
            traceback.print_exc()
            # Retorna um erro formatado para o HTMX exibir se possível, ou 500 genérico
            from django.http import HttpResponseServerError
            return HttpResponseServerError(f"Erro ao carregar formulário: {e}")


class LoteCreateHTMXView(View):
    def post(self, request, produto_id, slug=None):
        print(f"[DEBUG] LoteCreateHTMXView.post: path={request.path}, produto_id={produto_id}, slug_arg={slug}")
        
        # 1. Recuperação robusta de slug
        final_slug = slug
        
        if not final_slug and hasattr(self, 'kwargs'):
            final_slug = self.kwargs.get('slug')
            
        if not final_slug and request.resolver_match:
            final_slug = request.resolver_match.kwargs.get('slug')
            
        if not final_slug:
            match = re.search(r'/web/([^/]+)/', request.path)
            if match:
                final_slug = match.group(1)
        
        if not final_slug:
            parts = request.path.split('/')
            if 'web' in parts:
                try:
                    idx = parts.index('web') + 1
                    if idx < len(parts) and parts[idx]:
                        final_slug = parts[idx]
                except:
                    pass

        if not final_slug:
            print("[WARN] Slug não encontrado no POST. Usando 'default'.")
            final_slug = 'default'
            
        print(f"[DEBUG] Slug resolvido no POST: '{final_slug}'")

        try:
            db_name = get_licenca_db_config(request) or 'default'
            
            form = LoteProdutosForm(request.POST)
            
            if form.is_valid():
                data = form.cleaned_data
                # Adiciona campos hidden se não vierem no form (embora devessem vir)
                # Mas LoteService espera um dict com dados
                
                try:
                    LoteService.criar_lote(data=data, using=db_name)
                    print("[INFO] Lote criado com sucesso")
                    
                    # Retorna mensagem de sucesso e fecha modal via script no template ou evento htmx
                    # Mas o padrão aqui parece ser retornar a lista atualizada ou nada?
                    # O código anterior retornava lote_list.html com os lotes.
                    # Vamos manter isso, mas verificar se lote_list.html precisa de slug?
                    
                    lotes = LoteProdutos.objects.using(db_name).filter(lote_prod=produto_id)
                    # Se lote_list.html precisar de slug para urls de edição/exclusão, precisamos passar
                    return render(request, 'Agricola/parciais/lote_list.html', {
                        'lotes': lotes, 
                        'produto_id': produto_id,
                        'slug': final_slug
                    })
                    
                except Exception as e:
                    print(f"[ERROR] Erro ao salvar lote: {e}")
                    form.add_error(None, f"Erro ao salvar: {e}")
            
            # Se inválido ou erro ao salvar
            print("[WARN] Formulário inválido ou erro ao salvar")
            print(form.errors)
            return render(request, 'Agricola/parciais/lote_form.html', {
                'form': form, 
                'produto_id': produto_id, 
                'slug': final_slug
            })
            
        except Exception as e:
            print(f"[ERROR] Erro crítico no POST: {e}")
            import traceback
            traceback.print_exc()
            from django.http import HttpResponseServerError
            return HttpResponseServerError(f"Erro ao processar formulário: {e}")
