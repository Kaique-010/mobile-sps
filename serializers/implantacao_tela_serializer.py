from rest_framework import serializers
from .models import ImplantacaoTela

class ImplantacaoTelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImplantacaoTela
        fields = '__all__'

    def validate(self, data):
        modulos = data.get('modulos', [])
        telas = data.get('telas', [])

        # Validar módulos escolhidos
        modulo_valido = all(modulo in dict(ImplantacaoTela.MODULOS_CHOICES).keys() for modulo in modulos)
        if not modulo_valido:
            raise serializers.ValidationError("Um ou mais módulos são inválidos.")

        # Validar telas
        telas_validas = []
        for modulo in modulos:
            telas_validas += ImplantacaoTela.TELAS_POR_MODULO.get(modulo, [])

        tela_valida = all(tela in telas_validas for tela in telas)
        if not tela_valida:
            raise serializers.ValidationError("Uma ou mais telas são inválidas para os módulos selecionados.")

        return data