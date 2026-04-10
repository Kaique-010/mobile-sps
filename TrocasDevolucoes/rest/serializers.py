from rest_framework import serializers

from TrocasDevolucoes.models import TrocaDevolucao, ItensTrocaDevolucao


class ItensTrocaDevolucaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItensTrocaDevolucao
        fields = [
            'itdv_pdor', 'itdv_itor', 'itdv_pror', 'itdv_qtor', 'itdv_vlor',
            'itdv_prre', 'itdv_qtre', 'itdv_vlre', 'itdv_moti'
        ]


class TrocaDevolucaoSerializer(serializers.ModelSerializer):
    itens = ItensTrocaDevolucaoSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = TrocaDevolucao
        fields = [
            'tdvl_empr', 'tdvl_fili', 'tdvl_nume', 'tdvl_pdor', 'tdvl_clie',
            'tdvl_vend', 'tdvl_data', 'tdvl_tipo', 'tdvl_stat', 'tdvl_tode',
            'tdvl_tore', 'tdvl_safi', 'tdvl_obse', 'itens'
        ]
        read_only_fields = ['tdvl_nume']
