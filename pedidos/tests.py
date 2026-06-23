import json
from unittest.mock import MagicMock

import pytest

from pedidos.management.commands.run_worker import processar
from pedidos.models import ItemPedido, Pedido


@pytest.mark.django_db
class TestPedidoModel:
    def test_criacao_pedido_com_itens(self):
        pedido = Pedido.objects.create(id='abc123', cliente='Ana', total=100, status='processado')
        ItemPedido.objects.create(pedido=pedido, produto='Caneca', qty=2, preco=50)

        assert Pedido.objects.count() == 1
        assert pedido.itens.count() == 1
        assert str(pedido) == 'abc123 — Ana (processado)'

    def test_status_default_pendente(self):
        pedido = Pedido.objects.create(id='xyz789', cliente='Bruno', total=10)
        assert pedido.status == 'pendente'


@pytest.mark.django_db
class TestProcessarWorker:
    def _mensagem(self, order_id='order-1', qty=1, preco=10.0):
        body = json.dumps({
            'order_id': order_id,
            'cliente': 'Cliente Teste',
            'itens': [{'produto': 'Produto X', 'qty': qty, 'preco': preco}],
        }).encode()
        ch = MagicMock()
        method = MagicMock(delivery_tag=1)
        return ch, method, body

    def test_ack_e_persiste_pedido_valido(self):
        ch, method, body = self._mensagem(order_id='order-ok', qty=2, preco=25.0)

        processar(ch, method, None, body)

        ch.basic_ack.assert_called_once_with(delivery_tag=1)
        ch.basic_nack.assert_not_called()
        pedido = Pedido.objects.get(id='order-ok')
        assert pedido.status == 'processado'
        assert pedido.total == 50.0
        assert pedido.itens.count() == 1

    def test_nack_sem_requeue_quando_qty_invalida(self):
        ch, method, body = self._mensagem(order_id='order-bad-qty', qty=0)

        processar(ch, method, None, body)

        ch.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
        ch.basic_ack.assert_not_called()
        assert not Pedido.objects.filter(id='order-bad-qty').exists()

    def test_nack_com_requeue_em_erro_inesperado(self):
        ch = MagicMock()
        method = MagicMock(delivery_tag=1)
        body = b'mensagem-invalida-nao-json'

        processar(ch, method, None, body)

        ch.basic_nack.assert_called_once_with(delivery_tag=1, requeue=True)
        ch.basic_ack.assert_not_called()
