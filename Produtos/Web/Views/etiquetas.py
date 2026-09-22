import logging

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import (
    Case,
    CharField,
    DecimalField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value as V,
    When,
)
from django.db.models.functions import Cast, Coalesce
from django.http import JsonResponse
from django.views.generic import TemplateView

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from Produtos.models import (
    GrupoProduto,
    Marca,
    Produtos,
    SaldoProduto,
    SubgrupoProduto,
    Tabelaprecos,
)
from Produtos.servicos.grade_service import GradeService
from Produtos.servicos.modelo_etiqueta_service import ModeloEtiquetaService
from Produtos.utils import formatar_dados_etiqueta

logger = logging.getLogger(__name__)


class EtiquetasView(ModuloRequeridoMixin, TemplateView):
    template_name = "Produtos/etiquetas_print.html"
    modulo_necessario = "Produtos"
    itens_por_pagina = 50

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _obter_empresa_filial(self, request):
        empresa_id = (
            getattr(request.user, "empresa_id", None)
            or request.session.get("empresa_id")
        )

        filial_id = (
            getattr(request.user, "filial_id", None)
            or request.session.get("filial_id")
        )

        return empresa_id, filial_id

    def _criar_grade_service(self, banco, empresa_id, filial_id):
        if not filial_id:
            # GradeService filtra grad_fili=filial_id; com None nenhuma grade é encontrada.
            logger.warning(
                "Etiquetas: filial_id vazio (empresa=%s). "
                "As grades não serão encontradas.",
                empresa_id,
            )

        return GradeService(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
        )

    def _criar_modelo_etiqueta_service(self, banco, empresa_id, filial_id):
        return ModeloEtiquetaService(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
        )

    @staticmethod
    def _ler_quantidade(request, campo, padrao):
        try:
            return int(request.POST.get(campo, padrao))
        except (ValueError, TypeError):
            return padrao

    # ------------------------------------------------------------------
    # Busca de produtos (listagem com filtros)
    # ------------------------------------------------------------------
    def _buscar_produtos(
        self,
        request,
        banco,
        empresa_id,
        grade_service,
        busca,
        f_marca,
        f_grupo,
        f_subgrupo,
    ):
        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef("pk")
            ).values("saldo_estoque")[:1],
            output_field=DecimalField(),
        )

        preco_vista_subquery = Subquery(
            Tabelaprecos.objects.using(banco).filter(
                tabe_prod=OuterRef("prod_codi"),
                tabe_empr=OuterRef("prod_empr"),
            ).exclude(
                tabe_entr__year__lt=1900
            ).exclude(
                tabe_entr__year__gt=2100
            ).values("tabe_avis")[:1],
            output_field=DecimalField(),
        )

        qs = (
            Produtos.objects.using(banco)
            .select_related("prod_marc")
            .annotate(
                saldo_estoque=Coalesce(
                    saldo_subquery, V(0), output_field=DecimalField()
                ),
                prod_preco_vista=Coalesce(
                    preco_vista_subquery, V(0), output_field=DecimalField()
                ),
                prod_coba_str=Coalesce(
                    Cast("prod_coba", CharField()), V("")
                ),
                prod_codi_int=Case(
                    When(
                        prod_codi__regex=r"^\d+$",
                        then=Cast("prod_codi", IntegerField()),
                    ),
                    default=V(None),
                    output_field=IntegerField(),
                ),
            )
        )

        if busca:
            qs = qs.filter(
                Q(prod_nome__icontains=busca)
                | Q(prod_coba_str__exact=busca)
                | Q(prod_codi__exact=busca)
                | Q(prod_codi__exact=busca.lstrip("0"))
            )

        if f_marca:
            qs = qs.filter(prod_marc__codigo=f_marca)

        if f_grupo:
            qs = qs.filter(prod_grup__codigo=f_grupo)

        if f_subgrupo:
            qs = qs.filter(prod_sugr__codigo=f_subgrupo)

        if empresa_id:
            qs = qs.filter(prod_empr=empresa_id)

        qs = qs.order_by("prod_empr", "prod_codi_int")

        paginator = Paginator(qs, self.itens_por_pagina)
        page_obj = paginator.get_page(request.GET.get("page"))

        # Materializa a página para poder anexar os dados de grade em cada produto.
        page_obj.object_list = list(page_obj.object_list)

        grades_por_produto = grade_service.agrupar_por_produto(
            [produto.prod_codi for produto in page_obj.object_list]
        )

        for produto in page_obj.object_list:
            variacoes = grades_por_produto.get(str(produto.prod_codi), [])
            produto.grade_itens = variacoes
            produto.tem_grade = bool(variacoes)

        return page_obj

    # ------------------------------------------------------------------
    # Etiquetas via GET ?ids=1,2,3 (uma etiqueta por produto)
    # ------------------------------------------------------------------
    def _etiquetas_por_ids(self, banco, empresa_id, grade_service, ids):
        lista_ids = [i.strip() for i in ids.split(",") if i.strip()]

        qs = Produtos.objects.using(banco).filter(prod_codi__in=lista_ids)

        if empresa_id:
            qs = qs.filter(prod_empr=empresa_id)

        produtos = list(qs.select_related("prod_marc"))

        grades_por_produto = grade_service.agrupar_por_produto(
            [produto.prod_codi for produto in produtos]
        )

        etiquetas = []

        for produto in produtos:
            dados = formatar_dados_etiqueta(produto)
            variacoes = grades_por_produto.get(str(produto.prod_codi), [])

            dados["grade"] = variacoes
            dados["tem_grade"] = bool(variacoes)

            etiquetas.append(dados)

        return etiquetas

    # ------------------------------------------------------------------
    # Etiquetas via POST (seleção + quantidades)
    # ------------------------------------------------------------------
    def _etiquetas_por_selecao(
        self,
        request,
        banco,
        empresa_id,
        grade_service,
        produtos_ids,
    ):
        qs = Produtos.objects.using(banco).filter(prod_codi__in=produtos_ids)

        if empresa_id:
            qs = qs.filter(prod_empr=empresa_id)

        produtos = list(qs.select_related("prod_marc"))

        grades_por_produto = grade_service.agrupar_por_produto(
            [produto.prod_codi for produto in produtos]
        )

        etiquetas = []

        for produto in produtos:
            produto_id = str(produto.prod_codi)
            dados = formatar_dados_etiqueta(produto)
            variacoes = grades_por_produto.get(produto_id, [])

            if variacoes:
                for variacao in variacoes:
                    qtd = self._ler_quantidade(
                        request,
                        f"qtd_{produto_id}_{variacao['item_id']}",
                        padrao=0,
                    )

                    if qtd <= 0:
                        continue

                    dados_grade = {**dados, "grade": variacao, "tem_grade": True}
                    etiquetas.extend([dados_grade] * qtd)
            else:
                qtd = max(
                    self._ler_quantidade(
                        request, f"qtd_{produto_id}", padrao=1
                    ),
                    1,
                )

                dados_simples = {**dados, "grade": {}, "tem_grade": False}
                etiquetas.extend([dados_simples] * qtd)

        return etiquetas

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        banco = get_licenca_db_config(request)

        if not banco:
            return context

        empresa_id, filial_id = self._obter_empresa_filial(request)
        grade_service = self._criar_grade_service(banco, empresa_id, filial_id)

        modelo_service = self._criar_modelo_etiqueta_service(
            banco,
            empresa_id,
            filial_id,
        )

        context["modelos_etiqueta"] = modelo_service.listar_modelos()
        context["modelo_etiqueta_padrao"] = modelo_service.obter_modelo_padrao()

        modelo_id = (
            request.GET.get("modelo_etiqueta")
            or request.POST.get("modelo_etiqueta")
            or request.POST.get("modelo_id")
        )

        modelo_selecionado = None

        if modelo_id:
            try:
                modelo_selecionado = modelo_service.obter_por_id(modelo_id)
            except ValidationError:
                pass

        if not modelo_selecionado:
            modelo_selecionado = modelo_service.obter_modelo_padrao()

        context["modelo_etiqueta_selecionado"] = modelo_selecionado

        # Listas para os filtros
        context["marcas"] = Marca.objects.using(banco).all().order_by("nome")
        context["grupos"] = GrupoProduto.objects.using(banco).all().order_by("descricao")
        context["subgrupos"] = SubgrupoProduto.objects.using(banco).all().order_by("descricao")

        # Filtros do request (string vazia em vez de None, para não virar "None" nos links)
        busca = request.GET.get("q", "").strip()
        f_marca = request.GET.get("marca", "")
        f_grupo = request.GET.get("grupo", "")
        f_subgrupo = request.GET.get("sub_grupo", "")

        context["termo_busca"] = busca
        context["filtro_marca"] = f_marca
        context["filtro_grupo"] = f_grupo
        context["filtro_subgrupo"] = f_subgrupo

        if busca or f_marca or f_grupo or f_subgrupo:
            context["produtos_busca"] = self._buscar_produtos(
                request,
                banco,
                empresa_id,
                grade_service,
                busca,
                f_marca,
                f_grupo,
                f_subgrupo,
            )

        ids = request.GET.get("ids")

        if ids:
            context["etiquetas"] = self._etiquetas_por_ids(
                banco,
                empresa_id,
                grade_service,
                ids,
            )

        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get("acao")

        if acao == "salvar_modelo":
            return self._salvar_modelo(request)

        if acao == "novo_modelo":
            return self._criar_novo_modelo(request)

        context = self.get_context_data(**kwargs)

        produtos_ids = request.POST.getlist("produtos_selecionados")

        # Fallback: texto separado por vírgula
        if not produtos_ids and request.POST.get("produtos_ids_manual"):
            produtos_ids = [
                i.strip()
                for i in request.POST["produtos_ids_manual"].split(",")
                if i.strip()
            ]

        banco = get_licenca_db_config(request)

        if produtos_ids and banco:
            empresa_id, filial_id = self._obter_empresa_filial(request)
            grade_service = self._criar_grade_service(banco, empresa_id, filial_id)

            etiquetas = self._etiquetas_por_selecao(
                request,
                banco,
                empresa_id,
                grade_service,
                produtos_ids,
            )

            context["etiquetas"] = etiquetas
            context["sem_etiquetas"] = not etiquetas
        else:
            context["sem_etiquetas"] = True

        return self.render_to_response(context)

    # ------------------------------------------------------------------
    # Modelos de etiqueta (AJAX) — a regra fica no ModeloEtiquetaService
    # ------------------------------------------------------------------
    def _salvar_modelo(self, request):
        return self._processar_modelo(request, criar=False)

    def _criar_novo_modelo(self, request):
        return self._processar_modelo(request, criar=True)

    def _processar_modelo(self, request, criar):
        banco = get_licenca_db_config(request)

        if not banco:
            return JsonResponse({
                "sucesso": False,
                "mensagem": "Banco da licença não identificado.",
            }, status=400)

        empresa_id, filial_id = self._obter_empresa_filial(request)

        if not empresa_id:
            return JsonResponse({
                "sucesso": False,
                "mensagem": "Empresa não identificada.",
            }, status=400)

        service = self._criar_modelo_etiqueta_service(
            banco,
            empresa_id,
            filial_id,
        )

        try:
            dados = service.converter_dados_formulario(request.POST)

            if criar:
                modelo = service.criar_modelo(dados)
                mensagem = "Modelo criado com sucesso."
            else:
                modelo = service.atualizar_modelo(
                    request.POST.get("modelo_id"),
                    dados,
                )
                mensagem = "Modelo atualizado com sucesso."

        except ValidationError as erro:
            return JsonResponse({
                "sucesso": False,
                "mensagem": " ".join(erro.messages),
            }, status=400)

        except Exception:
            logger.exception("Erro ao salvar modelo de etiqueta")

            return JsonResponse({
                "sucesso": False,
                "mensagem": "Erro interno ao salvar o modelo.",
            }, status=500)

        return JsonResponse({
            "sucesso": True,
            "mensagem": mensagem,
            "modelo": service.para_dict(modelo),
        })