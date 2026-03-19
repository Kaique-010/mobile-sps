from datetime import datetime

from django.views.generic import TemplateView

from core.utils import get_licenca_db_config
from Entidades.models import Entidades

from Lancamentos_Bancarios.services import obter_resumo_dashboard




class DashboardView(TemplateView):
    template_name = 'Lancamentos_Bancarios/Dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        slug_val = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request) or 'default'

        empresa_id = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get(
            'empr'
        )
        filial_id = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get(
            'fili'
        )

        entidade_id = self.request.GET.get('enti') or self.request.GET.get('entidade')
        centro_custo_id = (
            self.request.GET.get('centro_custo')
            or self.request.GET.get('cecu')
            or self.request.GET.get('cc')
            or self.request.GET.get('centrodecusto')
        )
        data_inicial = self.request.GET.get('data_ini')
        data_final = self.request.GET.get('data_fim')
        limite = self.request.GET.get('limite') or 10

        try:
            empresa_id = int(empresa_id) if empresa_id is not None else None
        except Exception:
            empresa_id = None
        try:
            filial_id = int(filial_id) if filial_id is not None else None
        except Exception:
            filial_id = None
        try:
            entidade_id_int = int(entidade_id) if entidade_id not in (None, "") else None
        except Exception:
            entidade_id_int = None
        try:
            centro_custo_id_int = int(centro_custo_id) if centro_custo_id not in (None, "") else None
        except Exception:
            centro_custo_id_int = None

        try:
            data_inicial_dt = datetime.strptime(data_inicial, '%Y-%m-%d').date() if data_inicial else None
        except Exception:
            data_inicial_dt = None
        try:
            data_final_dt = datetime.strptime(data_final, '%Y-%m-%d').date() if data_final else None
        except Exception:
            data_final_dt = None

        try:
            limite_int = max(1, min(int(limite), 100))
        except Exception:
            limite_int = 10

        resumo = obter_resumo_dashboard(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            entidade_id=entidade_id_int,
            centro_custo_id=centro_custo_id_int,
            data_inicial=data_inicial_dt,
            data_final=data_final_dt,
            limite=limite_int,
        )

        entidade_display = ""
        if empresa_id is not None and entidade_id_int is not None:
            enti_obj = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id), enti_clie=int(entidade_id_int)).first()
            if enti_obj:
                entidade_display = f"{enti_obj.enti_clie} - {enti_obj.enti_nome}"

        centro_custo_display = ""
        if empresa_id is not None and centro_custo_id_int is not None:
            try:
                from CentrodeCustos.models import Centrodecustos
            except Exception:
                Centrodecustos = None
            if Centrodecustos:
                cc_obj = Centrodecustos.objects.using(banco).filter(
                    cecu_empr=int(empresa_id),
                    cecu_redu=int(centro_custo_id_int),
                ).first()
                if cc_obj:
                    centro_custo_display = f"{cc_obj.cecu_redu} - {cc_obj.cecu_nome}"

        if empresa_id is not None:
            entidade_ids = set()
            banco_ids = set()
            centro_custo_ids = set()
            for row in resumo.get("entradas_por_entidade", []):
                if row.get("laba_enti") not in (None, ""):
                    entidade_ids.add(int(row["laba_enti"]))
            for row in resumo.get("saidas_por_entidade", []):
                if row.get("laba_enti") not in (None, ""):
                    entidade_ids.add(int(row["laba_enti"]))
            for row in resumo.get("saldo_por_entidade", []):
                if row.get("laba_enti") not in (None, ""):
                    entidade_ids.add(int(row["laba_enti"]))

            for row in resumo.get("entradas_por_banco", []):
                if row.get("laba_banc") not in (None, ""):
                    banco_ids.add(int(row["laba_banc"]))
            for row in resumo.get("saidas_por_banco", []):
                if row.get("laba_banc") not in (None, ""):
                    banco_ids.add(int(row["laba_banc"]))
            for row in resumo.get("saldo_por_banco", []):
                if row.get("laba_banc") not in (None, ""):
                    banco_ids.add(int(row["laba_banc"]))

            for row in resumo.get("entradas_por_centro_custo", []):
                if row.get("laba_cecu") not in (None, ""):
                    centro_custo_ids.add(int(row["laba_cecu"]))
            for row in resumo.get("saidas_por_centro_custo", []):
                if row.get("laba_cecu") not in (None, ""):
                    centro_custo_ids.add(int(row["laba_cecu"]))
            for row in resumo.get("saldo_por_centro_custo", []):
                if row.get("laba_cecu") not in (None, ""):
                    centro_custo_ids.add(int(row["laba_cecu"]))

            entidades_map = {}
            if entidade_ids:
                qs_enti = Entidades.objects.using(banco).filter(enti_empr=str(empresa_id), enti_clie__in=list(entidade_ids))
                entidades_map = {int(obj.enti_clie): obj.enti_nome for obj in qs_enti}

            bancos_map = {}
            if banco_ids:
                qs_bancos = Entidades.objects.using(banco).filter(
                    enti_empr=str(empresa_id),
                    enti_clie__in=list(banco_ids),
                    enti_tien__in=["B", "C"],
                )
                bancos_map = {int(obj.enti_clie): obj.enti_nome for obj in qs_bancos}

            centros_custo_map = {}
            if centro_custo_ids:
                try:
                    from CentrodeCustos.models import Centrodecustos
                except Exception:
                    Centrodecustos = None
                if Centrodecustos:
                    qs_cc = Centrodecustos.objects.using(banco).filter(
                        cecu_empr=int(empresa_id),
                        cecu_redu__in=list(centro_custo_ids),
                    )
                    centros_custo_map = {int(obj.cecu_redu): obj.cecu_nome for obj in qs_cc}

            for row in resumo.get("entradas_por_entidade", []):
                enti_id = row.get("laba_enti")
                row["nome_entidade"] = entidades_map.get(int(enti_id)) if enti_id not in (None, "") else None
            for row in resumo.get("saidas_por_entidade", []):
                enti_id = row.get("laba_enti")
                row["nome_entidade"] = entidades_map.get(int(enti_id)) if enti_id not in (None, "") else None
            for row in resumo.get("saldo_por_entidade", []):
                enti_id = row.get("laba_enti")
                row["nome_entidade"] = entidades_map.get(int(enti_id)) if enti_id not in (None, "") else None

            for row in resumo.get("entradas_por_banco", []):
                banc_id = row.get("laba_banc")
                nome = bancos_map.get(int(banc_id)) if banc_id not in (None, "") else None
                row["banco_label"] = f"{banc_id} - {nome}" if nome else banc_id
            for row in resumo.get("saidas_por_banco", []):
                banc_id = row.get("laba_banc")
                nome = bancos_map.get(int(banc_id)) if banc_id not in (None, "") else None
                row["banco_label"] = f"{banc_id} - {nome}" if nome else banc_id
            for row in resumo.get("saldo_por_banco", []):
                banc_id = row.get("laba_banc")
                nome = bancos_map.get(int(banc_id)) if banc_id not in (None, "") else None
                row["banco_label"] = f"{banc_id} - {nome}" if nome else banc_id

            for row in resumo.get("entradas_por_centro_custo", []):
                cecu_id = row.get("laba_cecu")
                row["nome_centro_custo"] = centros_custo_map.get(int(cecu_id)) if cecu_id not in (None, "") else None
            for row in resumo.get("saidas_por_centro_custo", []):
                cecu_id = row.get("laba_cecu")
                row["nome_centro_custo"] = centros_custo_map.get(int(cecu_id)) if cecu_id not in (None, "") else None
            for row in resumo.get("saldo_por_centro_custo", []):
                cecu_id = row.get("laba_cecu")
                row["nome_centro_custo"] = centros_custo_map.get(int(cecu_id)) if cecu_id not in (None, "") else None

        ctx.update(resumo)
        ctx['slug'] = slug_val
        ctx['filtros'] = {
            'empresa': empresa_id,
            'filial': filial_id,
            'entidade': entidade_id_int,
            'entidade_display': entidade_display,
            'centro_custo': centro_custo_id_int,
            'centro_custo_display': centro_custo_display,
            'data_inicial': data_inicial,
            'data_final': data_final,
            'limite': limite_int,
        }

        return ctx
