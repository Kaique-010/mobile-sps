from django.views.generic import ListView, DetailView
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from Licencas.models import Filiais
from .models import NotaFiscalEntrada
from django.db.models import Q
from .forms import NotaManualForm
from .services.entrada_nfe_manual_service import EntradaNFeManualService
from django.views.generic.edit import FormView
from django.http import JsonResponse
from django.urls import reverse_lazy
import json
from decimal import Decimal
from datetime import datetime

class NotasDestinadasListView(ListView):
    model = NotaFiscalEntrada
    template_name = 'NotasDestinadas/destinadas_lista.html'
    context_object_name = 'notas'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        
        # Recupera empresa e filial da sessão com fallbacks para garantir integridade
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        
        try:
            if self.empresa_id: self.empresa_id = int(self.empresa_id)
            if self.filial_id: self.filial_id = int(self.filial_id)
        except (ValueError, TypeError):
            self.empresa_id = None
            self.filial_id = None
            
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

class NotasManuaisListView(NotasDestinadasListView):
    template_name = 'NotasDestinadas/manuais_lista.html'

    def get_queryset(self):
        # Override to filter only manual notes (no XML)
        qs = NotaFiscalEntrada.objects.using(self.db_alias).filter(
            empresa=self.empresa_id,
            filial=self.filial_id
        ).filter(Q(xml_nfe__isnull=True) | Q(xml_nfe=''))
        
        return qs.order_by('-data_emissao', '-numero_nota_fiscal')

