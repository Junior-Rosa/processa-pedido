from django.db import models


class Pedido(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    cliente = models.CharField(max_length=100)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pedidos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.id} — {self.cliente} ({self.status})'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.CharField(max_length=100)
    qty = models.IntegerField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'itens_pedido'

    def __str__(self):
        return f'{self.produto} x{self.qty}'
