from rest_framework import serializers
from ..models import Renegociado


class RenegociadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Renegociado
        fields = [
            "rene_id",
            "rene_empr",
            "rene_fili",
            "rene_clie",
            "rene_titu",
            "rene_seri",
            "rene_parc",
            "rene_venc",
            "rene_valo",
            "rene_perc_mult",
            "rene_valo_mult",
            "rene_perc_juro",
            "rene_valo_juro",
            "rene_desc",
            "rene_vlfn",
            "rene_data",
            "rene_stat",
            "rene_usua",
            "rene_obse",
            "rene_pai",
        ]
        read_only_fields = ["rene_id", "rene_data", "rene_stat"]

