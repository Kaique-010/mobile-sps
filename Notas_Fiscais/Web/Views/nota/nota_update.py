import logging

from django.views.generic import UpdateView
from django.urls import reverse
from core.utils import get_licenca_db_config
from django.core.exceptions import ValidationError
from ....models import Nota, NotaItem
from ...forms import NotaForm, NotaItemFormSet, TransporteForm
from ....services.nota_service import NotaService
from ....services.calculo_impostos_service import CalculoImpostosService
from ....dominio.builder import NotaBuilder
from ..base import SPSViewMixin
from django.contrib import messages
from django.http import HttpResponseRedirect


logger = logging.getLogger(__name__)


class NotaUpdateView(SPSViewMixin, UpdateView):
    model = Nota
    template_name = "notas/nota_form.html"
    form_class = NotaForm
    context_object_name = "nota"

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")
        qs = Nota.objects.using(banco)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        if filial is not None:
            qs = qs.filter(filial=filial)
        return qs

    def get_success_url(self):
        slug = self.kwargs.get("slug")
        return reverse("notas_list_web", kwargs={"slug": slug})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        kwargs.update({"database": banco, "empresa_id": empresa})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nota = self.object
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        try:
            transp_instance = nota.transporte
        except Nota.transporte.RelatedObjectDoesNotExist:
            transp_instance = None

        if self.request.POST:
            context["itens_formset"] = NotaItemFormSet(
                self.request.POST,
                instance=nota,
                queryset=NotaItem.objects.using(banco).filter(nota=nota).order_by("id"),
                form_kwargs={"database": banco, "empresa_id": empresa},
            )
            context["transporte_form"] = TransporteForm(self.request.POST, instance=transp_instance)
        else:
            context["itens_formset"] = NotaItemFormSet(
                instance=nota,
                queryset=NotaItem.objects.using(banco).filter(nota=nota).order_by("id"),
                form_kwargs={"database": banco, "empresa_id": empresa},
            )
            context["transporte_form"] = TransporteForm(instance=transp_instance)

        context["slug"] = self.kwargs.get("slug")

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        itens_fs = context["itens_formset"]
        transporte_form = context["transporte_form"]

        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")
        logger.info(
            "NotaUpdateView POST pk=%s banco=%s empresa=%s filial=%s btn_gravar=%s btn_calcular=%s",
            getattr(self.object, "pk", None),
            banco,
            empresa,
            filial,
            self.request.POST.get("btn_gravar"),
            self.request.POST.get("btn_calcular"),
        )
        try:
            mgmt_prefix = getattr(itens_fs, "prefix", "itens")
            tf = self.request.POST.get(f"{mgmt_prefix}-TOTAL_FORMS")
            inf = self.request.POST.get(f"{mgmt_prefix}-INITIAL_FORMS")
            logger.info(
                "NotaUpdateView formset prefix=%s TOTAL_FORMS=%s INITIAL_FORMS=%s bound_total=%s bound_initial=%s",
                mgmt_prefix,
                tf,
                inf,
                itens_fs.total_form_count(),
                itens_fs.initial_form_count(),
            )
        except Exception:
            pass

        if not itens_fs.is_valid() or not transporte_form.is_valid():
            return self.form_invalid(form)

        nota_data = form.cleaned_data
        itens = []
        for f in itens_fs:
            cd = getattr(f, "cleaned_data", None) or {}
            if not cd or cd.get("DELETE"):
                continue
            if not cd.get("produto"):
                continue
            itens.append(cd)
        transp = transporte_form.cleaned_data if transporte_form.has_changed() else None

        logger.info("NotaUpdateView itens_validos=%s transporte_changed=%s", len(itens), bool(transp))
        try:
            resumo = []
            for idx, it in enumerate(itens[:10]):
                prod = it.get("produto")
                prod_id = getattr(prod, "pk", None) if prod is not None else None
                resumo.append(
                    {
                        "idx": idx,
                        "produto": str(prod_id) if prod_id is not None else None,
                        "quantidade": str(it.get("quantidade") or ""),
                        "unitario": str(it.get("unitario") or ""),
                        "desconto": str(it.get("desconto") or ""),
                        "cfop": str(it.get("cfop") or ""),
                        "ncm": str(it.get("ncm") or ""),
                    }
                )
            logger.debug("NotaUpdateView itens_resumo=%s", resumo)
        except Exception:
            pass

        try:
            nota = NotaService.atualizar(
                nota=self.object,
                data=nota_data,
                itens=itens,
                impostos_map=None,
                transporte=transp,
                database=banco,
                usuario_id=getattr(getattr(self.request, "user", None), "id", None),
            )
        except ValidationError as e:
            logger.exception("NotaUpdateView ValidationError pk=%s", getattr(self.object, "pk", None))
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.exception("NotaUpdateView Exception pk=%s", getattr(self.object, "pk", None))
            messages.error(self.request, f"Erro ao salvar: {str(e)}")
            return self.form_invalid(form)

        # Recalcular impostos se solicitado ou se houver alterações
        if self.request.POST.get("btn_calcular") == "true":
            try:
                CalculoImpostosService(banco).aplicar_impostos(nota)
                messages.success(self.request, "Impostos calculados com sucesso.")
                return HttpResponseRedirect(self.request.path_info)
            except Exception as e:
                messages.error(self.request, f"Erro ao calcular impostos: {str(e)}")
                return self.form_invalid(form)

        if self.request.POST.get("btn_gravar") == "true":
            try:
                NotaService.gravar(nota, descricao="Rascunho atualizado via WEB", database=banco)
                messages.success(self.request, "Rascunho gravado.")
                logger.info("NotaUpdateView rascunho_gravado pk=%s", getattr(nota, "pk", None))
            except Exception as e:
                logger.exception("NotaUpdateView erro_gravar_rascunho pk=%s", getattr(self.object, "pk", None))
                messages.error(self.request, f"Erro ao gravar rascunho: {str(e)}")
                return self.form_invalid(form)

        try:
            empresa = self.request.session.get("empresa_id")
            filial = self.request.session.get("filial_id")
            dto = NotaBuilder(nota, database=banco).build()
            dto_payload = dto.dict()
            logger.debug(
                "NotaUpdateView.form_valid: DTO base para geração de XML da nota %s (empresa=%s, filial=%s): %s",
                nota.pk,
                empresa,
                filial,
                dto_payload,
            )
        except Exception as e:
            logger.warning("NotaUpdateView.form_valid: falha ao montar DTO para nota %s: %s", self.object.pk, e)

        return self.form_success()

    def form_invalid(self, form):
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        filial = self.request.session.get("filial_id")
        try:
            context = self.get_context_data(form=form)
            itens_fs = context.get("itens_formset")
            transp_form = context.get("transporte_form")
            try:
                prefix = getattr(itens_fs, "prefix", "itens")
                id0 = self.request.POST.get(f"{prefix}-0-id")
                id1 = self.request.POST.get(f"{prefix}-1-id")
                id_keys = [k for k in self.request.POST.keys() if k.endswith("-id")]
                id_sample = {k: self.request.POST.getlist(k)[:2] for k in id_keys[:10]}
            except Exception:
                prefix = None
                id0 = None
                id1 = None
                id_sample = None
            logger.warning(
                "NotaUpdateView INVALID pk=%s banco=%s empresa=%s filial=%s form_errors=%s itens_non_form=%s itens_errors=%s transp_errors=%s formset_prefix=%s id0=%s id1=%s id_keys_sample=%s",
                getattr(self.object, "pk", None),
                banco,
                empresa,
                filial,
                getattr(form, "errors", None),
                getattr(itens_fs, "non_form_errors", lambda: None)(),
                getattr(itens_fs, "errors", None),
                getattr(transp_form, "errors", None),
                prefix,
                id0,
                id1,
                id_sample,
            )
        except Exception:
            logger.exception("NotaUpdateView INVALID logging failed pk=%s", getattr(self.object, "pk", None))
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        banco = get_licenca_db_config(self.request) or "default"
        empresa = self.request.session.get("empresa_id")
        kwargs.update({"database": banco, "empresa_id": empresa})
        return kwargs
