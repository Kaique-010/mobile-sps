
from ..models import ParametroAgricola
from ..registry import ParametrosAgricolasRegistry
from core.utils import get_licenca_db_config
import json


class ParametroAgricolaService:

    @staticmethod
    def get(empresa, filial, chave, using='default'):
        try:
            param = ParametroAgricola.objects.using(using).get(
                para_empr=empresa,
                para_fili=filial,
                para_chav=chave,
            )
            return json.loads(param.para_valo)
        except (ParametroAgricola.DoesNotExist, json.JSONDecodeError):
            return ParametrosAgricolasRegistry.PARAMS[chave]["default"]

    @staticmethod
    def set(empresa, filial, chave, valor, using='default'):
        ParametroAgricola.objects.using(using).update_or_create(
            para_empr=empresa,
            para_fili=filial,
            para_chav=chave,
            defaults={"para_valo": json.dumps(valor)},
        )
