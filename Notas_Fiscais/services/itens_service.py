# notas_fiscais/services/itens_service.py

from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import NotaItem, NotaItemImposto
from ..handlers.itens_handler import ItensHandler
from Produtos.models import Produtos
from core.utils import calcular_total_item_com_desconto


class ItensService:

    @staticmethod
    def inserir_itens(nota, itens, impostos_map=None):
        """
        Cria os itens e seus impostos.
        impostos_map → dict {index_item: dados_impostos}
        """

        ItensHandler.validar_itens(itens)
        itens_norm = ItensHandler.normalizar_itens(itens)

        db_alias = getattr(getattr(nota, "_state", None), "db", None) or "default"
        empresa_id = getattr(nota, "empresa", None)

        from CFOP.services.services import MotorFiscal, get_empresa_uf_origem

        uf_origem = get_empresa_uf_origem(
            empresa_id=getattr(nota, "empresa", None),
            filial_id=getattr(nota, "filial", None),
            banco=db_alias,
        )

        dest = getattr(nota, "destinatario", None)
        uf_destino = (getattr(dest, "enti_esta", None) or "").strip()
        if not uf_destino and getattr(nota, "destinatario_id", None):
            from Entidades.models import Entidades

            dest = (
                Entidades.objects.using(db_alias)
                .filter(pk=nota.destinatario_id)
                .first()
            )
            uf_destino = (getattr(dest, "enti_esta", None) or "").strip()

        if not uf_destino:
            uf_destino = uf_origem

        def mapear_tipo_operacao(n):
            if getattr(n, "tipo_operacao", None) == 1:
                if getattr(n, "finalidade", None) == 4:
                    return "DEVOLUCAO_COMPRA"
                return "VENDA"
            if getattr(n, "finalidade", None) == 4:
                return "DEVOLUCAO_VENDA"
            return "COMPRA"

        tipo_oper = mapear_tipo_operacao(nota)
        motor = MotorFiscal(banco=db_alias)

        for index, item_data in enumerate(itens_norm):
            prod_val = item_data.get("produto")
            if prod_val and not isinstance(prod_val, Produtos):
                qs = Produtos.objects.using(db_alias).filter(prod_codi=str(prod_val))
                if empresa_id is not None:
                    qs = qs.filter(prod_empr=str(empresa_id))
                try:
                    produto_obj = qs.get()
                except Produtos.MultipleObjectsReturned:
                    raise ValidationError(
                        f"Produto {prod_val} possui múltiplos cadastros para a empresa {empresa_id}."
                    )
                except Produtos.DoesNotExist:
                    raise ValidationError(
                        f"Produto {prod_val} não encontrado para a empresa {empresa_id}."
                    )
                item_data["produto"] = produto_obj
            
            model_fields = {f.name for f in NotaItem._meta.get_fields()}
            clean_data = {k: v for k, v in item_data.items() if k in model_fields}

            produto_obj = item_data.get("produto")
            if isinstance(produto_obj, Produtos):
                if ("ncm" in model_fields) and (not str(clean_data.get("ncm") or "").strip()):
                    ncm_raw = str(getattr(produto_obj, "prod_ncm", "") or "")
                    ncm_digits = "".join(ch for ch in ncm_raw if ch.isdigit())[:8]
                    if ncm_digits:
                        clean_data["ncm"] = ncm_digits

                if ("cfop" in model_fields) and (not str(clean_data.get("cfop") or "").strip()):
                    cfop_obj = motor.resolver_cfop(tipo_oper, uf_origem, uf_destino)
                    if cfop_obj and getattr(cfop_obj, "cfop_codi", None):
                        clean_data["cfop"] = str(cfop_obj.cfop_codi)

            quantidade = clean_data.get("quantidade") or 0
            unitario = clean_data.get("unitario") or 0
            desconto = clean_data.get("desconto") or 0
            if "total_item" in model_fields and "total_item" not in clean_data:
                clean_data["total_item"] = calcular_total_item_com_desconto(
                    quantidade, unitario, desconto
                )

            item_obj = NotaItem.objects.using(db_alias).create(nota=nota, **clean_data)

            # impostos
            if impostos_map and index in impostos_map:
                imp_raw = impostos_map[index]
                imp_norm = ItensHandler.normalizar_impostos(imp_raw)

                NotaItemImposto.objects.using(db_alias).create(item=item_obj, **imp_norm)


    @staticmethod
    def atualizar_itens(nota, itens, impostos_map=None):
        """
        Remove tudo e recria.
        Mais simples e consistente para notas fiscais.
        """

        NotaItem.objects.filter(nota=nota).delete()

        ItensService.inserir_itens(nota, itens, impostos_map)
