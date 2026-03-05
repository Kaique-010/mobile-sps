from rest_framework import serializers
from transportes.models import Cte
from Entidades.models import Entidades
from Licencas.models import Filiais
from CFOP.models import CFOP
from transportes.services.icms_service import ICMSCalculationService
from transportes.services.st_service import STService
from transportes.services.difal_service import DIFALService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class CteTributacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'cfop', 'cst_icms', 'aliq_icms', 'base_icms', 'reducao_icms', 'valor_icms',
            'base_icms_st', 'aliquota_icms_st', 'valor_icms_st', 'margem_valor_adicionado_st', 'reducao_base_icms_st',
            'valor_bc_uf_dest', 'valor_icms_uf_dest', 'aliquota_interna_dest', 'aliquota_interestadual',
            'cst_pis', 'aliquota_pis', 'base_pis', 'valor_pis',
            'cst_cofins', 'aliquota_cofins', 'base_cofins', 'valor_cofins',
            # IBS e CBS
            'ibscbs_vbc', 'ibscbs_cstid', 'ibscbs_cst', 'ibscbs_cclasstrib',
            'ibs_pdifuf', 'ibs_vdifuf', 'ibs_vdevtribuf', 'ibs_vdevtribmun',
            'cbs_vdevtrib', 'ibs_pibsuf', 'ibs_preduf', 'ibs_paliqefetuf',
            'ibs_vibsuf', 'ibs_pdifmun', 'ibs_vdifmun', 'ibs_pibsmun',
            'ibs_predmun', 'ibs_paliqefetmun', 'ibs_vibsmun', 'ibs_vibs',
            'cbs_pdif', 'cbs_vdif', 'cbs_pcbs', 'cbs_pred', 'cbs_paliqefet',
            'cbs_vcbs', 'ibscbs_cstregid', 'ibscbs_cstreg', 'ibscbs_cclasstribreg',
            'ibs_paliqefetufreg', 'ibs_vtribufreg'
        ]

    def validate(self, attrs):
        instance = self.instance
        # Se não tiver instância (create) ou se CFOP não foi enviado, não recalcula
        # Assumimos que o cálculo só ocorre quando o CFOP é alterado/informado explicitamente
        if not instance or 'cfop' not in attrs:
            return attrs

        try:
            db_alias = instance._state.db or 'default'
            cfop_val = attrs.get('cfop')
            
            if not cfop_val:
                return attrs

            # Busca CFOP
            cfop_obj = CFOP.objects.using(db_alias).filter(
                cfop_codi=str(cfop_val),
                cfop_empr=instance.empresa
            ).first()
            
            if not cfop_obj:
                 cfop_obj = CFOP.objects.using(db_alias).filter(
                    cfop_codi=str(cfop_val)
                ).first()
            
            if not cfop_obj:
                return attrs

            # Define Base de Cálculo (prioriza valor enviado, depois instância, depois total)
            base_icms = attrs.get('base_icms')
            if base_icms is None: # Se não enviado no payload
                base_icms = instance.total_valor or Decimal('0.00')
                # Não definimos attrs['base_icms'] ainda, pois o service pode retornar base reduzida
            
            # Busca Entidades
            remetente_id = instance.remetente
            destinatario_id = instance.destinatario
            
            if not remetente_id or not destinatario_id:
                return attrs
                
            remetente = Entidades.objects.using(db_alias).filter(pk=remetente_id).first()
            destinatario = Entidades.objects.using(db_alias).filter(pk=destinatario_id).first()
            
            if not remetente or not destinatario:
                return attrs
                
            filial_id = instance.filial
            filial = Filiais.objects.using(db_alias).filter(pk=filial_id).first()
            
            if not filial:
                return attrs

            # Parâmetros para o Service
            simples_nacional = str(filial.empr_regi_trib) == '1'
            uf_origem = remetente.enti_esta
            uf_destino = destinatario.enti_esta
            
            ie_dest = destinatario.enti_insc_esta
            contribuinte = bool(ie_dest and ie_dest.strip().upper() not in ['ISENTO', 'ISENTA', ''])
            
            # Adapters
            class ServiceEmpresaAdapter:
                def __init__(self, simples, db_alias='default'):
                    self.simples_nacional = simples
                    self._state = type('State', (), {'db': db_alias})
            
            class ServiceOperacaoAdapter:
                def __init__(self, uf_orig, uf_dest, contrib):
                    self.uf_origem = uf_orig
                    self.uf_destino = uf_dest
                    self.contribuinte = contrib
            
            empresa_adapter = ServiceEmpresaAdapter(simples_nacional, db_alias)
            operacao_adapter = ServiceOperacaoAdapter(uf_origem, uf_destino, contribuinte)
            
            # --- Cálculo ICMS ---
            icms_calculado_valor = Decimal('0.00')
            if cfop_obj.cfop_exig_icms:
                icms_service = ICMSCalculationService(empresa_adapter, operacao_adapter)
                res_icms = icms_service.calcular(base_icms, cfop_obj)
                
                if res_icms:
                    # Usa setdefault para não sobrescrever valores manuais enviados pelo usuário
                    attrs.setdefault('cst_icms', res_icms['cst'])
                    attrs.setdefault('aliq_icms', res_icms['aliquota'])
                    attrs.setdefault('valor_icms', res_icms['valor'])
                    attrs.setdefault('reducao_icms', res_icms['reducao'])
                    attrs.setdefault('base_icms', res_icms['base'])
                    icms_calculado_valor = res_icms['valor']

            # --- Cálculo ST ---
            if cfop_obj.cfop_gera_st:
                st_service = STService(empresa_adapter, operacao_adapter)
                res_st = st_service.calcular(base_icms, icms_calculado_valor, cfop_obj)
                
                if res_st:
                    attrs.setdefault('base_icms_st', res_st['base_st'])
                    attrs.setdefault('valor_icms_st', res_st['valor_st'])
                    attrs.setdefault('aliquota_icms_st', res_st['aliquota_st'])
                    attrs.setdefault('margem_valor_adicionado_st', res_st['mva_st'])

            # --- Cálculo DIFAL ---
            if cfop_obj.cfop_gera_difal:
                difal_service = DIFALService(empresa_adapter, operacao_adapter)
                res_difal = difal_service.calcular(base_icms, icms_calculado_valor, cfop_obj)
                
                if res_difal:
                    attrs.setdefault('valor_bc_uf_dest', res_difal['base_difal'])
                    attrs.setdefault('valor_icms_uf_dest', res_difal['valor_difal'])
                    attrs.setdefault('aliquota_interestadual', res_difal['aliquota_interestadual'])
                    attrs.setdefault('aliquota_interna_dest', res_difal['aliquota_destino'])

        except Exception as e:
            logger.error(f"Erro ao calcular impostos no CteTributacaoSerializer: {e}")
            
        return attrs
