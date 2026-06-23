import uuid

from prometheus_client import Counter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .rabbit import publish_order
from .serializers import OrderSerializer

pedidos_recebidos_total = Counter(
    'pedidos_recebidos_total', 'Total de pedidos recebidos pela loja'
)


class OrderView(APIView):
    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedidos_recebidos_total.inc()

        order_id = str(uuid.uuid4())[:8]
        payload = {
            'order_id': order_id,
            'cliente': serializer.validated_data['cliente'],
            'itens': [
                {
                    'produto': item['produto'],
                    'qty': item['qty'],
                    'preco': str(item['preco']),
                }
                for item in serializer.validated_data['itens']
            ],
        }

        try:
            publish_order(payload)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'order_id': order_id, 'status': 'queued'}, status=status.HTTP_201_CREATED)


class HealthView(APIView):
    def get(self, request):
        return Response({'status': 'ok'})
