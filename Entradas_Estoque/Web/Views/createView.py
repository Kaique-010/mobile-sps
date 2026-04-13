from django.views.generic import CreateView
import json
from django.views import View
from django.http import JsonResponse
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef, BigIntegerField
from django.db.models.functions import Cast
from django.shortcuts import redirect
from ...models import EntradaEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ..forms import EntradaEstoqueForm
import logging
logger = logging.getLogger(__name__)



class EntradaCreateView(CreateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entradas_criar.html'


    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/entradas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        """Passa parâmetros extras para o form"""
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        
        # Produtos para o template (usado no JavaScript para adicionar linhas)
        try:
            from Produtos.models import Produtos
            qs = Produtos.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(prod_empr=str(empresa_id))
            context['produtos'] = qs.order_by('prod_nome')[:500]
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
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
            from Produtos.models import Lote, Tabelaprecos
            import re
            obj = form.save(commit=False)
            obj.entr_empr = empresa_id
            obj.entr_fili = filial_id
            auto_lote = bool(form.cleaned_data.get('auto_lote'))
            atualizar_preco = bool(form.cleaned_data.get('atualizar_preco'))
            lote_informado = form.cleaned_data.get('entr_lote_vend')
            lote_texto = (form.data.get('entr_lote_vend') or '').strip()
            lote_label = None
            if lote_texto and not lote_texto.isdigit():
                lote_label = lote_texto
            obj.entr_lote_vend = lote_informado or None
            max_sequ = EntradaEstoque.objects.using(banco).aggregate(
                models.Max('entr_sequ')
            )['entr_sequ__max'] or 0
            obj.entr_sequ = (max_sequ + 1)
            with transaction.atomic(using=banco):
                obj.save(using=banco)
                lote_num = obj.entr_lote_vend
                if not lote_num and lote_texto and not re.search(r'\d', lote_texto):
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(obj.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    lote_num = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=obj.pk).update(entr_lote_vend=int(lote_num))
                    obj.entr_lote_vend = int(lote_num)
                elif auto_lote and not lote_num:
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(obj.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    lote_num = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=obj.pk).update(entr_lote_vend=int(lote_num))
                    obj.entr_lote_vend = int(lote_num)
                if lote_num:
                    codigo = str(obj.entr_prod)
                    lote_data_fabr = form.cleaned_data.get('lote_data_fabr') or obj.entr_data
                    lote_data_vali = form.cleaned_data.get('lote_data_vali')
                    lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=codigo, lote_lote=int(lote_num))
                        .first()
                    )
                    if not lote:
                        lote = Lote(
                            lote_empr=int(empresa_id),
                            lote_prod=codigo,
                            lote_lote=int(lote_num),
                            lote_unit=Decimal(str(obj.entr_unit or 0)),
                            lote_sald=Decimal('0.00'),
                            lote_data_fabr=lote_data_fabr,
                            lote_data_vali=lote_data_vali,
                            lote_ativ=True,
                            lote_obse=lote_label,
                        )
                    elif lote_label and not getattr(lote, 'lote_obse', None):
                        lote.lote_obse = lote_label
                    if lote_data_fabr is not None:
                        lote.lote_data_fabr = lote_data_fabr
                    if lote_data_vali is not None:
                        lote.lote_data_vali = lote_data_vali
                    saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                    qtd = Decimal(str(obj.entr_quan or 0))
                    lote.lote_sald = (saldo_atual + qtd).quantize(Decimal('0.01'))
                    lote.save(using=banco)

                if atualizar_preco:
                    preco_vista = form.cleaned_data.get('preco_vista')
                    preco_prazo = form.cleaned_data.get('preco_prazo')
                    update_fields = {
                        'tabe_cuge': Decimal(str(obj.entr_unit or 0)).quantize(Decimal('0.01')),
                        'tabe_entr': obj.entr_data,
                    }
                    if preco_vista is not None:
                        update_fields['tabe_avis'] = Decimal(str(preco_vista)).quantize(Decimal('0.01'))
                    if preco_prazo is not None:
                        update_fields['tabe_apra'] = Decimal(str(preco_prazo)).quantize(Decimal('0.01'))
                    qs = Tabelaprecos.objects.using(banco).filter(
                        tabe_empr=int(empresa_id),
                        tabe_fili=int(filial_id),
                        tabe_prod=str(obj.entr_prod),
                    )
                    updated = qs.update(**update_fields)
                    if not updated:
                        create_fields = {
                            'tabe_empr': int(empresa_id),
                            'tabe_fili': int(filial_id),
                            'tabe_prod': str(obj.entr_prod),
                            **update_fields,
                        }
                        Tabelaprecos.objects.using(banco).create(**create_fields)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao salvar entrada: {e}")
            return self.form_invalid(form)


