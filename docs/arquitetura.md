# Arquitetura da Aplicação

Sistema de processamento de pedidos com RabbitMQ como broker de mensagens e ACK/NACK manual.

## Os 5 serviços

| Serviço   | Tecnologia              | Porta  | Função |
|-----------|-------------------------|--------|--------|
| loja      | Django + DRF            | 5000   | Recebe `POST /order`, publica no RabbitMQ |
| rabbitmq  | RabbitMQ 3-management   | 15672  | Broker — exchange `pedidos`, fila `pedidos.queue` |
| db        | Postgres 15             | 5432   | Tabelas `pedidos` e `itens_pedido` |
| worker    | Django management cmd   | —      | Consome `pedidos.queue` com ACK manual, insere no Postgres |
| painel    | Django templates        | 3000   | Lista pedidos com auto-refresh |

## Fluxo completo

```
SIMULAÇÃO DE COMPRA
──────────────────────────────────────────────────────
[Cliente]  ──POST /order {cliente, itens[]}──▶  [loja Django]
                                                     │
                                    gera order_id = uuid[:8]
                                                     │
                              DRF valida → publish_order()
                                       [RabbitMQ]
                                                     │
                              ◀── {order_id, status: "queued"}

PROCESSAMENTO COM ACK MANUAL
──────────────────────────────────────────────────────
[RabbitMQ]  ──deliver──▶  [worker — manage.py run_worker]
                                     │
                         valida estoque (qty > 0)
                                     │
                    ┌────────────────┴────────────────┐
                 válido                           inválido
                    │                                 │
       transaction.atomic():               NACK → requeue=False
         Pedido.objects.create()          (mensagem descartada)
         ItemPedido.objects.bulk_create()
                    │
                  ACK()  ← só após commit bem-sucedido
                    │
             [RabbitMQ] remove da fila

PAINEL
──────────────────────────────────────────────────────
[Usuário]  ──GET /──▶  [painel Django :3000]
                                │
             Pedido.objects.prefetch_related('itens').all()[:50]
                           [Postgres]
```

## Monorepo Django — uma imagem, três serviços

O projeto usa **um único projeto Django** com três apps. Docker Compose constrói **uma imagem**
e a executa com comandos diferentes:

| Serviço | Command no Compose |
|---------|-------------------|
| loja    | `python manage.py migrate && gunicorn ... --bind 0.0.0.0:5000` |
| worker  | `python manage.py run_worker` |
| painel  | `gunicorn ... --bind 0.0.0.0:3000` |

## Redis List vs RabbitMQ

| | Redis List | RabbitMQ |
|---|---|---|
| ACK nativo | Não — BLPOP remove imediatamente | Sim — `basic_ack` explícito |
| Perda em crash | Mensagem perdida após BLPOP | Reentrega automática (unacked → requeue) |
| Roteamento | Simples (LPUSH/BLPOP) | Exchange → binding → queue (flexível) |
| Caso de uso | Filas simples, perda tolerável | Pedidos, pagamentos, onde perda é inaceitável |

## Banco de dados

```sql
-- Criadas via Django migrations (python manage.py migrate)

CREATE TABLE pedidos (
    id          VARCHAR(36) PRIMARY KEY,
    cliente     VARCHAR(100) NOT NULL,
    total       NUMERIC(10,2) DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'pendente',
    criado_em   TIMESTAMP WITH TIME ZONE
);

CREATE TABLE itens_pedido (
    id          BIGSERIAL PRIMARY KEY,
    pedido_id   VARCHAR(36) REFERENCES pedidos(id),
    produto     VARCHAR(100) NOT NULL,
    qty         INTEGER NOT NULL,
    preco       NUMERIC(10,2) NOT NULL
);
```
