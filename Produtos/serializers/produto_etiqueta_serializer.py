from rest_framework import serializers

class ProdutoEtiquetasSerializer(serializers.Serializer):
    produtos = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False
    )

    def validate_produtos(self, value):
        produtos = [p.strip() for p in value if p.strip()]
        if not produtos:
            raise serializers.ValidationError("Lista de produtos vazia.")
        return list(set(produtos))
