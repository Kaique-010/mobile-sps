from rest_framework import serializers
from decimal import Decimal
from datetime import timedelta
from .models import ComissaoSps
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber

class ComissaoSpsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComissaoSps
        fields = '__all__'

    def get_percentual_categoria(self, codigo):
        return {
            '1': 5, '2': 5, '3': 20, '4': 20, '5': 5,
        }.get(codigo, 0)

    def calcular_campos(self, validated_data):
        valor_total = Decimal(str(validated_data.get('comi_valo_tota', 0)))
        impostos = Decimal(str(validated_data.get('comi_impo', 0)))
        categoria = validated_data.get('comi_cate')
        parcelas = validated_data.get('comi_parc', 1)
        perc = self.get_percentual_categoria(categoria)

        liquido = round((valor_total - impostos) * (Decimal('1') - Decimal('0.135')), 2)
        comissao_total = round(liquido * (Decimal(str(perc)) / Decimal('100')), 2)
        comissao_parcela = round(comissao_total / max(parcelas, 1), 2)

        validated_data['comi_perc'] = perc
        validated_data['comi_valo_liqu'] = liquido
        validated_data['comi_comi_tota'] = comissao_total
        validated_data['comi_comi_parc'] = comissao_parcela
        return validated_data

    def gerar_titulos(self, instancia, banco):
        data_base = instancia.comi_data_entr
        parcelas = instancia.comi_parc
        func = instancia.comi_func
        cliente = instancia.comi_clie_nome
        comissao_id = instancia.comi_id

        valor_parcela_receber = round(instancia.comi_valo_tota / max(parcelas, 1), 2)
        valor_parcela_pagar = instancia.comi_comi_parc

        # TÍTULOS A RECEBER DO CLIENTE
        for i in range(parcelas):
            Titulosreceber.objects.using(banco).create(
                titu_empr=instancia.comi_empr,
                titu_fili=instancia.comi_fili,
                titu_clie=cliente,
                titu_titu=comissao_id,
                titu_parc=i + 1,
                titu_seri='CMS',
                titu_valo=valor_parcela_receber,
                titu_data=data_base + timedelta(days=30 * i),
                titu_obse=f"Parcela {i+1}/{parcelas} - Recebimento por {instancia.comi_cate} - {cliente}"
            )

        # TÍTULOS A PAGAR PARA O FUNCIONÁRIO
        for i in range(parcelas):
            Titulospagar.objects.using(banco).create(
                titu_empr=instancia.comi_empr,
                titu_fili=instancia.comi_fili,
                titu_func=func,
                titu_titu=comissao_id,
                titu_parc=i + 1,
                titu_seri='CMS',
                titu_valo=valor_parcela_pagar,
                titu_data=data_base + timedelta(days=30 * i),
                titu_obse=f"Parcela {i+1}/{parcelas} - Comissão {instancia.comi_cate} - {func}"
            )

    def create(self, validated_data):
        banco = self.context.get('banco', 'default')
        validated_data = self.calcular_campos(validated_data)
        instancia = ComissaoSps.objects.using(banco).create(**validated_data)
        self.gerar_titulos(instancia, banco)
        return instancia

    def update(self, instance, validated_data):
        banco = self.context.get('banco', 'default')
        validated_data = self.calcular_campos(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
