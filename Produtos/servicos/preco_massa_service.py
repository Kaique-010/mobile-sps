from decimal import Decimal, ROUND_HALF_UP

from django.db import connections, IntegrityError

from Produtos.models import (
    FamiliaProduto,
    GrupoProduto,
    Marca,
    Produtos,
    SubgrupoProduto,
    Tabelaprecos,
)
from Produtos.preco_models import TabelaprecosPromocional
from Produtos.servicos.preco_promocional import (
    atualizar_preco_com_historico as atualizar_preco_promocional_com_historico,
    criar_preco_com_historico as criar_preco_promocional_com_historico,
)
from Produtos.servicos.preco_servico import (
    atualizar_preco_com_historico as atualizar_preco_normal_com_historico,
    criar_preco_com_historico as criar_preco_normal_com_historico,
)





class PrecoMassaService:
    CAMPOS_SUPORTADOS = ("tabe_prco", "tabe_cust", "tabe_cuge", "tabe_avis", "tabe_apra")

    @staticmethod
    def _to_decimal(value, default=Decimal("0")):
        if value in (None, ""):
            return default
        try:
            if isinstance(value, Decimal):
                return value
            s = str(value).strip().replace(".", "").replace(",", ".") if isinstance(value, str) else str(value)
            return Decimal(s)
        except Exception:
            return default

    @staticmethod
    def _round_money(value):
        return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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
    def listar_produtos(cls, *, banco, empresa, filial, page=1, page_size=30, **filtros):
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
            .select_related("prod_marc", "prod_fami", "prod_grup", "prod_sugr")
            .order_by("prod_nome")
        )

        total = base_qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        produtos = list(base_qs[start:end])
        codigos = [p.prod_codi for p in produtos]

        precos_normais = {}
        precos_promo = {}
        if codigos:
            for p in Tabelaprecos.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos
            ):
                precos_normais[p.tabe_prod] = p
            for p in TabelaprecosPromocional.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos
            ):
                precos_promo[p.tabe_prod] = p

        rows = []
        for prod in produtos:
            normal = precos_normais.get(prod.prod_codi)
            promo = precos_promo.get(prod.prod_codi)
            rows.append(
                {
                    "prod_codi": prod.prod_codi,
                    "prod_nome": prod.prod_nome,
                    "marca": getattr(prod.prod_marc, "nome", None),
                    "familia": getattr(prod.prod_fami, "descricao", None),
                    "grupo": getattr(prod.prod_grup, "descricao", None),
                    "subgrupo": getattr(prod.prod_sugr, "descricao", None),
                    "normal": {
                        "tabe_prco": float(getattr(normal, "tabe_prco", 0) or 0),
                        "tabe_cust": float(getattr(normal, "tabe_cust", 0) or 0),
                        "tabe_cuge": float(getattr(normal, "tabe_cuge", 0) or 0),
                        "tabe_avis": float(getattr(normal, "tabe_avis", 0) or 0),
                        "tabe_apra": float(getattr(normal, "tabe_apra", 0) or 0),
                    },
                    "promocional": {
                        "tabe_prco": float(getattr(promo, "tabe_prco", 0) or 0),
                        "tabe_cust": float(getattr(promo, "tabe_cust", 0) or 0),
                        "tabe_cuge": float(getattr(promo, "tabe_cuge", 0) or 0),
                        "tabe_avis": float(getattr(promo, "tabe_avis", 0) or 0),
                        "tabe_apra": float(getattr(promo, "tabe_apra", 0) or 0),
                    },
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
    def _calcular_valor(cls, *, tipo, valor_atual, percentual, valor_fixo):
        atual = cls._to_decimal(valor_atual, Decimal("0"))
        if tipo == "percentual":
            perc = cls._to_decimal(percentual, Decimal("0"))
            return cls._round_money(atual * (Decimal("1") + (perc / Decimal("100"))))
        return cls._round_money(cls._to_decimal(valor_fixo, atual))

    @classmethod
    def _montar_novos_dados(cls, *, instancia, tipo, percentual, valores, campos):
        novos = {}
        for campo in campos:
            if campo not in cls.CAMPOS_SUPORTADOS:
                continue
            valor_atual = getattr(instancia, campo, None)
            valor_fixo = (valores or {}).get(campo)
            if tipo == "valor" and valor_fixo in (None, ""):
                continue
            novos[campo] = cls._calcular_valor(
                tipo=tipo,
                valor_atual=valor_atual,
                percentual=percentual,
                valor_fixo=valor_fixo,
            )
        return novos
    
    
    
    @classmethod
    def _upsert_preco(cls, banco, empresa, filial, prod_codi, novos, tabela):
        """
        Faz INSERT ... ON CONFLICT DO UPDATE direto no PostgreSQL.
        Evita o problema do Django ORM com PK composta (tabe_empr só como pk).
        """
        campos = list(novos.keys())
        valores = list(novos.values())
        insert_cols = ", ".join(["tabe_empr", "tabe_fili", "tabe_prod"] + campos)
        placeholders = ", ".join(["%s"] * (3 + len(campos)))
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in campos)

        sql = f"""
            INSERT INTO {tabela} ({insert_cols})
            VALUES ({placeholders})
            ON CONFLICT (tabe_empr, tabe_fili, tabe_prod)
            DO UPDATE SET {set_clause}
        """
        params = [int(empresa), int(filial), str(prod_codi)] + valores

        with connections[banco].cursor() as cursor:
            cursor.execute(sql, params)
    
    

    @classmethod
    def aplicar_reajuste(
        cls,
        *,
        banco,
        empresa,
        filial,
        tipo,
        percentual=None,
        valores=None,
        campos=None,
        aplicar_normal=True,
        aplicar_promocional=True,
        codigos=None,
        **filtros,
    ):
        campos = [c for c in (campos or cls.CAMPOS_SUPORTADOS) if c in cls.CAMPOS_SUPORTADOS]
        if not campos:
            raise ValueError("Nenhum campo válido para atualizar.")
        if tipo not in {"percentual", "valor"}:
            raise ValueError("Tipo inválido. Use 'percentual' ou 'valor'.")

        qs = cls.montar_filtros(empresa=empresa, **filtros).using(banco)
        if codigos:
            qs = qs.filter(prod_codi__in=[str(c) for c in codigos if c])
        produtos = list(qs.only("prod_codi"))
        if not produtos:
            return {"total_produtos": 0, "atualizados_normal": 0, "atualizados_promocional": 0}

        codigos_prod = [p.prod_codi for p in produtos]
        normal_map = {}
        promo_map = {}

        if aplicar_normal:
            for p in Tabelaprecos.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos_prod
            ):
                normal_map[p.tabe_prod] = p

        if aplicar_promocional:
            for p in TabelaprecosPromocional.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos_prod
            ):
                promo_map[p.tabe_prod] = p

        atualizados_normal = 0
        atualizados_promocional = 0

        for prod_codi in codigos_prod:

            # ── TABELA NORMAL ────────────────────────────────────────────
            if aplicar_normal:
                inst_normal = normal_map.get(prod_codi)
                if inst_normal:
                    # Registro existe no map → atualiza normalmente via ORM
                    novos_normal = cls._montar_novos_dados(
                        instancia=inst_normal,
                        tipo=tipo,
                        percentual=percentual,
                        valores=valores,
                        campos=campos,
                    )
                    if novos_normal:
                        atualizar_preco_normal_com_historico(banco, inst_normal, novos_normal)
                        atualizados_normal += 1
                elif tipo == "valor":
                    # Registro não existe → upsert raw SQL, sem tocar no ORM
                    novos_create = cls._montar_novos_dados(
                        instancia=type("obj", (), {})(),
                        tipo=tipo,
                        percentual=percentual,
                        valores=valores,
                        campos=campos,
                    )
                    if novos_create:
                        cls._upsert_preco(
                            banco, empresa, filial, prod_codi,
                            novos_create, "tabelaprecos"
                        )
                        atualizados_normal += 1

            # ── TABELA PROMOCIONAL ───────────────────────────────────────
            if aplicar_promocional:
                inst_promo = promo_map.get(prod_codi)
                if inst_promo:
                    novos_promo = cls._montar_novos_dados(
                        instancia=inst_promo,
                        tipo=tipo,
                        percentual=percentual,
                        valores=valores,
                        campos=campos,
                    )
                    if novos_promo:
                        atualizar_preco_promocional_com_historico(banco, inst_promo, novos_promo)
                        atualizados_promocional += 1
                elif tipo == "valor":
                    novos_create = cls._montar_novos_dados(
                        instancia=type("obj", (), {})(),
                        tipo=tipo,
                        percentual=percentual,
                        valores=valores,
                        campos=campos,
                    )
                    if novos_create:
                        cls._upsert_preco(
                            banco, empresa, filial, prod_codi,
                            novos_create, "tabelaprecos_promocional"
                        )
                        atualizados_promocional += 1

        return {
            "total_produtos": len(codigos_prod),
            "atualizados_normal": atualizados_normal,
            "atualizados_promocional": atualizados_promocional,
        }

    @classmethod
    def preview_reajuste(
        cls,
        *,
        banco,
        empresa,
        filial,
        tipo,
        percentual=None,
        valores=None,
        campos=None,
        aplicar_normal=True,
        aplicar_promocional=True,
        codigos=None,
        page=None,
        page_size=None,
        limit=50,
        **filtros,
    ):
        campos = [c for c in (campos or cls.CAMPOS_SUPORTADOS) if c in cls.CAMPOS_SUPORTADOS]
        if not campos:
            raise ValueError("Nenhum campo válido para atualizar.")
        if tipo not in {"percentual", "valor"}:
            raise ValueError("Tipo inválido. Use 'percentual' ou 'valor'.")

        base_qs = cls.montar_filtros(empresa=empresa, **filtros).using(banco).select_related(
            "prod_marc", "prod_fami", "prod_grup", "prod_sugr"
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

        codigos_prod = [p.prod_codi for p in produtos]

        normal_map = {}
        promo_map = {}
        if codigos_prod and aplicar_normal:
            for p in Tabelaprecos.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos_prod
            ):
                normal_map[p.tabe_prod] = p
        if codigos_prod and aplicar_promocional:
            for p in TabelaprecosPromocional.objects.using(banco).filter(
                tabe_empr=int(empresa), tabe_fili=int(filial), tabe_prod__in=codigos_prod
            ):
                promo_map[p.tabe_prod] = p

        def as_float(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0

        resultados = []
        alterados = 0

        for prod in produtos:
            normal = normal_map.get(prod.prod_codi)
            promo = promo_map.get(prod.prod_codi)

            item = {
                "prod_codi": prod.prod_codi,
                "prod_nome": prod.prod_nome,
                "marca": getattr(prod.prod_marc, "nome", None),
                "familia": getattr(prod.prod_fami, "descricao", None),
                "grupo": getattr(prod.prod_grup, "descricao", None),
                "subgrupo": getattr(prod.prod_sugr, "descricao", None),
                "normal": {},
                "promocional": {},
            }

            mudou_item = False

            if aplicar_normal and normal:
                novos = cls._montar_novos_dados(
                    instancia=normal,
                    tipo=tipo,
                    percentual=percentual,
                    valores=valores,
                    campos=campos,
                )
                for campo in campos:
                    antes = getattr(normal, campo, None)
                    depois = novos.get(campo)
                    item["normal"][campo] = {"antes": as_float(antes), "depois": as_float(depois if depois is not None else antes)}
                    if depois is not None and cls._to_decimal(depois) != cls._to_decimal(antes):
                        mudou_item = True

            if aplicar_promocional and promo:
                novos = cls._montar_novos_dados(
                    instancia=promo,
                    tipo=tipo,
                    percentual=percentual,
                    valores=valores,
                    campos=campos,
                )
                for campo in campos:
                    antes = getattr(promo, campo, None)
                    depois = novos.get(campo)
                    item["promocional"][campo] = {"antes": as_float(antes), "depois": as_float(depois if depois is not None else antes)}
                    if depois is not None and cls._to_decimal(depois) != cls._to_decimal(antes):
                        mudou_item = True

            if mudou_item:
                alterados += 1
            resultados.append(item)

        return {"count": total, "alterados": alterados, "campos": campos, "results": resultados}

    @staticmethod
    def listar_filtros(banco):
        return {
            "marcas": list(Marca.objects.using(banco).all().order_by("nome").values("codigo", "nome")),
            "familias": list(FamiliaProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
            "grupos": list(GrupoProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
            "subgrupos": list(SubgrupoProduto.objects.using(banco).all().order_by("descricao").values("codigo", "descricao")),
        }