class NotaManualDetailView(DetailView):
    model = NotaFiscalEntrada
    template_name = 'NotasDestinadas/nota_manual_detail.html'
    context_object_name = 'nota'
    pk_url_kwarg = 'nota_id'
    
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        
        try:
            if self.empresa_id: self.empresa_id = int(self.empresa_id)
            if self.filial_id: self.filial_id = int(self.filial_id)
        except (ValueError, TypeError):
            self.empresa_id = None
            self.filial_id = None
            
        return super().dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        return NotaFiscalEntrada.objects.using(self.db_alias).filter(
            empresa=self.empresa_id,
            filial=self.filial_id
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nota = self.object
        
        # Busca itens
        try:
            from Entradas_Estoque.models import EntradaEstoque
            from Produtos.models import Produtos
            from Entidades.models import Entidades

            # Fallback para cliente se não estiver salvo na nota
            cliente_id = nota.cliente
            if not cliente_id and nota.emitente_cnpj:
                try:
                    entidade = Entidades.objects.using(self.db_alias).filter(
                        enti_cnpj=nota.emitente_cnpj,
                        enti_empr=nota.empresa
                    ).first()
                    if entidade:
                        cliente_id = entidade.enti_clie
                except Exception as e:
                    print(f"Erro ao buscar entidade fallback detail view: {e}")
            
            if cliente_id:
                try:
                    num_nota_int = int(nota.numero_nota_fiscal)
                except:
                    num_nota_int = nota.numero_nota_fiscal
                
                itens_estoque = EntradaEstoque.objects.using(self.db_alias).filter(
                    entr_empr=nota.empresa,
                    entr_fili=nota.filial,
                    entr_enti=str(cliente_id),
                    entr_obse__icontains=f"NF Manual {num_nota_int}"
                )
            else:
                itens_estoque = []
            
            itens_formatados = []
            for item in itens_estoque:
                # Busca dados do produto
                produto = Produtos.objects.using(self.db_alias).filter(
                    prod_codi=item.entr_prod,
                    prod_empr=nota.empresa
                ).first()
                
                itens_formatados.append({
                    'cprod': item.entr_prod,
                    'xprod': produto.prod_nome if produto else 'Produto não encontrado',
                    'ucom': produto.prod_unme_id if produto else '-',
                    'qcom': item.entr_quan,
                    'vuncom': float(item.entr_tota) / float(item.entr_quan) if item.entr_quan else 0,
                    'vprod': item.entr_tota,
                    'cfop': '-'
                })
            
            context['itens'] = itens_formatados
        except Exception as e:
            print(f"Erro ao buscar itens na detail view: {e}")
            context['itens'] = []
            
        # Busca parcelas
        try:
            from contas_a_pagar.models import Titulospagar
            from Entidades.models import Entidades

            # Fallback para cliente se não estiver salvo na nota (reutiliza lógica anterior ou busca novamente)
            if 'cliente_id' not in locals():
                cliente_id = nota.cliente
                if not cliente_id and nota.emitente_cnpj:
                     try:
                        entidade = Entidades.objects.using(self.db_alias).filter(
                            enti_cnpj=nota.emitente_cnpj,
                            enti_empr=nota.empresa
                        ).first()
                        if entidade:
                            cliente_id = entidade.enti_clie
                     except:
                        pass
            
            if cliente_id:
                context['parcelas'] = Titulospagar.objects.using(self.db_alias).filter(
                    titu_empr=nota.empresa,
                    titu_fili=nota.filial,
                    titu_forn=cliente_id,
                    titu_titu=str(nota.numero_nota_fiscal),
                    titu_tipo='Entrada'
                ).order_by('titu_parc')
            else:
                context['parcelas'] = []
        except Exception as e:
             print(f"Erro ao buscar parcelas na detail view: {e}")
             context['parcelas'] = []
             
        return context

class NotaManualCreateView(FormView):
    template_name = 'NotasDestinadas/nota_manual_form.html'
    form_class = NotaManualForm
    
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug') or get_licenca_slug()
        self.db_alias = get_licenca_db_config(request)
        self.nota_id = kwargs.get('nota_id')
        
        # Recupera empresa e filial da sessão com fallbacks para garantir integridade
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial')
        
        try:
            if self.empresa_id: self.empresa_id = int(self.empresa_id)
            if self.filial_id: self.filial_id = int(self.filial_id)
        except (ValueError, TypeError):
            self.empresa_id = None
            self.filial_id = None
            
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = int(self.empresa_id) if self.empresa_id else None
        kwargs['using_db'] = self.db_alias
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.nota_id:
            try:
                # Tenta buscar a nota
                print(f"Carregando nota {self.nota_id} para edição. Empresa: {self.empresa_id}, Filial: {self.filial_id}")
                nota = NotaFiscalEntrada.objects.using(self.db_alias).get(
                    pk=self.nota_id
                )
                
                # Valida permissão (opcional, mas bom para debug)
                if self.empresa_id and nota.empresa != self.empresa_id:
                    print(f"Aviso: Nota pertence a empresa {nota.empresa}, sessão é {self.empresa_id}")
                
                # Fallback para cliente se não estiver salvo na nota
                cliente_id = nota.cliente
                if not cliente_id and nota.emitente_cnpj:
                    try:
                        from Entidades.models import Entidades
                        entidade = Entidades.objects.using(self.db_alias).filter(
                            enti_cnpj=nota.emitente_cnpj,
                            enti_empr=nota.empresa
                        ).first()
                        if entidade:
                            cliente_id = entidade.enti_clie
                    except Exception as e:
                        print(f"Erro ao buscar entidade fallback no initial: {e}")

                initial.update({
                    'fornecedor': cliente_id,
                    'numero': nota.numero_nota_fiscal,
                    'serie': nota.serie,
                    'data_emissao': nota.data_emissao.strftime('%Y-%m-%d') if nota.data_emissao else None,
                        'data_entrada': nota.data_saida_entrada.strftime('%Y-%m-%d') if nota.data_saida_entrada else None,
                        'valor_total': nota.valor_total_nota
                })
            except Exception as e:
                print(f"Erro ao carregar initial data: {e}")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from Produtos.models import Produtos
        # Limit to 500 products for performance, ideally use AJAX search
        try:
            context['produtos_list'] = list(Produtos.objects.using(self.db_alias).filter(prod_empr=self.empresa_id).values('prod_codi', 'prod_nome', 'prod_unme__unid_desc')[:500])
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            context['produtos_list'] = []
        
        if self.nota_id:
            try:
                nota = NotaFiscalEntrada.objects.using(self.db_alias).get(
                    pk=self.nota_id
                )
                
                context['nota_existente'] = nota
                
                # Busca itens de EntradaEstoque
                from Entradas_Estoque.models import EntradaEstoque
                from Produtos.models import Produtos
                from Entidades.models import Entidades

                # Fallback para cliente se não estiver salvo na nota
                cliente_id = nota.cliente
                if not cliente_id and nota.emitente_cnpj:
                    try:
                        entidade = Entidades.objects.using(self.db_alias).filter(
                            enti_cnpj=nota.emitente_cnpj,
                            enti_empr=nota.empresa
                        ).first()
                        if entidade:
                            cliente_id = entidade.enti_clie
                    except Exception as e:
                        print(f"Erro ao buscar entidade fallback: {e}")

                # Busca flexível por observação
                if cliente_id:
                    try:
                        num_nota_int = int(nota.numero_nota_fiscal)
                    except:
                        num_nota_int = nota.numero_nota_fiscal

                    itens_estoque = EntradaEstoque.objects.using(self.db_alias).filter(
                        entr_empr=nota.empresa, # Usa da nota, não da sessão, para garantir
                        entr_fili=nota.filial,
                        entr_enti=str(cliente_id),
                        entr_obse__icontains=f"NF Manual {num_nota_int}"
                    )
                    print(f"Buscando itens estoque: Empresa={nota.empresa} Filial={nota.filial} Cliente={cliente_id} Obs='NF Manual {num_nota_int}'. Encontrados: {itens_estoque.count()}")
                else:
                    itens_estoque = []
                
                itens_existentes = []
                for item in itens_estoque:
                    produto = Produtos.objects.using(self.db_alias).filter(
                        prod_codi=item.entr_prod,
                        prod_empr=nota.empresa
                    ).first()
                    
                    itens_existentes.append({
                        'codigo': item.entr_prod,
                        'descricao': produto.prod_nome if produto else item.entr_prod,
                        'quantidade': float(item.entr_quan),
                        'valor_unitario': float(item.entr_tota) / float(item.entr_quan) if item.entr_quan else 0,
                        'valor_total': float(item.entr_tota)
                    })
                context['itens_existentes'] = json.dumps(itens_existentes)
                
                # Busca parcelas
                if cliente_id:
                    from contas_a_pagar.models import Titulospagar
                    parcelas = Titulospagar.objects.using(self.db_alias).filter(
                        titu_empr=nota.empresa,
                        titu_fili=nota.filial,
                        titu_forn=cliente_id,
                        titu_titu=str(nota.numero_nota_fiscal),
                        titu_tipo='Entrada'
                    ).values('titu_parc', 'titu_venc', 'titu_valo')
                else:
                    parcelas = []
                
                parcelas_list = []
                for p in parcelas:
                    parcelas_list.append({
                        'numero': p['titu_parc'],
                        'data_vencimento': p['titu_venc'].strftime('%Y-%m-%d') if p['titu_venc'] else '',
                        'valor': float(p['titu_valo'] or 0)
                    })
                context['parcelas_existentes'] = json.dumps(parcelas_list)
                
            except Exception as e:
                print(f"Erro ao carregar nota {self.nota_id} para contexto: {e}")
                
        return context

    def post(self, request, *args, **kwargs):
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                if not self.empresa_id or not self.filial_id:
                     return JsonResponse({'status': 'error', 'message': 'Empresa ou Filial não identificadas na sessão.'}, status=400)

                data = json.loads(request.body)
                
                # Basic validation
                if not data.get('fornecedor') or not data.get('numero'):
                     return JsonResponse({'status': 'error', 'message': 'Campos obrigatórios faltando (Fornecedor ou Número)'}, status=400)

                EntradaNFeManualService.registrar_entrada_manual(
                    empresa=int(self.empresa_id),
                    filial=int(self.filial_id),
                    fornecedor_id=int(data.get('fornecedor')),
                    numero_nota=int(data.get('numero')),
                    serie=data.get('serie'),
                    data_emissao=datetime.strptime(data.get('data_emissao'), '%Y-%m-%d').date(),
                    data_entrada=datetime.strptime(data.get('data_entrada'), '%Y-%m-%d').date(),
                    valor_total=Decimal(str(data.get('valor_total') or 0)),
                    itens=data.get('itens', []),
                    parcelas=data.get('parcelas', []),
                    usuario_id=request.user.usua_codi if request.user.is_authenticated else 0,
                    banco=self.db_alias
                )
                
                url = reverse_lazy('notas-manuais-lista', kwargs={'slug': self.slug})
                return JsonResponse({'status': 'success', 'redirect_url': str(url)})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        
        return super().post(request, *args, **kwargs)
