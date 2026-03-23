from django.views.generic import CreateView
import json
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import redirect
from Saidas_Estoque.models import SaidasEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ..forms import SaidasEstoqueForm
import logging
logger = logging.getLogger(__name__)


class SaidaCreateView(CreateView):
    model = SaidasEstoque
    form_class = SaidasEstoqueForm
    template_name = 'Saidas/saidas_criar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/saidas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception as e:
            logger.error(f"Erro ao carregar produtos: {e}")
            context['produtos'] = []
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context

    def form_valid(self, form):
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        banco = get_licenca_db_config(self.request) or 'default'
        try:
            from django.db import models
            from decimal import Decimal
            from Produtos.models import Lote
            obj = form.save(commit=False)
            unit = form.cleaned_data.get('valor_unitario')
            if unit is not None and obj.said_quan is not None:
                obj.said_tota = obj.said_quan * unit
            obj.said_empr = empresa_id
            obj.said_fili = filial_id
            obj.said_lote_vend = form.cleaned_data.get('said_lote_vend') or None
            max_sequ = SaidasEstoque.objects.using(banco).aggregate(
                models.Max('said_sequ')
            )['said_sequ__max'] or 0
            obj.said_sequ = (max_sequ + 1)
            with transaction.atomic(using=banco):
                obj.save(using=banco)
                lote_num = obj.said_lote_vend
                if lote_num:
                    codigo = str(obj.said_prod)
                    lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=codigo, lote_lote=int(lote_num))
                        .first()
                    )
                    if not lote:
                        raise ValueError("Lote informado não existe para o produto selecionado")
                    saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                    qtd = Decimal(str(obj.said_quan or 0))
                    lote.lote_sald = (saldo_atual - abs(qtd)).quantize(Decimal('0.01'))
                    if form.cleaned_data.get('lote_data_fabr'):
                        lote.lote_data_fabr = form.cleaned_data.get('lote_data_fabr')
                    if form.cleaned_data.get('lote_data_vali'):
                        lote.lote_data_vali = form.cleaned_data.get('lote_data_vali')
                    lote.save(using=banco)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao salvar saída: {e}")
            return self.form_invalid(form)


class SaidaLoteView(View):

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or 'default'
        empresa_id = request.session.get('empresa_id', 1)
        filial_id = request.session.get('filial_id', 1)
        usuario_id = request.session.get('usua_codi', 0) or 0

        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON inválido'}, status=400)

        itens = payload.get('itens', [])
        entidade = payload.get('entidade')
        data_mov = payload.get('data')

        if not data_mov:
            return JsonResponse({'erro': 'Data é obrigatória'}, status=400)

        if not isinstance(itens, list) or not itens:
            return JsonResponse({'erro': 'Informe pelo menos um item'}, status=400)

        from django.db import models
        import re

        def parse_lote(value):
            if value is None:
                return None
            s = str(value).strip()
            if not s:
                return None
            if s.isdigit():
                return int(s)
            parts = re.findall(r'(\d+)', s)
            return int(parts[-1]) if parts else None

        try:
            with transaction.atomic(using=banco):
                max_sequ = SaidasEstoque.objects.using(banco).aggregate(
                    models.Max('said_sequ')
                )['said_sequ__max'] or 0

                objs = []
                for i, item in enumerate(itens):
                    if not item.get('produto'):
                        raise ValueError('Produto é obrigatório')
                    if item.get('qtd') is None or item.get('unit') is None:
                        raise ValueError('Quantidade e unitário são obrigatórios')
                    try:
                        qtd = float(str(item.get('qtd')).replace(',', '.'))
                        unit = float(str(item.get('unit')).replace(',', '.'))
                    except Exception:
                        raise ValueError('Quantidade e unitário inválidos')
                    if qtd <= 0 or unit <= 0:
                        raise ValueError('Quantidade e unitário devem ser maiores que zero')
                    total_raw = item.get('total', None)
                    if total_raw is None:
                        total = qtd * unit
                    else:
                        try:
                            total = float(str(total_raw).replace(',', '.'))
                        except Exception:
                            total = qtd * unit
                    lote_num = parse_lote(item.get('lote'))
                    if item.get('lote') and not lote_num:
                        raise ValueError('Lote inválido. Informe um lote com número (ex: 123 ou LOTE-123).')
                    objs.append(
                        SaidasEstoque(
                            said_empr=empresa_id,
                            said_fili=filial_id,
                            said_enti=entidade,
                            said_prod=item.get('produto'),
                            said_quan=qtd,
                            said_tota=total,
                            said_data=data_mov,
                            said_sequ=max_sequ + i + 1,
                            said_usua=usuario_id,
                            said_lote_vend=lote_num,
                        )
                    )

                from Produtos.models import Lote
                from decimal import Decimal
                SaidasEstoque.objects.using(banco).bulk_create(objs)
                for o, it in zip(objs, itens):
                    lote_num = parse_lote(it.get('lote'))
                    if not lote_num:
                        continue
                    codigo = str(o.said_prod)
                    lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=codigo, lote_lote=int(lote_num))
                        .first()
                    )
                    if not lote:
                        raise ValueError("Lote informado não existe para o produto selecionado")
                    saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                    qtd = Decimal(str(o.said_quan or 0))
                    lote.lote_sald = (saldo_atual - abs(qtd)).quantize(Decimal('0.01'))
                    lote.save(using=banco)

            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=400)
