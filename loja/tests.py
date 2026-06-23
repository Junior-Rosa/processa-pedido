from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from .serializers import OrderSerializer
from .views import OrderView


class TestOrderSerializer:
    def test_valid_payload(self):
        data = {
            'cliente': 'Maria',
            'itens': [{'produto': 'Mouse', 'qty': 2, 'preco': '89.90'}],
        }
        serializer = OrderSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_itens_vazio_invalido(self):
        data = {'cliente': 'Maria', 'itens': []}
        serializer = OrderSerializer(data=data)
        assert not serializer.is_valid()
        assert 'itens' in serializer.errors

    def test_qty_minima_invalida(self):
        data = {
            'cliente': 'Maria',
            'itens': [{'produto': 'Mouse', 'qty': 0, 'preco': '10.00'}],
        }
        serializer = OrderSerializer(data=data)
        assert not serializer.is_valid()

    def test_cliente_default_anonimo(self):
        data = {'itens': [{'produto': 'Mouse', 'qty': 1, 'preco': '10.00'}]}
        serializer = OrderSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['cliente'] == 'anonimo'


@pytest.mark.django_db
class TestOrderView:
    def setup_method(self):
        self.factory = APIRequestFactory()

    @patch('loja.views.publish_order')
    def test_post_publica_pedido_valido(self, mock_publish):
        payload = {
            'cliente': 'Joao',
            'itens': [{'produto': 'Teclado', 'qty': 1, 'preco': '199.90'}],
        }
        request = self.factory.post('/order', payload, format='json')
        response = OrderView.as_view()(request)

        assert response.status_code == 201
        assert response.data['status'] == 'queued'
        mock_publish.assert_called_once()

    @patch('loja.views.publish_order')
    def test_post_rejeita_payload_invalido(self, mock_publish):
        request = self.factory.post('/order', {'cliente': 'Joao', 'itens': []}, format='json')
        response = OrderView.as_view()(request)

        assert response.status_code == 400
        mock_publish.assert_not_called()

    @patch('loja.views.publish_order', side_effect=Exception('rabbitmq indisponível'))
    def test_post_retorna_500_quando_publish_falha(self, mock_publish):
        payload = {
            'cliente': 'Joao',
            'itens': [{'produto': 'Teclado', 'qty': 1, 'preco': '199.90'}],
        }
        request = self.factory.post('/order', payload, format='json')
        response = OrderView.as_view()(request)

        assert response.status_code == 500
