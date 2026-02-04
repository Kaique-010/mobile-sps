from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Q, Subquery, OuterRef, DecimalField, Value as V, CharField, IntegerField, Case, When
from django.db.models.functions import Coalesce, Cast
from Produtos.models import Produtos, SaldoProduto, Tabelaprecos
from Produtos.utils import formatar_dados_etiqueta
from core.registry import get_licenca_db_config
from core.decorator import ModuloRequeridoMixin

class EtiquetasView(ModuloRequeridoMixin, TemplateView):
    template_name = "Produtos/etiquetas_print.html"
    modulo_necessario = 'Produtos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        banco = get_licenca_db_config(request)
        
        if not banco:
            return context

        # 1. Lógica de Busca de Produtos (para seleção)
        q = request.GET.get('q', '').strip()
        if q:
            # Subqueries otimizadas (reutilizando lógica da API)
            saldo_subquery = Subquery(
                SaldoProduto.objects.using(banco).filter(
                    produto_codigo=OuterRef('pk')
                ).values('saldo_estoque')[:1],
                output_field=DecimalField()
            )

            # Preço à vista (opcional para visualização na tabela de seleção)
            preco_vista_subquery = Subquery(
                Tabelaprecos.objects.using(banco).filter(
                    tabe_prod=OuterRef('prod_codi'),
                    tabe_empr=OuterRef('prod_empr')
                ).exclude(
                    tabe_entr__year__lt=1900
                ).exclude(
                    tabe_entr__year__gt=2100
                ).values('tabe_avis')[:1],
                output_field=DecimalField()
            )
            
            produtos_busca = Produtos.objects.using(banco).annotate(
                saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
                prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
                prod_coba_str=Coalesce(Cast('prod_coba', CharField()), V('')),
                prod_codi_int=Case(
                    When(prod_codi__regex=r'^\d+$', then=Cast('prod_codi', IntegerField())),
                    default=V(None),
                    output_field=IntegerField()
                )
            ).filter(
                Q(prod_nome__icontains=q) |
                Q(prod_coba_str__exact=q) |
                Q(prod_codi__exact=q.lstrip("0"))
            ).order_by('prod_empr', 'prod_codi_int')[:50]

            context['produtos_busca'] = produtos_busca
            context['termo_busca'] = q

        # 2. Lógica de Impressão (Processar IDs selecionados)
        # Tenta pegar IDs do GET (link direto) ou do contexto se vier de um POST anterior (embora POST renderize direto, manter consistência)
        ids = request.GET.get('ids')
        if ids:
            lista_ids = [i.strip() for i in ids.split(',') if i.strip()]
            produtos_imprimir = Produtos.objects.using(banco).filter(
                prod_codi__in=lista_ids
            ).select_related('prod_marc')
            
            etiquetas = [formatar_dados_etiqueta(p) for p in produtos_imprimir]
            context['etiquetas'] = etiquetas
            
        return context

    def post(self, request, *args, **kwargs):
        # Quando o formulário de seleção é submetido
        context = self.get_context_data(**kwargs)
        produtos_ids = request.POST.getlist('produtos_selecionados')
        
        # Fallback para input de texto separado por vírgula se houver
        if not produtos_ids and request.POST.get('produtos_ids_manual'):
             produtos_ids = request.POST.get('produtos_ids_manual').split(',')
             
        if produtos_ids:
            banco = get_licenca_db_config(request)
            if banco:
                produtos = Produtos.objects.using(banco).filter(
                    prod_codi__in=produtos_ids
                ).select_related('prod_marc')
                
                etiquetas = []
                for p in produtos:
                    try:
                        qtd = int(request.POST.get(f'qtd_{p.prod_codi}', 1))
                        if qtd < 1: qtd = 1
                    except (ValueError, TypeError):
                        qtd = 1
                    
                    dados = formatar_dados_etiqueta(p)
                    for _ in range(qtd):
                        etiquetas.append(dados)

                context['etiquetas'] = etiquetas
        
        # Se foi uma submissão de busca via POST (opcional, mas comum em forms)
        if 'q' in request.POST:
            # Redirecionar para GET ou processar aqui mesmo. 
            # Para simplificar, vamos processar a busca no POST também se necessário, 
            # mas idealmente busca é GET.
            pass
            
        return render(request, self.template_name, context)
