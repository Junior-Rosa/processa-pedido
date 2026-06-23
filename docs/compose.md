# Docker Compose

## Subir o ambiente

```bash
# Dev — hot reload, runserver
make dev

# Prod — gunicorn
make prod
```

Aguarde o RabbitMQ ficar `healthy` (~30s). Verifique com:

```bash
docker compose ps
```

## Simular compras

```bash
# Via Makefile
make order

# Manualmente
curl -s -X POST http://localhost:5000/order \
  -H "Content-Type: application/json" \
  -d '{
    "cliente": "Maria",
    "itens": [
      {"produto": "Notebook", "qty": 1, "preco": 3500.00},
      {"produto": "Mouse",    "qty": 2, "preco": 89.90}
    ]
  }' | python3 -m json.tool

curl -s -X POST http://localhost:5000/order \
  -H "Content-Type: application/json" \
  -d '{"cliente":"João","itens":[{"produto":"Teclado","qty":1,"preco":250.00}]}'
```

**Resposta esperada:**
```json
{"order_id": "a1b2c3d4", "status": "queued"}
```

## Interfaces

| URL | Descrição |
|-----|-----------|
| http://localhost:5000/order | POST — criar pedido |
| http://localhost:5000/health | GET — healthcheck loja |
| http://localhost:3000/ | Painel de pedidos (auto-refresh 4s) |
| http://localhost:3000/orders | GET — JSON dos últimos 20 pedidos |
| http://localhost:15672 | RabbitMQ Management (guest/guest) |

## Checklist

- [ ] `POST /order` retorna `{order_id, status: "queued"}`
- [ ] Worker imprime `ACK: pedido XXXX processado`
- [ ] Painel `:3000` lista pedidos com status `processado`
- [ ] RabbitMQ `:15672` — fila `pedidos.queue` com 0 mensagens pendentes
- [ ] Teste NACK: `make order-nack` — worker imprime `NACK: qty inválida`

## Comandos de debug

```bash
# Logs em tempo real
make logs
make logs-worker

# Ver pedidos no banco
make db-status

# Shell psql
make db-shell

# Listar filas RabbitMQ
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers

# Django shell
make shell

# Parar tudo (mantém volume)
make down

# Parar e limpar DB
make down-v
```

## Dev vs Prod

| | Dev (`make dev`) | Prod (`make prod`) |
|---|---|---|
| Servidor | `runserver` (hot reload) | `gunicorn` (2 workers) |
| Volume | `.:/app` (código local montado) | Sem volume |
| DEBUG | True | False |
| Rebuild | Necessário só ao mudar deps | `docker compose up --build` |
