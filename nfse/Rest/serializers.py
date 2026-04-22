from rest_framework import serializers

from nfse.models import Nfse, NfseItem


class NfseItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='nfsi_id', read_only=True)
    descricao = serializers.CharField(source='nfsi_desc')
    quantidade = serializers.DecimalField(source='nfsi_qtde', max_digits=15, decimal_places=4)
    valor_unitario = serializers.DecimalField(source='nfsi_unit', max_digits=15, decimal_places=6)
    valor_total = serializers.DecimalField(source='nfsi_tota', max_digits=15, decimal_places=2)
    servico_codigo = serializers.CharField(source='nfsi_serv_codi', required=False, allow_blank=True, allow_null=True)
    cnae_codigo = serializers.CharField(source='nfsi_cnae', required=False, allow_blank=True, allow_null=True)
    lc116_codigo = serializers.CharField(source='nfsi_lc116', required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = NfseItem
        fields = [
            'id',
            'descricao',
            'quantidade',
            'valor_unitario',
            'valor_total',
            'servico_codigo',
            'cnae_codigo',
            'lc116_codigo',
        ]


class NfseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='nfse_id', read_only=True)
    municipio_codigo = serializers.CharField(source='nfse_muni_codi', read_only=True)
    numero = serializers.CharField(source='nfse_nume', read_only=True)
    rps_numero = serializers.CharField(source='nfse_rps_nume')
    rps_serie = serializers.CharField(source='nfse_rps_seri', required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(source='nfse_statu', read_only=True)

    prestador_documento = serializers.CharField(source='nfse_pres_doc')
    prestador_nome = serializers.CharField(source='nfse_pres_nome')

    tomador_documento = serializers.CharField(source='nfse_tom_doc', required=False, allow_null=True, allow_blank=True)
    tomador_nome = serializers.CharField(source='nfse_tom_nome', required=False, allow_null=True, allow_blank=True)
    tomador_email = serializers.CharField(source='nfse_tom_email', required=False, allow_null=True, allow_blank=True)
    tomador_telefone = serializers.CharField(source='nfse_tom_fone', required=False, allow_null=True, allow_blank=True)
    tomador_endereco = serializers.CharField(source='nfse_tom_ende', required=False, allow_null=True, allow_blank=True)

    servico_codigo = serializers.CharField(source='nfse_serv_codi')
    servico_descricao = serializers.CharField(source='nfse_serv_desc')
    cnae_codigo = serializers.CharField(source='nfse_serv_cnae', required=False, allow_null=True, allow_blank=True)
    lc116_codigo = serializers.CharField(source='nfse_serv_lc116', required=False, allow_null=True, allow_blank=True)

    valor_servico = serializers.DecimalField(source='nfse_val_serv', max_digits=15, decimal_places=2)
    valor_iss = serializers.DecimalField(source='nfse_val_iss', max_digits=15, decimal_places=2, read_only=True)
    valor_liquido = serializers.DecimalField(source='nfse_val_liqu', max_digits=15, decimal_places=2, read_only=True)
    aliquota_iss = serializers.DecimalField(source='nfse_aliq_iss', max_digits=7, decimal_places=4, read_only=True)

    class Meta:
        model = Nfse
        fields = [
            'id',
            'municipio_codigo',
            'numero',
            'rps_numero',
            'rps_serie',
            'status',
            'prestador_documento',
            'prestador_nome',
            'tomador_documento',
            'tomador_nome',
            'tomador_email',
            'tomador_telefone',
            'tomador_endereco',
            'servico_codigo',
            'servico_descricao',
            'cnae_codigo',
            'lc116_codigo',
            'valor_servico',
            'valor_iss',
            'valor_liquido',
            'aliquota_iss',
        ]


class NfseDetailSerializer(NfseSerializer):
    itens = serializers.SerializerMethodField()

    class Meta(NfseSerializer.Meta):
        fields = NfseSerializer.Meta.fields + ['itens']

    def get_itens(self, obj):
        db_alias = getattr(obj._state, 'db', None)
        itens = NfseItem.objects
        if db_alias:
            itens = itens.using(db_alias)

        queryset = (
            itens
            .filter(
                nfsi_nfse_id=obj.nfse_id,
                nfsi_empr=obj.nfse_empr,
                nfsi_fili=obj.nfse_fili,
            )
            .order_by('nfsi_orde', 'nfsi_id')
        )
        return NfseItemSerializer(queryset, many=True).data


class EmitirNfseItemSerializer(serializers.Serializer):
    descricao = serializers.CharField()
    quantidade = serializers.DecimalField(max_digits=15, decimal_places=4)
    valor_unitario = serializers.DecimalField(max_digits=15, decimal_places=6)
    valor_total = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    servico_codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cnae_codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lc116_codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if not attrs.get('valor_total'):
            attrs['valor_total'] = attrs['quantidade'] * attrs['valor_unitario']
        return attrs


class EmitirNfseSerializer(serializers.Serializer):
    municipio_codigo = serializers.CharField()
    rps_numero = serializers.CharField()
    rps_serie = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    prestador_ie = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    prestador_documento = serializers.CharField()
    prestador_nome = serializers.CharField()

    tomador_documento = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_nome = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_telefone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_endereco = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_numero = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_bairro = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_cep = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_cidade = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_uf = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_ie = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tomador_im = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    servico_codigo = serializers.CharField()
    servico_descricao = serializers.CharField()
    cnae_codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lc116_codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    natureza_operacao = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    municipio_incidencia = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    municipio_servico = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    valor_servico = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_deducao = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_inss = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_irrf = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_csll = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_cofins = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_pis = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_iss = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    valor_liquido = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    aliquota_iss = serializers.DecimalField(max_digits=7, decimal_places=4, required=False, default=0)

    iss_retido = serializers.BooleanField(required=False, default=False)
    data_competencia = serializers.DateField(required=False)

    itens = EmitirNfseItemSerializer(many=True, required=False)

    def validate(self, attrs):
        itens = attrs.get('itens') or []

        if itens:
            total_itens = sum(item['valor_total'] for item in itens)
            if not attrs.get('valor_servico'):
                attrs['valor_servico'] = total_itens

        if not attrs.get('valor_liquido'):
            attrs['valor_liquido'] = (
                attrs.get('valor_servico', 0)
                - attrs.get('valor_iss', 0)
                - attrs.get('valor_inss', 0)
                - attrs.get('valor_irrf', 0)
                - attrs.get('valor_csll', 0)
                - attrs.get('valor_cofins', 0)
                - attrs.get('valor_pis', 0)
            )

        return attrs