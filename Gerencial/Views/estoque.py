from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from datetime import datetime
from django.db.models import Sum
from Entradas_Estoque.models import EntradaEstoque
from Saidas_Estoque.models import SaidasEstoque
from Produtos.models import SaldoProduto, Produtos

class ExtratoMovimentacaoProdutosView(ModuloRequeridoMixin, APIView):
    permission_classes = [IsAuthenticated]
    modulo_requerido = 'Produtos'

    @modulo_necessario('Produtos')
    def get(self, request, *args, **kwargs):
        empresa = request.GET.get('empr') or request.META.get('HTTP_X_EMPRESA')
        filial = request.GET.get('fili') or request.META.get('HTTP_X_FILIAL')
        data_ini = request.GET.get('data_ini')
        data_fim = request.GET.get('data_fim')
        produto = request.GET.get('prod')

        if not all([empresa, filial, data_ini, data_fim]):
            return Response({"erro": "Parâmetros obrigatórios faltando"}, status=400)

        try:
            di = datetime.strptime(data_ini, '%Y-%m-%d').date()
            df = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except Exception:
            return Response({"erro": "Datas inválidas"}, status=400)

        entradas_qs = EntradaEstoque.objects.filter(entr_empr=empresa, entr_fili=filial, entr_data__range=(di, df))
        saidas_qs = SaidasEstoque.objects.filter(said_empr=empresa, said_fili=filial, said_data__range=(di, df))
        if produto:
            entradas_qs = entradas_qs.filter(entr_prod=produto)
            saidas_qs = saidas_qs.filter(said_prod=produto)

        total_entr_quan = sum(float(e.entr_quan) for e in entradas_qs)
        total_entr_valo = sum(float(e.entr_tota) for e in entradas_qs)
        total_said_quan = sum(float(s.said_quan) for s in saidas_qs)
        total_said_valo = sum(float(s.said_tota) for s in saidas_qs)

        series_entr = {}
        for e in entradas_qs:
            k = e.entr_data.strftime('%Y-%m-%d')
            v = series_entr.get(k, {"quantidade": 0.0, "valor": 0.0})
            v["quantidade"] += float(e.entr_quan)
            v["valor"] += float(e.entr_tota)
            series_entr[k] = v

        series_said = {}
        for s in saidas_qs:
            k = s.said_data.strftime('%Y-%m-%d')
            v = series_said.get(k, {"quantidade": 0.0, "valor": 0.0})
            v["quantidade"] += float(s.said_quan)
            v["valor"] += float(s.said_tota)
            series_said[k] = v

        extrato_list = None
        ent_agg = list(entradas_qs.order_by().values('entr_prod').annotate(q=Sum('entr_quan'), v=Sum('entr_tota')))
        sai_agg = list(saidas_qs.order_by().values('said_prod').annotate(q=Sum('said_quan'), v=Sum('said_tota')))
        ent_map = {e['entr_prod']: {'q': float(e['q'] or 0), 'v': float(e['v'] or 0)} for e in ent_agg}
        sai_map = {s['said_prod']: {'q': float(s['q'] or 0), 'v': float(s['v'] or 0)} for s in sai_agg}
        codes = sorted(set(list(ent_map.keys()) + list(sai_map.keys())))
        prod_info_map = {}
        if codes:
            for p in Produtos.objects.filter(prod_codi__in=codes, prod_empr=str(empresa)):
                prod_info_map[p.prod_codi] = { 'nome': p.prod_nome, 'unidade': str(p.prod_unme) }
            saldo_map = {}
            for sp in SaldoProduto.objects.filter(produto_codigo__prod_codi__in=codes, empresa=str(empresa), filial=str(filial)):
                saldo_map[sp.produto_codigo.prod_codi] = float(sp.saldo_estoque or 0)
            extrato_list = []
            for c in codes:
                e = ent_map.get(c, {'q':0.0,'v':0.0})
                s = sai_map.get(c, {'q':0.0,'v':0.0})
                info = prod_info_map.get(c, {})
                saldo_periodo = e['q'] - s['q']
                extrato_list.append({
                    'codigo': c,
                    'nome': info.get('nome'),
                    'unidade': info.get('unidade'),
                    'entradas_quantidade': e['q'],
                    'entradas_valor': e['v'],
                    'saidas_quantidade': s['q'],
                    'saidas_valor': s['v'],
                    'saldo_periodo': saldo_periodo,
                    'saldo_atual': saldo_map.get(c),
                })

        saldo_val = None
        produto_nome = None
        unidade_desc = None
        if produto:
            try:
                sp = SaldoProduto.objects.filter(produto_codigo__prod_codi=produto, empresa=str(empresa), filial=str(filial)).first()
                saldo_val = float(sp.saldo_estoque) if sp and sp.saldo_estoque is not None else None
            except Exception:
                saldo_val = None
            try:
                prod_obj = Produtos.objects.filter(prod_codi=produto, prod_empr=str(empresa)).first()
                if prod_obj:
                    produto_nome = prod_obj.prod_nome
                    unidade_desc = str(prod_obj.prod_unme)
            except Exception:
                pass

        resp = {
            "produto": produto or None,
            "empresa": empresa,
            "filial": filial,
            "kpis": {
                "entradas_quantidade": total_entr_quan,
                "entradas_valor": total_entr_valo,
                "saidas_quantidade": total_said_quan,
                "saidas_valor": total_said_valo,
                "saldo_estoque": saldo_val,
            },
            "produto_info": {
                "codigo": produto or None,
                "nome": produto_nome,
                "unidade": unidade_desc,
            },
            "series": {
                "entradas_diarias": [{"data": k, "quantidade": v["quantidade"], "valor": v["valor"]} for k, v in sorted(series_entr.items())],
                "saidas_diarias": [{"data": k, "quantidade": v["quantidade"], "valor": v["valor"]} for k, v in sorted(series_said.items())],
            },
            "extrato": extrato_list,
        }
        return Response(resp)