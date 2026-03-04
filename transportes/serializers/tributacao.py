from rest_framework import serializers
from transportes.models import Cte

class CteTributacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cte
        fields = [
            'id', 'cfop', 'cst_icms', 'aliq_icms', 'base_icms', 'reducao_icms', 'valor_icms',
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
