from rest_framework import serializers


class ItemSerializer(serializers.Serializer):
    produto = serializers.CharField(max_length=100)
    qty = serializers.IntegerField(min_value=1)
    preco = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderSerializer(serializers.Serializer):
    cliente = serializers.CharField(max_length=100, default='anonimo')
    itens = ItemSerializer(many=True)

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError('itens não pode ser vazio')
        return value
