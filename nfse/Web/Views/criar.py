from django.shortcuts import render, redirect
from django.views import View

from core.mixin import DBAndSlugMixin
from nfse.Web.forms import NfseForm, NfseItemFormSet
from nfse.services.context import NfseContext
from nfse.services.emissao_service import EmissaoNfseService


class NfseCreateView(DBAndSlugMixin, View):
    template_name = 'nfse/form.html'

    def get(self, request, *args, **kwargs):
        form = NfseForm()
        item_formset = NfseItemFormSet(prefix='itens')
        return render(request, self.template_name, {
            'form': form,
            'item_formset': item_formset,
            'slug': self.slug,
        })

    def post(self, request, *args, **kwargs):
        form = NfseForm(request.POST)
        item_formset = NfseItemFormSet(request.POST, prefix='itens')

        if not form.is_valid() or not item_formset.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'item_formset': item_formset,
                'slug': self.slug,
                'error': form.errors.as_json(),
                'item_error': item_formset.errors.as_json(),
                'modo': 'criar',
            })

        itens = []
        for item_form in item_formset:
            if not item_form.cleaned_data:
                continue
            if item_form.cleaned_data.get('DELETE'):
                continue

            itens.append({
                'descricao': item_form.cleaned_data['descricao'],
                'quantidade': item_form.cleaned_data['quantidade'],
                'valor_unitario': item_form.cleaned_data['valor_unitario'],
                'valor_total': item_form.cleaned_data['valor_total'],
                'servico_codigo': item_form.cleaned_data.get('servico_codigo'),
                'cnae_codigo': item_form.cleaned_data.get('cnae_codigo'),
                'lc116_codigo': item_form.cleaned_data.get('lc116_codigo'),
            })

        data = form.cleaned_data
        data['itens'] = itens

        context = NfseContext.from_request(request, self.slug)
        EmissaoNfseService.emitir(context, data)

        return redirect('nfse_web:listar', slug=self.slug)