from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .base import BancoModelSerializer
from ..models import Ordemservicopecas, Ordemservicoservicos

class OrdemServicoPecasSerializer(serializers.ModelSerializer):
    produto_nome = serializers.SerializerMethodField()
    peca_id = serializers.IntegerField(required=False)
    peca_empr = serializers.IntegerField(required=True)
    peca_fili = serializers.IntegerField(required=True)
    peca_orde = serializers.IntegerField(required=True)
    peca_codi = serializers.CharField(required=True)
    peca_comp = serializers.CharField(required=False, allow_blank=True)
    peca_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=True)
    peca_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=True)
    peca_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False)
   
    class Meta:
        model = Ordemservicopecas
        fields = '__all__'

    def validate(self, data):
        campos_obrigatorios = ['peca_empr', 'peca_fili', 'peca_orde', 'peca_codi']
        for campo in campos_obrigatorios:
            if campo not in data:
                raise serializers.ValidationError(f"O campo {campo} é obrigatório.")
            if data[campo] is None:
                raise serializers.ValidationError(f"O campo {campo} não pode ser nulo.")

        if data.get('peca_quan', 0) < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")
        
        if 'peca_tota' not in data and 'peca_quan' in data and 'peca_unit' in data:
            data['peca_tota'] = data['peca_quan'] * data['peca_unit']

        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")

        # Validação de duplicidade
        # Ignora se o contexto solicitar (ex: durante update geral da ordem onde IDs podem faltar)
        if not self.context.get('skip_duplicate_check'):
            qs = Ordemservicopecas.objects.using(banco).filter(
                peca_empr=data.get('peca_empr') if data.get('peca_empr') is not None else getattr(self.instance, 'peca_empr', None),
                peca_fili=data.get('peca_fili') if data.get('peca_fili') is not None else getattr(self.instance, 'peca_fili', None),
                peca_orde=data.get('peca_orde') if data.get('peca_orde') is not None else getattr(self.instance, 'peca_orde', None),
                peca_codi=data.get('peca_codi') if data.get('peca_codi') is not None else getattr(self.instance, 'peca_codi', None),
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Esta peça já foi informada nesta ordem de serviço.")


        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
        return Ordemservicopecas.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        for key in ['peca_id', 'peca_empr', 'peca_fili', 'peca_orde']:
            if key in validated_data:
                validated_data.pop(key)

        quan = validated_data.get('peca_quan')
        unit = validated_data.get('peca_unit')
        if quan is not None and unit is not None and 'peca_tota' not in validated_data:
            try:
                validated_data['peca_tota'] = quan * unit
            except Exception:
                pass

        return super().update(instance, validated_data)

    def get_produto_nome(self, obj):
        try:
            banco = self.context.get('banco')
            from django.db.models import Q
            from Produtos.models import Produtos
            codigo = str(obj.peca_codi)
            empresa = str(getattr(obj, 'peca_empr', ''))
            qs = Produtos.objects.using(banco).filter(
                Q(prod_codi=codigo) | Q(prod_codi_nume=codigo)
            )
            if empresa:
                qs = qs.filter(prod_empr=empresa)
            produto = qs.first()
            return produto.prod_nome if produto else ""
        except Exception:
            return ""

class OrdemServicoServicosSerializer(BancoModelSerializer):
    serv_id = serializers.IntegerField(required=False)
    serv_empr = serializers.IntegerField(required=True)
    serv_fili = serializers.IntegerField(required=True)
    serv_orde = serializers.IntegerField(required=True)
    serv_sequ = serializers.IntegerField(required=False)
    serv_codi = serializers.CharField(required=True)
    serv_comp = serializers.CharField(required=False, allow_blank=True)
    serv_quan = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_unit = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    serv_tota = serializers.DecimalField(max_digits=15, decimal_places=4, required=False, default=0)
    servico_nome = serializers.SerializerMethodField()

    class Meta:
        model = Ordemservicoservicos
        fields = '__all__'
        
    def validate(self, data):
        campos_obrigatorios = ['serv_empr', 'serv_fili', 'serv_orde', 'serv_codi']
        for campo in campos_obrigatorios:
            if campo not in data:
                raise serializers.ValidationError(f"O campo {campo} é obrigatório.")
            if data[campo] is None:
                raise serializers.ValidationError(f"O campo {campo} não pode ser nulo.")

        if data.get('serv_quan', 0) < 0:
            raise serializers.ValidationError("A quantidade não pode ser negativa.")

        if 'serv_tota' not in data and 'serv_quan' in data and 'serv_unit' in data:
            data['serv_tota'] = data['serv_quan'] * data['serv_unit']

        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")

        # Validação de duplicidade
        # Ignora se o contexto solicitar
        if not self.context.get('skip_duplicate_check'):
            qs = Ordemservicoservicos.objects.using(banco).filter(
                serv_empr=data.get('serv_empr') if data.get('serv_empr') is not None else getattr(self.instance, 'serv_empr', None),
                serv_fili=data.get('serv_fili') if data.get('serv_fili') is not None else getattr(self.instance, 'serv_fili', None),
                serv_orde=data.get('serv_orde') if data.get('serv_orde') is not None else getattr(self.instance, 'serv_orde', None),
                serv_codi=data.get('serv_codi') if data.get('serv_codi') is not None else getattr(self.instance, 'serv_codi', None),
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Este serviço já foi informado nesta ordem de serviço.")


        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco de dados não fornecido.")
        return Ordemservicoservicos.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        for key in ['serv_id', 'serv_empr', 'serv_fili', 'serv_orde', 'serv_sequ']:
            if key in validated_data:
                validated_data.pop(key)

        quan = validated_data.get('serv_quan')
        unit = validated_data.get('serv_unit')
        if quan is not None and unit is not None and 'serv_tota' not in validated_data:
            try:
                validated_data['serv_tota'] = quan * unit
            except Exception:
                pass

        return super().update(instance, validated_data)

    def get_servico_nome(self, obj):
        try:
            banco = self.context.get('banco')
            from Produtos.models import Produtos
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.serv_codi
            ).first()
            return produto.prod_nome if produto else ''
        except Exception:
            return ''
