import pytest
from django.core.cache import cache
from django.test import RequestFactory

from pedidos.models import Pedido
from .views import OrdersJsonView


@pytest.mark.django_db
class TestOrdersJsonView:
    def setup_method(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_lista_pedidos_em_cache_miss(self):
        Pedido.objects.create(id='p1', cliente='Ana', total=10, status='processado')

        request = self.factory.get('/orders')
        response = OrdersJsonView.as_view()(request)

        assert response.status_code == 200
        assert b'p1' in response.content

    def test_segunda_chamada_usa_cache(self):
        Pedido.objects.create(id='p2', cliente='Bia', total=20, status='processado')
        request = self.factory.get('/orders')

        OrdersJsonView.as_view()(request)  # popula cache
        Pedido.objects.filter(id='p2').update(status='cancelado')
        response = OrdersJsonView.as_view()(request)  # deve vir do cache, sem refletir update

        assert b'"status": "processado"' in response.content
