from decimal import Decimal
from django.db import transaction

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

    # ------------------------------------------------------------------
    # PÚBLICO: aplica em uma nota inteira
    # ------------------------------------------------------------------
    def aplicar_impostos(self, nota: Nota):
        """
        Calcula e aplica impostos para todos os itens da nota.
        """
        # Garante que estamos usando o banco correto
        nota = Nota.objects.using(self.banco).get(pk=nota.pk)

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

        motor = MotorFiscal(banco=self.banco)
        tipo_oper = self._mapear_tipo_operacao(nota)

        itens = (
            NotaItem.objects.using(self.banco)
            .select_related("produto")
            .filter(nota=nota)
        )

        with transaction.atomic(using=self.banco):
            for item in itens:
                pacote = self._calcular_pacote_item(
                    motor=motor,
                    nota=nota,
                    item=item,
                    uf_origem=uf_origem,
                    uf_destino=uf_destino,
                    regime=regime,
                    tipo_oper=tipo_oper,
                )
                self._aplicar_no_item_nota(item, pacote)

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
             cfop_obj = CFOP.objects.using(self.banco).filter(
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
        - se NotaItem.total preenchido, usa ele
        - senão: (quantidade * unitario) - desconto
        """
        if item.total is not None:
            return motor._d(item.total, 2)

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
        # item.ncm = pacote["ncm"]  # Se o motor retornasse NCM, mas geralmente vem do produto
        
        csts = pacote["csts"]
        item.cst_icms = csts.get("icms", "")
        item.cst_pis = csts.get("pis", "")
        item.cst_cofins = csts.get("cofins", "")
        item.cst_ipi = csts.get("ipi", "")
        item.cst_ibs = csts.get("ibs", "")
        item.cst_cbs = csts.get("cbs", "")

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
