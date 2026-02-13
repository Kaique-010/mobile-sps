from django.http import JsonResponse
from django.views import View
from Agricola.models import Fazenda, Talhao, CategoriaProduto, ProdutoAgro, Animal
from Entidades.models import Entidades
from core.utils import get_licenca_db_config

class EntidadeAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        
        queryset = Entidades.objects.using(db_name).all()

        # Filter by tenant/empresa
        empresa = getattr(request.user, 'empresa', None)
        if hasattr(empresa, 'pk'):
            empresa = empresa.pk
        empresa = empresa or request.session.get('empresa_id', 1)

        # Entidades uses enti_empr only (no filial usually for shared entities, but let's check model)
        # Model has enti_empr.
        if empresa:
             queryset = queryset.filter(enti_empr=empresa)
        
        if pk:
            queryset = queryset.filter(enti_clie=pk)
        elif term:
            queryset = queryset.filter(enti_nome__icontains=term) | queryset.filter(enti_fant__icontains=term)
            
        results = []
        for entidade in queryset[:20]:
            text = f"{entidade.enti_nome}"
            if entidade.enti_fant:
                text += f" ({entidade.enti_fant})"
            results.append({
                'id': entidade.enti_clie,
                'text': text
            })
            
        return JsonResponse({'results': results})

class FazendaAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        print(db_name)
        
        queryset = Fazenda.objects.using(db_name).all()
        print(queryset)
        
        # Filter by tenant/empresa/filial
        empresa = getattr(request.user, 'empresa', None) or request.session.get('empresa_id', 1)
        filial = getattr(request.user, 'filial', None) or request.session.get('filial_id', 1)
        
        if empresa:
             queryset = queryset.filter(faze_empr=empresa)
        if filial:
             queryset = queryset.filter(faze_fili=filial)

        if pk:
            queryset = queryset.filter(id=pk)
        elif term:
            queryset = queryset.filter(faze_nome__icontains=term)
            
        results = []
        for fazenda in queryset[:20]:
            results.append({
                'id': fazenda.id,
                'text': fazenda.faze_nome
            })
            print(fazenda.faze_nome)
            
        return JsonResponse({'results': results})


class TalhaoAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        
        queryset = Talhao.objects.using(db_name).all()
        
        # Filter by tenant/empresa/filial
        empresa = getattr(request.user, 'empresa', None)
        if hasattr(empresa, 'pk'):
            empresa = empresa.pk
        empresa = empresa or request.session.get('empresa_id', 1)

        filial = getattr(request.user, 'filial', None)
        if hasattr(filial, 'pk'):
            filial = filial.pk
        filial = filial or request.session.get('filial_id', 1)
        
        if empresa:
             queryset = queryset.filter(talh_empr=empresa)
        if filial:
             queryset = queryset.filter(talh_fili=filial)

        if pk:
            queryset = queryset.filter(id=pk)
        elif term:
            queryset = queryset.filter(talh_nome__icontains=term)
        result = []
        for talhao in queryset[:20]:
            result.append({
                'id': talhao.id,
                'text': talhao.talh_nome
            })
            

        return JsonResponse({'results': result})


class CategoriaProdutoAutocomplete(View):
     def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        
        queryset = CategoriaProduto.objects.using(db_name).all()
        

        if pk:
            queryset = queryset.filter(id=pk)
        elif term:
            queryset = queryset.filter(cate_nome__icontains=term)
        result = []
        for categoria in queryset[:20]:
            result.append({
                'id': categoria.id,
                'text': categoria.cate_nome
            })
            

        return JsonResponse({'results': result})


class ProdutoAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        queryset = ProdutoAgro.objects.using(db_name).all()
        
        # Filter by tenant/empresa/filial
        empresa = getattr(request.user, 'empresa', None)
        if hasattr(empresa, 'pk'):
            empresa = empresa.pk
        empresa = empresa or request.session.get('empresa_id', 1)

        filial = getattr(request.user, 'filial', None)
        if hasattr(filial, 'pk'):
            filial = filial.pk
        filial = filial or request.session.get('filial_id', 1)
        
        if empresa:
             queryset = queryset.filter(prod_empr_agro=empresa)
        if filial:
             queryset = queryset.filter(prod_fili_agro=filial)

        if pk:
            queryset = queryset.filter(id=pk)
        elif term:
            queryset = queryset.filter(prod_nome_agro__icontains=term)
        result = []
        for produto in queryset[:20]:
            result.append({
                'id': produto.id,
                'text': produto.prod_nome_agro
            })
            

        return JsonResponse({'results': result})


class AnimalAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        term = request.GET.get('term', '').strip()
        pk = request.GET.get('id', '').strip()
        db_name = get_licenca_db_config(request) or 'default'
        
        queryset = Animal.objects.using(db_name).all()

        # Filter by tenant/empresa/filial
        empresa = getattr(request.user, 'empresa', None)
        if hasattr(empresa, 'pk'):
            empresa = empresa.pk
        empresa = empresa or request.session.get('empresa_id', 1)

        filial = getattr(request.user, 'filial', None)
        if hasattr(filial, 'pk'):
            filial = filial.pk
        filial = filial or request.session.get('filial_id', 1)
        
        if empresa:
             queryset = queryset.filter(anim_empr=empresa)
        if filial:
             queryset = queryset.filter(anim_fili=filial)
        

        if pk:
            queryset = queryset.filter(id=pk)
        elif term:
            queryset = queryset.filter(anim_ident__icontains=term)
        result = []
        for animal in queryset[:20]:
            result.append({
                'id': animal.id,
                'text': animal.anim_ident
            })
            

        return JsonResponse({'results': result})
