from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import redirect

from core.utils import get_licenca_db_config
from Financeiro.Web.forms import OrcamentoForm
from Financeiro.models import Orcamento
from Financeiro.models import OrcamentoItem
from Financeiro.orcamento_financeiro_service import OrcamentoCadastroService


class OrcamentoCreateView(CreateView):
    model = Orcamento
    form_class = OrcamentoForm
    template_name = "financeiro/orcamento/form.html"

    def get_service(self):
        db_alias = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get("empresa_id")
        filial_id = self.request.session.get("filial_id")

        return OrcamentoCadastroService(
            db_alias=db_alias,
            empresa_id=int(empresa_id) if empresa_id is not None else None,
            filial_id=int(filial_id) if filial_id is not None else None,
        )

    def form_valid(self, form):
        service = self.get_service()

        orcamento = service.criar_orcamento(
            descricao=form.cleaned_data["descricao"],
            ano=form.cleaned_data["ano"],
            tipo=form.cleaned_data["tipo"],
            cenario=form.cleaned_data["cenario"],
            ativo=form.cleaned_data["ativo"],
        )

        self.object = orcamento
        messages.success(self.request, "Orçamento criado com sucesso.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("financeiro_web:orcamento_item_create", kwargs={"slug": self.kwargs.get("slug"), "orcamento_id": self.object.orca_id})

    


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.generic import FormView

from Financeiro.Web.forms import OrcamentoItemForm
from Financeiro.models import Orcamento


class OrcamentoItemCreateView(FormView):
    template_name = "financeiro/orcamento/item_form.html"
    form_class = OrcamentoItemForm

    def dispatch(self, request, *args, **kwargs):
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get("empresa_id")
        self.filial_id = request.session.get("filial_id")

        self.orcamento = get_object_or_404(
            Orcamento.objects.using(self.db_alias),
            orca_id=kwargs["orcamento_id"],
            orca_empr=int(self.empresa_id) if self.empresa_id is not None else None,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_service(self):
        return OrcamentoCadastroService(
            db_alias=self.db_alias,
            empresa_id=int(self.empresa_id),
            filial_id=int(self.filial_id) if self.filial_id else None,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["db_alias"] = self.db_alias
        kwargs["empresa_id"] = int(self.empresa_id)
        kwargs["permitir_sintetico"] = False
        return kwargs

    def form_valid(self, form):
        service = self.get_service()
        centro_custo_id = int(form.cleaned_data["centro_custo"])
        ano = form.cleaned_data["ano"]
        valor_previsto = form.cleaned_data["valor_previsto"]
        observacao = form.cleaned_data["observacao"]

        if form.cleaned_data.get("replicar_ano_todo"):
            itens = service.replicar_para_ano_todo(
                orcamento_id=self.orcamento.orca_id,
                centro_custo_id=centro_custo_id,
                ano=ano,
                valor_previsto=valor_previsto,
                observacao=observacao,
            )
            messages.success(self.request, f"Planejamento replicado para o ano todo ({len(itens)} meses).")
        else:
            meses = form.cleaned_data.get("meses") or []
            if meses:
                itens = service.criar_itens_varios_meses(
                    orcamento_id=self.orcamento.orca_id,
                    centro_custo_id=centro_custo_id,
                    ano=ano,
                    meses=meses,
                    valor_previsto=valor_previsto,
                    observacao=observacao,
                )
                messages.success(self.request, f"Planejamento salvo para {len(itens)} mês(es).")
            else:
                service.criar_item(
                    orcamento_id=self.orcamento.orca_id,
                    centro_custo_id=centro_custo_id,
                    ano=ano,
                    mes=int(form.cleaned_data["mes"]),
                    valor_previsto=valor_previsto,
                    observacao=observacao,
                )
                messages.success(self.request, "Item do orçamento salvo com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("financeiro_web:orcamento_item_create", kwargs={"slug": self.kwargs.get("slug"), "orcamento_id": self.orcamento.orca_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orcamento"] = self.orcamento
        context["slug"] = self.kwargs.get("slug")
        return context


def orcamento_item_buscar(request, slug=None, orcamento_id=None):
    db_alias = get_licenca_db_config(request)
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id")

    if not empresa_id or not orcamento_id:
        return JsonResponse({"found": False}, status=400)

    try:
        orcamento_id_int = int(orcamento_id)
    except Exception:
        return JsonResponse({"found": False}, status=400)

    try:
        centro_custo_id = int(request.GET.get("centro_custo_id") or 0)
        ano = int(request.GET.get("ano") or 0)
        mes = int(request.GET.get("mes") or 0)
    except Exception:
        return JsonResponse({"found": False}, status=400)

    if centro_custo_id <= 0 or ano <= 0 or mes <= 0:
        return JsonResponse({"found": False}, status=400)

    qs_orc = Orcamento.objects.using(db_alias).filter(
        orca_id=orcamento_id_int,
        orca_empr=int(empresa_id),
    )
    if filial_id:
        qs_orc = qs_orc.filter(orca_fili=int(filial_id))
    if not qs_orc.exists():
        return JsonResponse({"found": False}, status=404)

    qs = OrcamentoItem.objects.using(db_alias).filter(
        orci_empr=int(empresa_id),
        orci_orca=orcamento_id_int,
        orci_cecu=int(centro_custo_id),
        orci_ano=int(ano),
        orci_mes=int(mes),
    )
    if filial_id:
        qs = qs.filter(orci_fili=int(filial_id))
    item = qs.first()
    if not item:
        return JsonResponse({"found": False})

    valor = getattr(item, "orci_valo", None)
    try:
        valor_str = str(valor) if valor is not None else "0.00"
    except Exception:
        valor_str = "0.00"

    return JsonResponse(
        {
            "found": True,
            "valor_previsto": valor_str,
            "observacao": getattr(item, "orci_obse", "") or "",
        }
    )
