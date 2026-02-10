from decimal import Decimal
from django.db import transaction
import json
from datetime import datetime
import uuid
from pathlib import Path
from django.conf import settings

from ..models import Nota, NotaItem, NotaItemImposto
from Licencas.models import Filiais
from Entidades.models import Entidades
from Produtos.models import Produtos
from CFOP.services.services import MotorFiscal, FiscalContexto, get_empresa_uf_origem, get_regime

class ResolverIncidencia:
    """
    Resolve regras de incidência fiscal baseadas no cabeçalho da Nota
    (ex: Isenções, Imunidades, Suframa, Simples Nacional).
    """
    @staticmethod
    def aplicar_regras_nota(nota: Nota, cfop_obj):
        """
        Ajusta flags do CFOP em memória baseado nas regras da Nota.
        """
        if not cfop_obj:
            return cfop_obj
            
        # Lógica de Exemplo: Zona Franca (Mock)
        # if nota.destinatario.is_suframa:
        #     cfop_obj.cfop_exig_ipi = False
        #     cfop_obj.cfop_exig_icms = False
        
        return cfop_obj


class CalculoImpostosService:
    """
    Calcula e aplica impostos para uma Nota:
    - Usa MotorFiscal refatorado para garantir determinismo e isolamento.
    - Preenche NotaItemImposto item a item.
    """

    def __init__(self, database: str = "default"):
        self.banco = database

    def _mask_ncm(self, ncm_code):
        if not ncm_code:
            return None
        s = str(ncm_code).strip()
        if len(s) <= 4:
            return s
        return s[:4] + ("*" * (len(s) - 4))

    def _to_str(self, value):
        if value is None:
            return None
        return str(value)

    def aplicar_impostos(self, nota: Nota, return_debug: bool = False):
        nota = Nota.objects.using(self.banco).get(pk=nota.pk)

        debug_id = str(uuid.uuid4())
        inicio = datetime.utcnow().isoformat() + "Z"
        debug_data = {
            "debug_id": debug_id,
            "timestamp_inicio": inicio,
            "ambiente": {
                "debug": bool(getattr(settings, "DEBUG", False)),
                "database_alias": self.banco,
            },
            "tabelas_tributacao": {
                "versao": getattr(settings, "TRIBUTACAO_VERSAO", "desconhecida"),
            },
            "nota": {
                "id": nota.pk,
                "modelo": self._to_str(getattr(nota, "modelo", None)),
                "serie": self._to_str(getattr(nota, "serie", None)),
                "numero": self._to_str(getattr(nota, "numero", None)),
                "empresa": self._to_str(getattr(nota, "empresa", None)),
                "filial": self._to_str(getattr(nota, "filial", None)),
                "destinatario_id": self._to_str(getattr(nota, "destinatario_id", None)),
            },
            "itens": [],
            "logs": [],
        }

        uf_origem = get_empresa_uf_origem(
            empresa_id=nota.empresa,
            filial_id=nota.filial,
            banco=self.banco,
        )
        
        regime = get_regime(
            empresa_id=nota.empresa,
            filial_id=nota.filial,
            banco=self.banco,
        )

        uf_destino = (nota.destinatario.enti_esta or "").strip()

        debug_data["nota"]["uf_origem"] = uf_origem
        debug_data["nota"]["uf_destino"] = uf_destino
        debug_data["nota"]["regime"] = self._to_str(regime)

        motor = MotorFiscal(banco=self.banco)
        tipo_oper = self._mapear_tipo_operacao(nota)

        debug_data["logs"].append({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tipo": "contexto_nota",
            "mensagem": "Contexto fiscal inicial da nota.",
            "dados": {
                "tipo_operacao": tipo_oper,
            },
        })

        itens = (
            NotaItem.objects.using(self.banco)
            .select_related("produto")
            .filter(nota=nota)
        )

        with transaction.atomic(using=self.banco):
            for item in itens:
                item_debug = {
                    "id": item.pk,
                    "produto_id": item.produto_id,
                    "descricao_produto": getattr(item.produto, "prod_nome", None),
                    "ncm_produto": self._mask_ncm(getattr(item.produto, "prod_ncm", None)),
                    "cfop_inicial": self._to_str(getattr(item, "cfop", None)),
                    "quantidade": self._to_str(getattr(item, "quantidade", None)),
                    "unitario": self._to_str(getattr(item, "unitario", None)),
                    "desconto": self._to_str(getattr(item, "desconto", None)),
                    "logs": [],
                }

                item_debug["logs"].append({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "tipo": "antes_calculo_item",
                    "mensagem": "Início do cálculo de impostos para o item.",
                    "dados": {
                        "uf_origem": uf_origem,
                        "uf_destino": uf_destino,
                        "regime": self._to_str(regime),
                        "tipo_operacao": tipo_oper,
                    },
                })

                pacote = self._calcular_pacote_item(
                    motor=motor,
                    nota=nota,
                    item=item,
                    uf_origem=uf_origem,
                    uf_destino=uf_destino,
                    regime=regime,
                    tipo_oper=tipo_oper,
                )

                cfop_pacote = pacote.get("cfop")
                ncm_pacote = pacote.get("ncm")
                fonte_tributacao = pacote.get("fonte_tributacao")
                bases = pacote.get("bases", {})
                valores = pacote.get("valores", {})
                aliquotas = pacote.get("aliquotas", {})
                csts = pacote.get("csts", {})

                cfop_flags = None
                if cfop_pacote is not None:
                    cfop_flags = {
                        "exig_icms": getattr(cfop_pacote, "cfop_exig_icms", None),
                        "exig_ipi": getattr(cfop_pacote, "cfop_exig_ipi", None),
                        "exig_pis_cofins": getattr(cfop_pacote, "cfop_exig_pis_cofins", None),
                        "exig_cbs": getattr(cfop_pacote, "cfop_exig_cbs", None),
                        "exig_ibs": getattr(cfop_pacote, "cfop_exig_ibs", None),
                        "gera_st": getattr(cfop_pacote, "cfop_gera_st", None),
                    }

                ncm_codigo_resolvido = None
                if ncm_pacote is not None:
                    ncm_codigo_resolvido = self._mask_ncm(getattr(ncm_pacote, "ncm_codi", None))

                item_debug["fonte_tributacao"] = fonte_tributacao
                item_debug["cfop_resolvido"] = getattr(cfop_pacote, "cfop_codi", None) if cfop_pacote else None
                item_debug["cfop_flags"] = cfop_flags
                item_debug["ncm_resolvido"] = ncm_codigo_resolvido
                item_debug["bases"] = {
                    "raiz": self._to_str(bases.get("raiz")),
                    "icms": self._to_str(bases.get("icms")),
                    "st": self._to_str(bases.get("st")),
                }
                item_debug["aliquotas"] = {
                    "ipi": self._to_str(aliquotas.get("ipi")),
                    "icms": self._to_str(aliquotas.get("icms")),
                    "st": self._to_str(aliquotas.get("st")),
                    "pis": self._to_str(aliquotas.get("pis")),
                    "cofins": self._to_str(aliquotas.get("cofins")),
                    "cbs": self._to_str(aliquotas.get("cbs")),
                    "ibs": self._to_str(aliquotas.get("ibs")),
                }
                item_debug["valores_calculados"] = {
                    "ipi": self._to_str(valores.get("ipi")),
                    "icms": self._to_str(valores.get("icms")),
                    "st": self._to_str(valores.get("st")),
                    "pis": self._to_str(valores.get("pis")),
                    "cofins": self._to_str(valores.get("cofins")),
                    "cbs": self._to_str(valores.get("cbs")),
                    "ibs": self._to_str(valores.get("ibs")),
                }
                item_debug["csts"] = csts
                item_debug["condicionais_aplicadas"] = {
                    "icms_habilitado_cfop": None if cfop_flags is None else bool(cfop_flags.get("exig_icms")),
                    "ipi_habilitado_cfop": None if cfop_flags is None else bool(cfop_flags.get("exig_ipi")),
                    "pis_cofins_habilitado_cfop": None if cfop_flags is None else bool(cfop_flags.get("exig_pis_cofins")),
                    "cbs_habilitado_cfop": None if cfop_flags is None else bool(cfop_flags.get("exig_cbs")),
                    "ibs_habilitado_cfop": None if cfop_flags is None else bool(cfop_flags.get("exig_ibs")),
                }

                debug_data["itens"].append(item_debug)

                self._aplicar_no_item_nota(item, pacote)

        debug_data["timestamp_fim"] = datetime.utcnow().isoformat() + "Z"

        try:
            base_dir = Path(getattr(settings, "BASE_DIR", "."))
            file_path = base_dir / "debug.json"
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

        if return_debug:
            return debug_data

    # ------------------------------------------------------------------
    # MAPEAMENTO DE TIPO OPERAÇÃO (nota → MotorFiscal / MapaCFOP)
    # ------------------------------------------------------------------
    def _mapear_tipo_operacao(self, nota: Nota) -> str:
        if nota.tipo_operacao == 1:  # Saída
            if nota.finalidade == 4:  # Devolução
                return "DEVOLUCAO_COMPRA"
            return "VENDA"
        else:  # Entrada
            if nota.finalidade == 4:
                return "DEVOLUCAO_VENDA"
            return "COMPRA"

    # ------------------------------------------------------------------
    # CÁLCULO DO PACOTE FISCAL PARA UM ITEM DA NOTA
    # ------------------------------------------------------------------
    def _calcular_pacote_item(
        self,
        motor: MotorFiscal,
        nota: Nota,
        item: NotaItem,
        uf_origem: str,
        uf_destino: str,
        regime: str,
        tipo_oper: str,
    ) -> dict:
        
        # 1. Preparar Contexto Fiscal
        from CFOP.models import CFOP
        
        # Resolve CFOP (Override ou Automático)
        cfop_obj = None
        if item.cfop:
             cfop_obj = CFOP.objects.using(self.banco).select_related("fiscal").filter(
                 cfop_codi=item.cfop, cfop_empr=nota.empresa
             ).first()
        else:
             cfop_obj = motor.resolver_cfop(tipo_oper, uf_origem, uf_destino)
             
        # Aplica Regras de Incidência (Suframa, Isenções, etc)
        cfop_obj = ResolverIncidencia.aplicar_regras_nota(nota, cfop_obj)
             
        ctx = FiscalContexto(
            empresa_id=nota.empresa,
            filial_id=nota.filial,
            banco=self.banco,
            regime=regime,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            produto=item.produto,
            cfop=cfop_obj, # Passamos o objeto já resolvido e ajustado
            ncm=None # O motor resolve
        )

        # 2. Calcular Base da Nota (regras de desconto e total manual)
        base = self._calcular_base_nota_item(motor, item)

        # 3. Executar Motor Fiscal
        pacote = motor.calcular_item(ctx, item, tipo_oper, base_manual=base)
        
        return pacote

    def _calcular_base_nota_item(self, motor: MotorFiscal, item: NotaItem) -> Decimal:
        """
        Base de cálculo para NF:
        - se NotaItem.total_item preenchido, usa ele
        - senão: (quantidade * unitario) - desconto
        """
        if item.total_item is not None:
            return motor._d(item.total_item, 2)

        quant = motor._d(item.quantidade or 0, 5)
        unit = motor._d(item.unitario or 0, 5)
        desc = motor._d(item.desconto or 0, 5)

        total = (quant * unit) - desc
        return motor._d(total, 2)

    # ------------------------------------------------------------------
    # PERSISTÊNCIA EM NotaItem + NotaItemImposto
    # ------------------------------------------------------------------
    def _aplicar_no_item_nota(self, item: NotaItem, pacote: dict):
        # Atualiza campos do NotaItem
        item.cfop = pacote["cfop"].cfop_codi if pacote["cfop"] else item.cfop
        item.fonte_tributacao = pacote.get("fonte_tributacao")        
        csts = pacote["csts"]
        item.cst_icms = csts.get("icms") or ""
        item.cst_pis = csts.get("pis") or ""
        item.cst_cofins = csts.get("cofins") or ""
        item.cst_ipi = csts.get("ipi") or ""
        item.cst_ibs = csts.get("ibs") or ""
        item.cst_cbs = csts.get("cbs") or ""

        item.save(using=self.banco)

        # Atualizar ou Criar NotaItemImposto
        imposto, created = NotaItemImposto.objects.using(self.banco).get_or_create(
            item=item
        )

        bases = pacote["bases"]
        vals = pacote["valores"]
        aliqs = pacote["aliquotas"]

        # ICMS
        imposto.icms_base = bases.get("icms")
        imposto.icms_valor = vals.get("icms")
        imposto.icms_aliquota = aliqs.get("icms")

        # IPI
        imposto.ipi_base = bases.get("ipi")
        imposto.ipi_valor = vals.get("ipi")
        imposto.ipi_aliquota = aliqs.get("ipi")

        # PIS
        imposto.pis_base = bases.get("pis")
        imposto.pis_valor = vals.get("pis")
        imposto.pis_aliquota = aliqs.get("pis")

        # COFINS
        imposto.cofins_base = bases.get("cofins")
        imposto.cofins_valor = vals.get("cofins")
        imposto.cofins_aliquota = aliqs.get("cofins")

        # IBS
        imposto.ibs_base = bases.get("ibs")
        imposto.ibs_valor = vals.get("ibs")
        imposto.ibs_aliquota = aliqs.get("ibs")

        # CBS
        imposto.cbs_base = bases.get("cbs")
        imposto.cbs_valor = vals.get("cbs")
        imposto.cbs_aliquota = aliqs.get("cbs")
        
        # FCP
        imposto.fcp_valor = vals.get("fcp")

        imposto.save(using=self.banco)
