from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from prometheus_client import Counter

from pedidos.models import Pedido

ORDERS_CACHE_KEY = 'orders_list'
ORDERS_CACHE_TTL = 3  # segundos — menor que o auto-refresh do painel (4s)

cache_hits_total = Counter('cache_hits_total', 'Acertos de cache no painel')
cache_misses_total = Counter('cache_misses_total', 'Faltas de cache no painel')


class IndexView(View):
    def get(self, request):
        pedidos = Pedido.objects.prefetch_related('itens').all()[:50]
        return render(request, 'painel/index.html', {'pedidos': pedidos})


class OrdersJsonView(View):
    def get(self, request):
        pedidos = cache.get(ORDERS_CACHE_KEY)
        if pedidos is not None:
            cache_hits_total.inc()
        else:
            cache_misses_total.inc()
            pedidos = list(
                Pedido.objects.values('id', 'cliente', 'total', 'status')
                .order_by('-criado_em')[:20]
            )
            for p in pedidos:
                p['total'] = float(p['total'])
            cache.set(ORDERS_CACHE_KEY, pedidos, ORDERS_CACHE_TTL)
        return JsonResponse(pedidos, safe=False)
