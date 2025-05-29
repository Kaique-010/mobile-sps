from rest_framework import serializers
from .models import Caixageral, Movicaixa

class CaixageralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caixageral
        fields = [
            'caix_empr',
            'caix_fili',
            'caix_caix',
            'caix_data',
            'caix_hora',
            'caix_aber',
            'caix_oper',
            'caix_ecf',
            'caix_orig',
            'caix_valo',
            'caix_ctrl',
            'field_log_data',
            'field_log_time',
            'caix_fech_data',
            'caix_fech_hora',
            'caix_obse_fech',
        ]
        read_only_fields = ['caix_empr']  # Chave primária, evita alteração no update
    
    def validate(self, data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")
        
        erros = {}
        obrigatorios = ['caix_empr', 'caix_fili', 'caix_caix', 'caix_data', 'caix_aber', 'caix_oper']
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Campo obrigatório.']

        if erros:
            raise serializers.ValidationError(erros)
        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        return Caixageral.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('caix_empr', None)
        return super().update(instance, validated_data)


class MovicaixaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movicaixa
        fields = [
            'movi_empr',
            'movi_fili',
            'movi_caix',
            'movi_data',
            'movi_ctrl',
            'movi_entr',
            'movi_said',
            'movi_tipo',
            'movi_obse',
            'movi_oper',
            'movi_hora',
            'movi_nume_vend',
            'movi_clie',
            'movi_vend',
            'movi_cont',
            'movi_even',
            'movi_cecu',
            'movi_cheq',
            'movi_nomi',
            'movi_bomp',
            'movi_titu',
            'movi_seri',
            'movi_parc',
            'movi_cheq_banc',
            'movi_cheq_agen',
            'movi_cheq_cont',
            'movi_seri_nota',
            'movi_nume_nota',
            'movi_coo',
            'movi_seri_ecf',
            'movi_codi_admi',
            'movi_tipo_movi',
            'movi_banc_tran',
            'movi_sequ_tran',
            'movi_sang',
            'movi_vend_orig',
            'movi_docu_fisc',
            'movi_bare_ctrl',
        ]
        read_only_fields = ['movi_empr']  # Chave primária
    
    def validate(self, data):
        banco = self.context.get('banco')
        if not banco:
            raise serializers.ValidationError("Banco não encontrado")

        obrigatorios = ['movi_empr', 'movi_fili', 'movi_caix', 'movi_data', 'movi_ctrl']
        erros = {}
        for campo in obrigatorios:
            if not data.get(campo):
                erros[campo] = ['Campo obrigatório.']

        if erros:
            raise serializers.ValidationError(erros)

        return data

    def create(self, validated_data):
        banco = self.context.get('banco')
        return Movicaixa.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('movi_empr', None)
        return super().update(instance, validated_data)
