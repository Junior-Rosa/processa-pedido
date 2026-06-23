import os
import time
import json

import pika
from django.core.management.base import BaseCommand
from django.db import transaction
from prometheus_client import Counter, Histogram, start_http_server

from pedidos.models import Pedido, ItemPedido

RABBIT_HOST = os.environ.get('RABBIT_HOST', 'rabbitmq')
RABBIT_USER = os.environ.get('RABBIT_USER', 'guest')
RABBIT_PASS = os.environ.get('RABBIT_PASS', 'guest')
METRICS_PORT = int(os.environ.get('METRICS_PORT', 9100))

pedidos_processados_total = Counter(
    'pedidos_processados_total', 'Total de pedidos processados com sucesso'
)
pedidos_processamento_falhas_total = Counter(
    'pedidos_processamento_falhas_total', 'Total de pedidos que falharam no processamento'
)
pedidos_tempo_processamento_seconds = Histogram(
    'pedidos_tempo_processamento_seconds', 'Tempo de processamento de um pedido'
)


def processar(ch, method, properties, body):
    with pedidos_tempo_processamento_seconds.time():
        try:
            data = json.loads(body)
            order_id = data['order_id']
            cliente = data['cliente']
            itens = data['itens']

            for item in itens:
                if int(item.get('qty', 0)) <= 0:
                    print(f"NACK: qty inválida em {order_id}")
                    pedidos_processamento_falhas_total.inc()
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return

            total = sum(float(i.get('preco', 0)) * int(i.get('qty', 1)) for i in itens)

            with transaction.atomic():
                pedido = Pedido.objects.create(
                    id=order_id,
                    cliente=cliente,
                    total=total,
                    status='processado',
                )
                ItemPedido.objects.bulk_create([
                    ItemPedido(
                        pedido=pedido,
                        produto=item['produto'],
                        qty=item['qty'],
                        preco=item['preco'],
                    )
                    for item in itens
                ])

            # ACK somente após INSERT bem-sucedido
            ch.basic_ack(delivery_tag=method.delivery_tag)
            pedidos_processados_total.inc()
            print(f"ACK: pedido {order_id} processado. Total: R${total:.2f}")

        except Exception as e:
            print(f"Erro: {e}")
            pedidos_processamento_falhas_total.inc()
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def run():
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBIT_HOST, credentials=creds, heartbeat=60))
    ch = conn.channel()
    ch.exchange_declare(exchange='pedidos', exchange_type='direct', durable=True)
    ch.queue_declare(queue='pedidos.queue', durable=True)
    ch.queue_bind(queue='pedidos.queue', exchange='pedidos', routing_key='pedido')
    ch.basic_qos(prefetch_count=1)  # fair dispatch — processa um por vez
    ch.basic_consume(queue='pedidos.queue', on_message_callback=processar)
    print('Worker aguardando pedidos...')
    ch.start_consuming()


class Command(BaseCommand):
    help = 'Consume pedidos.queue do RabbitMQ com ACK manual'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando worker...')
        start_http_server(METRICS_PORT)  # uma única vez — evita re-bind em reconexões
        while True:
            try:
                run()
            except Exception as e:
                self.stderr.write(f'Reconectando: {e}')
                time.sleep(5)
