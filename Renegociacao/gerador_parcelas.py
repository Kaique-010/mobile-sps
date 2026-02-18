from datetime import date, timedelta
from decimal import Decimal
from core.utils import get_db_from_slug
from contas_a_receber.services import criar_titulo_receber


class ParcelasGenerator:

    @staticmethod
    def gerar(
        *,
        slug: str,
        empresa_id: int,
        filial_id: int,
        cliente_id: int,
        renegociacao_id: int,
        valores: list,
        serie: str = "REN",
        vencimento_base: date | None = None,
        offsets: list[int] | None = None,
    ):
        banco = get_db_from_slug(slug)
        base = vencimento_base or date.today()
        offs = list(offsets or [])
        for i, valor in enumerate(valores, start=1):
            numero = f"REN{str(renegociacao_id).zfill(6)}-{str(i).zfill(3)}"
            if i == 1:
                dias = 0
            else:
                if len(offs) < (i - 1) and len(offs) > 0:
                    last = offs[-1]
                    offs = offs + [last] * ((i - 1) - len(offs))
                dias = sum(offs[: i - 1]) if offs else 30 * (i - 1)
            dados = {
                "titu_empr": empresa_id,
                "titu_fili": filial_id,
                "titu_clie": cliente_id,
                "titu_titu": numero,
                "titu_seri": serie,
                "titu_parc": str(i).zfill(3),
                "titu_emis": base,
                "titu_venc": base + timedelta(days=dias),
                "titu_valo": Decimal(str(valor)),
                "titu_hist": f"Título {numero} gerado por renegociação {renegociacao_id}",
                "titu_tipo": "Renegoc",
                "titu_aber": "A",
                "titu_ctrl": renegociacao_id,
                
            }
            criar_titulo_receber(banco=banco, dados=dados, empresa_id=empresa_id, filial_id=filial_id)
