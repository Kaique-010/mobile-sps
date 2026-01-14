# notas_fiscais/services/itens_service.py

from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import NotaItem, NotaItemImposto
from ..handlers.itens_handler import ItensHandler
from Produtos.models import Produtos


class ItensService:

    @staticmethod
    def inserir_itens(nota, itens, impostos_map=None):
        """
        Cria os itens e seus impostos.
        impostos_map → dict {index_item: dados_impostos}
        """

        ItensHandler.validar_itens(itens)
        itens_norm = ItensHandler.normalizar_itens(itens)

        for index, item_data in enumerate(itens_norm):
            prod_val = item_data.get("produto")
            if prod_val and not isinstance(prod_val, Produtos):
                empresa = getattr(nota, "empresa", None)
                qs = Produtos.objects.using(nota._state.db).filter(prod_codi=str(prod_val))
                if empresa is not None:
                    qs = qs.filter(prod_empr=str(empresa))
                try:
                    produto_obj = qs.get()
                except Produtos.MultipleObjectsReturned:
                    raise ValidationError(
                        f"Produto {prod_val} possui múltiplos cadastros para a empresa {empresa}."
                    )
                except Produtos.DoesNotExist:
                    raise ValidationError(
                        f"Produto {prod_val} não encontrado para a empresa {empresa}."
                    )
                item_data["produto"] = produto_obj
            
            # Filtra campos para manter apenas os que existem no modelo NotaItem
            model_fields = {f.name for f in NotaItem._meta.get_fields()}
            clean_data = {k: v for k, v in item_data.items() if k in model_fields}
            
            item_obj = NotaItem.objects.create(nota=nota, **clean_data)

            # impostos
            if impostos_map and index in impostos_map:
                imp_raw = impostos_map[index]
                imp_norm = ItensHandler.normalizar_impostos(imp_raw)

                NotaItemImposto.objects.create(item=item_obj, **imp_norm)


    @staticmethod
    def atualizar_itens(nota, itens, impostos_map=None):
        """
        Remove tudo e recria.
        Mais simples e consistente para notas fiscais.
        """

        NotaItem.objects.filter(nota=nota).delete()

        ItensService.inserir_itens(nota, itens, impostos_map)