class EntradaLoteView(View):

    def post(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or 'default'
        empresa_id = request.session.get('empresa_id', 1)
        filial_id = request.session.get('filial_id', 1)

        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON inválido'}, status=400)

        itens = payload.get('itens', [])
        entidade = payload.get('entidade')
        data_mov = payload.get('data')
        auto_lote = bool(payload.get('auto_lote'))
        atualizar_preco = bool(payload.get('atualizar_preco', True))

        if not entidade or not data_mov:
            return JsonResponse({'erro': 'Entidade e data são obrigatórias'}, status=400)

        if not isinstance(itens, list) or not itens:
            return JsonResponse({'erro': 'Informe pelo menos um item'}, status=400)

        from django.db import models
        import re

        def parse_lote(value):
            if value is None:
                return (None, None, '')
            s = str(value).strip()
            if not s:
                return (None, None, '')
            label = s if not s.isdigit() else None
            parts = re.findall(r'(\d+)', s)
            num = int(parts[-1]) if parts else None
            return (num, label, s)

        def parse_money(value):
            if value is None:
                return None
            s = str(value).strip()
            if not s:
                return None
            try:
                return float(s.replace(',', '.'))
            except Exception:
                return None

        try:
            with transaction.atomic(using=banco):

                max_sequ = EntradaEstoque.objects.using(banco).aggregate(
                    models.Max('entr_sequ')
                )['entr_sequ__max'] or 0

                objs = []
                lote_labels = []
                preco_vistas = []
                preco_prazos = []
                lote_fabrs = []
                lote_valis = []
                next_lote_by_prod = {}
                tem_lote = False
                sem_lote = False

                def parse_date(v):
                    if not v:
                        return None
                    if hasattr(v, 'year'):
                        return v
                    try:
                        from datetime import date
                        return date.fromisoformat(str(v))
                    except Exception:
                        return None

                def get_next_lote(produto_codigo: str) -> int:
                    from Produtos.models import Lote
                    key = str(produto_codigo)
                    if key in next_lote_by_prod:
                        val = next_lote_by_prod[key]
                        next_lote_by_prod[key] = val + 1
                        return val
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=key)
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    val = int(ultimo) + 1
                    next_lote_by_prod[key] = val + 1
                    return val

                for i, item in enumerate(itens):
                    produto = item.get('produto')
                    if not produto or str(produto).strip().lower() == 'undefined':
                        texto = (item.get('produto_text') or '').strip()
                        if texto and ' - ' in texto:
                            produto = texto.split(' - ', 1)[0].strip()
                    if not produto:
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
                    lote_num, lote_label, lote_texto = parse_lote(item.get('lote'))
                    if not lote_num and lote_texto:
                        lote_num = get_next_lote(str(produto))
                        lote_label = lote_texto
                    elif auto_lote and not lote_num:
                        lote_num = get_next_lote(str(produto))
                    if lote_num:
                        tem_lote = True
                    else:
                        sem_lote = True
                    lote_data_fabr = parse_date(item.get('lote_data_fabr'))
                    if lote_data_fabr is None:
                        lote_data_fabr = parse_date(data_mov)
                    lote_data_vali = parse_date(item.get('lote_data_vali'))
                    objs.append(
                        EntradaEstoque(
                            entr_empr=empresa_id,
                            entr_fili=filial_id,
                            entr_enti=entidade,
                            entr_prod=produto,
                            entr_quan=qtd,
                            entr_unit=unit,
                            entr_tota=total,
                            entr_data=data_mov,
                            entr_sequ=max_sequ + i + 1,
                            entr_lote_vend=lote_num,
                        )
                    )
                    lote_labels.append(lote_label)
                    preco_vistas.append(parse_money(item.get('preco_vista')))
                    preco_prazos.append(parse_money(item.get('preco_prazo')))
                    lote_fabrs.append(lote_data_fabr)
                    lote_valis.append(lote_data_vali)

                if tem_lote and sem_lote:
                    raise ValueError('Não é permitido misturar itens com lote e sem lote na mesma entrada')

                from Produtos.models import Lote
                from decimal import Decimal
                from Produtos.models import Tabelaprecos
                EntradaEstoque.objects.using(banco).bulk_create(objs)
                for o, lote_label, preco_vista, preco_prazo, lote_data_fabr, lote_data_vali in zip(objs, lote_labels, preco_vistas, preco_prazos, lote_fabrs, lote_valis):
                    lote_num = o.entr_lote_vend
                    if lote_num:
                        codigo = str(o.entr_prod)
                        lote = (
                            Lote.objects.using(banco)
                            .filter(lote_empr=int(empresa_id), lote_prod=codigo, lote_lote=int(lote_num))
                            .first()
                        )
                        if not lote:
                            lote = Lote(
                                lote_empr=int(empresa_id),
                                lote_prod=codigo,
                                lote_lote=int(lote_num),
                                lote_unit=Decimal(str(o.entr_unit or 0)),
                                lote_sald=Decimal('0.00'),
                                lote_data_fabr=lote_data_fabr,
                                lote_data_vali=lote_data_vali,
                                lote_ativ=True,
                                lote_obse=lote_label,
                            )
                        elif lote_label and not getattr(lote, 'lote_obse', None):
                            lote.lote_obse = lote_label
                        if lote_data_fabr is not None:
                            lote.lote_data_fabr = lote_data_fabr
                        if lote_data_vali is not None:
                            lote.lote_data_vali = lote_data_vali
                        saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                        qtd = Decimal(str(o.entr_quan or 0))
                        lote.lote_sald = (saldo_atual + qtd).quantize(Decimal('0.01'))
                        lote.save(using=banco)

                    if atualizar_preco:
                        update_fields = {
                            'tabe_cuge': Decimal(str(o.entr_unit or 0)).quantize(Decimal('0.01')),
                            'tabe_entr': data_mov,
                        }
                        if preco_vista is not None:
                            update_fields['tabe_avis'] = Decimal(str(preco_vista)).quantize(Decimal('0.01'))
                        if preco_prazo is not None:
                            update_fields['tabe_apra'] = Decimal(str(preco_prazo)).quantize(Decimal('0.01'))
                        qs = Tabelaprecos.objects.using(banco).filter(
                            tabe_empr=int(empresa_id),
                            tabe_fili=int(filial_id),
                            tabe_prod=str(o.entr_prod),
                        )
                        updated = qs.update(**update_fields)
                        if not updated:
                            create_fields = {
                                'tabe_empr': int(empresa_id),
                                'tabe_fili': int(filial_id),
                                'tabe_prod': str(o.entr_prod),
                                **update_fields,
                            }
                            Tabelaprecos.objects.using(banco).create(**create_fields)

            return JsonResponse({'ok': True})

        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=400)
