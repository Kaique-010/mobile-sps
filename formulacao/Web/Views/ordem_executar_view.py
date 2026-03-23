from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.db.models import Max
from django.shortcuts import redirect
from django.views import View

from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from Produtos.models import Lote, Tabelaprecos

from ...models import OrdemProducao
from ...services.formulacao_service import ProducaoService


class OrdemProducaoExecutarView(View):
    def post(self, request, *args, **kwargs):
        slug = kwargs.get("slug") or get_licenca_slug()
        banco = get_licenca_db_config(request) or "default"
        empresa_id = int(request.session.get("empresa_id", 1))
        filial_id = int(request.session.get("filial_id", 1))
        usuario_id = int(request.session.get("usua_codi") or getattr(getattr(request, "user", None), "id", 1) or 1)
        pk = int(kwargs.get("pk"))

        op = (
            OrdemProducao.objects.using(banco)
            .select_related("op_prod")
            .filter(op_empr=empresa_id, op_fili=filial_id, op_nume=pk)
            .first()
        )
        if not op:
            messages.error(request, "Ordem não encontrada.")
            return redirect(f"/web/{slug}/formulacao/ordens/")

        def parse_date(value):
            if not value:
                return None
            if hasattr(value, "year"):
                return value
            try:
                return datetime.strptime(str(value), "%Y-%m-%d").date()
            except Exception:
                return None

        try:
            preco_vista = request.POST.get("preco_vista")
            preco_prazo = request.POST.get("preco_prazo")
            if preco_vista is not None or preco_prazo is not None:
                chave = {
                    "tabe_empr": empresa_id,
                    "tabe_fili": filial_id,
                    "tabe_prod": str(op.op_prod.prod_codi),
                }
                update_fields = {}
                if preco_vista is not None and str(preco_vista).strip() != "":
                    update_fields["tabe_avis"] = str(preco_vista)
                if preco_prazo is not None and str(preco_prazo).strip() != "":
                    update_fields["tabe_apra"] = str(preco_prazo)
                if update_fields:
                    qs = Tabelaprecos.objects.using(banco).filter(**chave)
                    if qs.exists():
                        qs.update(**update_fields)
                    else:
                        Tabelaprecos.objects.using(banco).create(**{**chave, **update_fields})

            lote_data_fabr = parse_date(request.POST.get("lote_data_fabr"))
            lote_data_vali = parse_date(request.POST.get("lote_data_venc") or request.POST.get("lote_data_vali"))

            produto_codigo = str(op.op_prod.prod_codi)
            raw_lote = (op.op_lote or "").strip()
            parts = [p.strip() for p in raw_lote.replace("_", "-").split("-") if p.strip()]
            candidato = next((p for p in reversed([raw_lote] + parts) if p.isdigit()), None)
            lote_numero = int(candidato) if candidato else None
            should_sync_op_lote = (not raw_lote) or raw_lote.isdigit() or (
                "-" in raw_lote and raw_lote.replace("_", "-").split("-")[-1].isdigit()
            )

            if lote_numero is None:
                max_lote = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=empresa_id, lote_prod=produto_codigo)
                    .aggregate(m=Max("lote_lote"))
                    .get("m")
                    or 0
                )
                lote_numero = int(max_lote) + 1

            existe_lote = Lote.objects.using(banco).filter(
                lote_empr=empresa_id,
                lote_prod=produto_codigo,
                lote_lote=lote_numero,
            )
            if not existe_lote.exists():
                max_lote = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=empresa_id, lote_prod=produto_codigo)
                    .aggregate(m=Max("lote_lote"))
                    .get("m")
                    or 0
                )
                if int(lote_numero) <= int(max_lote):
                    lote_numero = int(max_lote) + 1

                novo_op_lote = str(int(lote_numero))
                if should_sync_op_lote and raw_lote != novo_op_lote:
                    OrdemProducao.objects.using(banco).filter(
                        op_empr=empresa_id, op_fili=filial_id, op_nume=op.op_nume
                    ).update(op_lote=novo_op_lote)
                    op.op_lote = novo_op_lote
                    raw_lote = novo_op_lote

                lote = Lote(
                    lote_empr=empresa_id,
                    lote_prod=produto_codigo,
                    lote_lote=int(lote_numero),
                    lote_unit=Decimal("0.00"),
                    lote_sald=Decimal(str(op.op_quan or 0)).quantize(Decimal("0.01")),
                    lote_data_fabr=lote_data_fabr,
                    lote_data_vali=lote_data_vali,
                    lote_ativ=True,
                )
                lote.save(using=banco)
            else:
                novo_op_lote = str(int(lote_numero))
                if should_sync_op_lote and raw_lote != novo_op_lote:
                    OrdemProducao.objects.using(banco).filter(
                        op_empr=empresa_id, op_fili=filial_id, op_nume=op.op_nume
                    ).update(op_lote=novo_op_lote)
                    op.op_lote = novo_op_lote

                update = {
                    "lote_ativ": True,
                    "lote_sald": Decimal(str(op.op_quan or 0)).quantize(Decimal("0.01")),
                }
                if lote_data_fabr:
                    update["lote_data_fabr"] = lote_data_fabr
                if lote_data_vali:
                    update["lote_data_vali"] = lote_data_vali
                if update:
                    existe_lote.update(**update)

            ProducaoService.executar(op, db_slug=slug, usuario_id=usuario_id)
            messages.success(request, "Ordem executada com sucesso.")
        except Exception as e:
            messages.error(request, str(e))

        return redirect(f"/web/{slug}/formulacao/ordens/")
