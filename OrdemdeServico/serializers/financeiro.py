from .base import BancoModelSerializer
from contas_a_receber.models import Titulosreceber

class TituloReceberSerializer(BancoModelSerializer):
    class Meta:
        model = Titulosreceber
        fields = [
            'titu_empr', 'titu_fili', 'titu_titu', 'titu_seri',
            'titu_parc', 'titu_clie', 'titu_valo', 'titu_venc',
            'titu_form_reci',
        ]
