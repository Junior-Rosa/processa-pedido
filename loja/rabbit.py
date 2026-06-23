import os
import json

import pika

RABBIT_HOST = os.environ.get('RABBIT_HOST', 'rabbitmq')
RABBIT_USER = os.environ.get('RABBIT_USER', 'guest')
RABBIT_PASS = os.environ.get('RABBIT_PASS', 'guest')


def publish_order(payload: dict) -> None:
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBIT_HOST, credentials=creds, heartbeat=60))
    ch = conn.channel()
    ch.exchange_declare(exchange='pedidos', exchange_type='direct', durable=True)
    ch.queue_declare(queue='pedidos.queue', durable=True)
    ch.queue_bind(queue='pedidos.queue', exchange='pedidos', routing_key='pedido')
    ch.basic_publish(
        exchange='pedidos',
        routing_key='pedido',
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )
    conn.close()
