from django.db import IntegrityError

from Produtos.models import (
    FamiliaProduto,
    GrupoProduto,
    Marca,
    Produtos,
    SubgrupoProduto,
    UnidadeMedida,
)

from .produto_servico import cadastrar_produtro_padrao


class ProdutosEmMassaService:
    CAMPOS_SUPORTADOS = (
        "prod_nome",
        "prod_unme",
        "prod_grup",
        "prod_sugr",
        "prod_fami",
        "prod_marc",
        "prod_ncm",
        "prod_gtin",
        "prod_loca",
        "prod_orig_merc",
        "prod_codi_nume",
    )

    CAMPOS_FK = {
        "prod_unme": UnidadeMedida,
        "prod_grup": GrupoProduto,
        "prod_sugr": SubgrupoProduto,
        "prod_fami": FamiliaProduto,
        "prod_marc": Marca,
    }

    @staticmethod
    def cadastrar_produtro_padrao(
        banco,
        empresa_id,
        prod_desc,
        prod_unme,
        prod_ncm,
        prod_gtin,
        prod_codi_nume,
        prod_orig_merc,
    ):
        return cadastrar_produtro_padrao(
            banco,
            empresa_id,
            prod_desc,
            prod_unme,
            prod_ncm,
            prod_gtin,
            prod_codi_nume,
            prod_orig_merc,
        )

    @classmethod
    def montar_filtros(cls, *, empresa, marca=None, familia=None, grupo=None, subgrupo=None, busca=None):
        filtros = {"prod_empr": str(empresa)}
        if marca:
            filtros["prod_marc_id"] = str(marca)
        if familia:
            filtros["prod_fami_id"] = str(familia)
        if grupo:
            filtros["prod_grup_id"] = str(grupo)
        if subgrupo:
            filtros["prod_sugr_id"] = str(subgrupo)
        qs = Produtos.objects.filter(**filtros)
        if busca:
            busca = str(busca).strip()
            if busca:
                from django.db.models import Q

                qs = qs.filter(Q(prod_codi__icontains=busca) | Q(prod_nome__icontains=busca))
        return qs

    @classmethod
    def listar_produtos(cls, *, banco, empresa, filial=None, page=1, page_size=30, **filtros):
        try:
            page = max(1, int(page or 1))
        except Exception:
            page = 1
        try:
            page_size = max(1, min(200, int(page_size or 30)))
        except Exception:
            page_size = 30

        base_qs = (
            cls.montar_filtros(empresa=empresa, **filtros)
            .using(banco)
            .select_related("prod_unme", "prod_marc", "prod_fami", "prod_grup", "prod_sugr")
            .order_by("prod_nome")
        )

        total = base_qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        produtos = list(base_qs[start:end])

        rows = []
        for prod in produtos:
            rows.append(
                {
                    "prod_codi": prod.prod_codi,
                    "prod_nome": prod.prod_nome,
                    "prod_unme": getattr(prod, "prod_unme_id", None),
                    "prod_unme_desc": getattr(getattr(prod, "prod_unme", None), "unid_desc", None),
                    "prod_ncm": prod.prod_ncm,
                    "prod_gtin": prod.prod_gtin,
                    "prod_loca": prod.prod_loca,
                    "prod_orig_merc": prod.prod_orig_merc,
                    "prod_codi_nume": prod.prod_codi_nume,
                    "prod_marc": getattr(prod, "prod_marc_id", None),
                    "prod_marc_nome": getattr(getattr(prod, "prod_marc", None), "nome", None),
                    "prod_fami": getattr(prod, "prod_fami_id", None),
                    "prod_fami_desc": getattr(getattr(prod, "prod_fami", None), "descricao", None),
                    "prod_grup": getattr(prod, "prod_grup_id", None),
                    "prod_grup_desc": getattr(getattr(prod, "prod_grup", None), "descricao", None),
                    "prod_sugr": getattr(prod, "prod_sugr_id", None),
                    "prod_sugr_desc": getattr(getattr(prod, "prod_sugr", None), "descricao", None),
                }
            )

        return {
            "count": total,
            "page": page,
            "page_size": page_size,
            "num_pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": rows,
        }

    @classmethod
    def _valor_field(cls, obj, campo):
        if campo in cls.CAMPOS_FK:
            return getattr(obj, f"{campo}_id", None)
        return getattr(obj, campo, None)

    @classmethod
    def _display_field(cls, obj, campo):
        if campo == "prod_unme":
            return {
                "codigo": getattr(obj, "prod_unme_id", None),
                "descricao": getattr(getattr(obj, "prod_unme", None), "unid_desc", None),
            }
        if campo == "prod_marc":
            return {
                "codigo": getattr(obj, "prod_marc_id", None),
                "nome": getattr(getattr(obj, "prod_marc", None), "nome", None),
            }
        if campo == "prod_fami":
            return {
                "codigo": getattr(obj, "prod_fami_id", None),
                "descricao": getattr(getattr(obj, "prod_fami", None), "descricao", None),
            }
        if campo == "prod_grup":
            return {
                "codigo": getattr(obj, "prod_grup_id", None),
                "descricao": getattr(getattr(obj, "prod_grup", None), "descricao", None),
            }
        if campo == "prod_sugr":
            return {
                "codigo": getattr(obj, "prod_sugr_id", None),
                "descricao": getattr(getattr(obj, "prod_sugr", None), "descricao", None),
            }
        return getattr(obj, campo, None)

    @classmethod
    def _validate_and_build_update_data(cls, *, banco, campos, valores):
        campos = [c for c in (campos or []) if c in cls.CAMPOS_SUPORTADOS]
        if not campos:
            raise ValueError("Nenhum campo válido para atualizar.")

        update_data = {}
        for campo in campos:
            if campo not in (valores or {}):
                continue
            value = (valores or {}).get(campo)
            if isinstance(value, str):
                value = value.strip()
            if value == "":
                if campo in cls.CAMPOS_FK:
                    value = None
                else:
                    field = Produtos._meta.get_field(campo)
                    value = None if getattr(field, "null", False) else ""

            field = Produtos._meta.get_field(campo)
            if value is None and not getattr(field, "null", False):
                raise ValueError(f"Campo '{campo}' não pode ser nulo.")

            if campo in cls.CAMPOS_FK:
                if value is None:
                    update_data[f"{campo}_id"] = None
                    continue
                model_fk = cls.CAMPOS_FK[campo]
                if not model_fk.objects.using(banco).filter(pk=value).exists():
                    raise ValueError(f"Valor inválido para '{campo}': {value}")
                update_data[f"{campo}_id"] = value
                continue

            if campo == "prod_nome" and value in (None, ""):
                raise ValueError("Nome do produto é obrigatório.")
            update_data[campo] = value

        if not update_data:
            raise ValueError("Nenhum valor informado para aplicar nos campos selecionados.")
        return campos, update_data

    @classmethod
    def aplicar_atualizacao(
        cls,
        *,
        banco,
        empresa,
        valores,
        campos,
        codigos=None,
        **filtros,
    ):
        campos, update_data = cls._validate_and_build_update_data(banco=banco, campos=campos, valores=valores or {})

        qs = cls.montar_filtros(empresa=empresa, **filtros).using(banco)
        if codigos:
            qs = qs.filter(prod_codi__in=[str(c) for c in codigos if c])

        total = qs.count()
        atualizados = qs.update(**update_data) if total else 0
        return {"total_produtos": total, "atualizados": atualizados, "campos": campos}

    @classmethod
    def aplicar_atualizacao_linhas(cls, *, banco, empresa, updates):
        if not isinstance(updates, list) or not updates:
            raise ValueError("Nenhuma linha informada para atualização.")

        atualizados = 0
        total = 0
        for item in updates:
            if not isinstance(item, dict):
                continue
            prod_codi = item.get("prod_codi")
            valores = item.get("valores") or {}
            if not prod_codi or not isinstance(valores, dict) or not valores:
                continue

            campos = [c for c in valores.keys() if c in cls.CAMPOS_SUPORTADOS]
            _, update_data = cls._validate_and_build_update_data(banco=banco, campos=campos, valores=valores)

            qs = Produtos.objects.using(banco).filter(prod_empr=str(empresa), prod_codi=str(prod_codi))
            total += 1
            atualizados += qs.update(**update_data)

        return {"total_produtos": total, "atualizados": atualizados}

    @classmethod
    def preview_atualizacao(
        cls,
        *,
        banco,
        empresa,
        valores=None,
        campos=None,
        codigos=None,
        page=None,
        page_size=None,
        limit=50,
        **filtros,
    ):
        campos = [c for c in (campos or cls.CAMPOS_SUPORTADOS) if c in cls.CAMPOS_SUPORTADOS]
        if not campos:
            raise ValueError("Nenhum campo válido para atualizar.")

        base_qs = cls.montar_filtros(empresa=empresa, **filtros).using(banco).select_related(
            "prod_unme", "prod_marc", "prod_fami", "prod_grup", "prod_sugr"
        )
        if codigos:
            codigos_list = [str(c) for c in codigos if c]
            base_qs = base_qs.filter(prod_codi__in=codigos_list)

        total = base_qs.count()

        if page is not None and page_size is not None and not codigos:
            try:
                page = max(1, int(page or 1))
            except Exception:
                page = 1
            try:
                page_size = max(1, min(200, int(page_size or 30)))
            except Exception:
                page_size = 30
            start = (page - 1) * page_size
            end = start + page_size
            produtos = list(base_qs.order_by("prod_nome")[start:end])
        else:
            try:
                limit = max(1, min(500, int(limit or 50)))
            except Exception:
                limit = 50
            produtos = list(base_qs.order_by("prod_nome")[:limit])

        resultados = []
        alterados = 0
        valores = valores or {}

        for prod in produtos:
            item = {
                "prod_codi": prod.prod_codi,
                "prod_nome": prod.prod_nome,
                "marca": getattr(getattr(prod, "prod_marc", None), "nome", None),
                "familia": getattr(getattr(prod, "prod_fami", None), "descricao", None),
                "grupo": getattr(getattr(prod, "prod_grup", None), "descricao", None),
                "subgrupo": getattr(getattr(prod, "prod_sugr", None), "descricao", None),
                "campos": {},
            }
            mudou_item = False

            for campo in campos:
                antes_val = cls._valor_field(prod, campo)
                depois_raw = valores.get(campo, None)

                if campo in cls.CAMPOS_FK:
                    if campo in valores:
                        depois_val = depois_raw
                    else:
                        depois_val = antes_val
                else:
                    if campo in valores and depois_raw != "":
                        depois_val = depois_raw
                    else:
                        depois_val = antes_val

                item["campos"][campo] = {"antes": cls._display_field(prod, campo), "depois": depois_val}
                if str(antes_val or "") != str(depois_val or ""):
                    mudou_item = True

            if mudou_item:
                alterados += 1
            resultados.append(item)

        return {"count": total, "alterados": alterados, "campos": campos, "results": resultados}

    @staticmethod
    def listar_filtros(banco):
        return {
            "unidades": list(UnidadeMedida.objects.using(banco).all().order_by("unid_desc").values("unid_codi", "unid_desc")),
            "marcas": list(Marca.objects.using(banco).all().order_by("nome").values("codigo", "nome")),
            "familias": list(FamiliaProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
            "grupos": list(GrupoProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
            "subgrupos": list(SubgrupoProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
        }
