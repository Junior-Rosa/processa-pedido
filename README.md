# Processador de Pedidos

Sistema de processamento de pedidos com mensageria. Django monorepo rodando via Docker Compose ou Kubernetes (k3d), com infraestrutura provisionada por Terraform, testes automatizados em CI e observabilidade via Prometheus/Grafana.

## Arquitetura

```
[Cliente]  ──POST /order──▶  [loja :5000]  ──publish──▶  [RabbitMQ]
                                                               │
                                                          deliver
                                                               │
                                                          [worker]  ──/metrics:9100──▶ [Prometheus]
                                                               │
                                                    transaction.atomic()
                                                               │
                                                          [Postgres]
                                                               │
                                                            ACK()

[Usuário]  ──GET /──▶  [painel :3000]  ──cache?──▶  [Redis]
                              │ (miss)                  │
                              └────────SELECT──▶  [Postgres]

[Prometheus :9090] ──scrape──▶ loja:/metrics, painel:/metrics, worker:9100
[Grafana :3001/30004] ──query──▶ [Prometheus]
```

### Serviços

| Serviço    | Tecnologia            | Porta       | Função |
|------------|------------------------|-------------|--------|
| loja       | Django + DRF           | 5000        | Recebe pedidos via API REST, publica no RabbitMQ, expõe `/metrics` |
| rabbitmq   | RabbitMQ 3-management  | 15672       | Broker — exchange `pedidos`, fila `pedidos.queue` |
| db         | Postgres 15            | 5432        | Tabelas `pedidos` e `itens_pedido` |
| worker     | Django management cmd  | 9100        | Consome fila com ACK manual, insere no banco, expõe `/metrics` |
| painel     | Django templates       | 3000        | Visualiza pedidos (auto-refresh 4s), cacheado via Redis, expõe `/metrics` |
| redis      | Redis 7                | 6379        | Cache de leitura da lista de pedidos (TTL 3s) |
| prometheus | Prometheus             | 9090/30003  | Coleta métricas de loja/painel/worker (k8s) |
| grafana    | Grafana                | 3001/30004  | Dashboard de métricas (k8s) |

### Por que RabbitMQ?

RabbitMQ garante **at-least-once delivery** via ACK manual. O worker só confirma (ACK) a mensagem *após* o INSERT no banco ser bem-sucedido. Se o worker cair no meio do processamento, RabbitMQ reenfileira automaticamente — nenhum pedido é perdido.

### Monorepo Django

Um único projeto Django, três apps, uma imagem Docker. Cada serviço roda um comando diferente:

```
loja   → gunicorn config.wsgi:application --bind 0.0.0.0:5000
worker → python manage.py run_worker
painel → gunicorn config.wsgi:application --bind 0.0.0.0:3000
```

## Estrutura

```
.
├── config/              # settings, urls, wsgi (+ settings_test.py p/ CI)
├── pedidos/             # models (Pedido, ItemPedido) + management command run_worker + tests.py
├── loja/                # DRF: POST /order, GET /health + tests.py
├── painel/              # views (cache Redis) + template HTML com auto-refresh + tests.py
├── k8s/                 # manifests Kubernetes (1 recurso por arquivo)
├── terraform/           # IaC: cluster k3d, build/import de imagem, apply dos manifests
├── .github/workflows/   # CI: testes app, integração, terraform, lint k8s
├── docs/                # documentação detalhada + respostas.md
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
└── Makefile
```

## Pré-requisitos

- Docker + Docker Compose
- `make`
- Para K8s: `k3d` + `kubectl` + `terraform` (>=1.5)
- Para testes: `uv` (gerencia o venv Python automaticamente)

## Observabilidade

- **Métricas de negócio**: `pedidos_recebidos_total` (loja), `pedidos_processados_total`/`pedidos_processamento_falhas_total`/`pedidos_tempo_processamento_seconds` (worker), `cache_hits_total`/`cache_misses_total` (painel).
- **Métricas técnicas**: latência/contagem HTTP e queries de banco via `django-prometheus` (loja/painel).
- **Prometheus** coleta tudo via scrape estático (`k8s/prometheus-configmap.yaml`); **Grafana** vem com datasource e dashboard pré-provisionados (`k8s/grafana-*-configmap.yaml`) — sem clique manual.
- Justificativa completa das métricas escolhidas: [docs/respostas.md](docs/respostas.md#3).

## Testes e CI

```bash
uv sync          # instala deps (incl. pytest-django) em .venv
uv run pytest -v # 14 testes: serializer, OrderView, modelos, worker (ack/nack), cache do painel
```

Workflows em `.github/workflows/`: `app-tests.yml` (unitários), `app-integration.yml` (docker-compose ponta-a-ponta), `terraform-ci.yml` (fmt/validate/plan), `k8s-lint.yml` (kubeconform). Detalhes do que cada um garante: [docs/respostas.md](docs/respostas.md#2).

## Rodando com Docker Compose

```bash
# Dev — hot reload, código local montado em /app
make dev

# Prod — gunicorn
make prod
```

Aguardar ~30s para RabbitMQ ficar healthy. Verificar:

```bash
docker compose ps
```

### Testar

```bash
make order        # envia pedido válido → {"order_id": "...", "status": "queued"}
make order-nack   # envia qty=-1 → worker imprime NACK
make health       # GET /health → {"status": "ok"}
make db-status    # lista pedidos no banco
make logs-worker  # acompanhar ACK/NACK em tempo real
```

### Interfaces

| URL | Descrição |
|-----|-----------|
| http://localhost:5000/order | POST — criar pedido |
| http://localhost:3000 | Painel de pedidos |
| http://localhost:15672 | RabbitMQ Management (guest/guest) |

## Rodando no Kubernetes (k3d) via Terraform

Terraform é responsável por criar/destruir o cluster k3d, buildar+importar a imagem e aplicar todos os manifests em `k8s/` (ver [terraform/](terraform/) e [docs/respostas.md](docs/respostas.md#1)).

```bash
# Cluster + imagem + todos os manifests (db, rabbitmq, redis, loja, painel, worker, prometheus, grafana)
make infra-up      # == terraform -chdir=terraform init && apply

# Aguardar pods ficarem Running
make k8s-status

# Testar
make k8s-order
make k8s-order-nack
make k8s-logs-worker

# Acessar RabbitMQ
make k8s-rabbitmq   # port-forward → http://localhost:15672

# Acessar Prometheus / Grafana
open http://localhost:9090   # Prometheus
open http://localhost:3001   # Grafana (dashboard "Processador de Pedidos" pré-provisionado)

# Escalar worker
make k8s-scale-worker

# Destruir tudo
make infra-down     # == terraform destroy (cluster k3d incluído)
```

## API

### `POST /order`

```json
{
  "cliente": "Maria",
  "itens": [
    {"produto": "Notebook", "qty": 1, "preco": 3500.00},
    {"produto": "Mouse",    "qty": 2, "preco": 89.90}
  ]
}
```

**Resposta:**
```json
{"order_id": "a1b2c3d4", "status": "queued"}
```

### `GET /health`
```json
{"status": "ok"}
```

### `GET /orders`
JSON dos últimos 20 pedidos.

## Comandos úteis

Ver [docs/makefile.md](docs/makefile.md) para referência completa de todos os comandos `make`.

| Comando | Descrição |
|---------|-----------|
| `make dev` / `make prod` | Subir ambiente |
| `make down` / `make down-v` | Parar (com ou sem apagar banco) |
| `make shell` | Django shell interativo |
| `make db-shell` | psql interativo |
| `make infra-up` | Cluster k3d + imagem + manifests via Terraform |
| `make infra-down` | Destruir cluster via Terraform |

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [docs/arquitetura.md](docs/arquitetura.md) | Fluxo detalhado, diagrama ASCII, modelos do banco |
| [docs/compose.md](docs/compose.md) | Docker Compose — subir, testar, debug |
| [docs/kubernetes.md](docs/kubernetes.md) | K8s — cluster, deploy, scale, checklist |
| [docs/django.md](docs/django.md) | ORM vs psycopg2, DRF, management commands, migrations |
| [docs/makefile.md](docs/makefile.md) | Referência de todos os comandos `make` |
| [docs/respostas.md](docs/respostas.md) | Respostas às 5 perguntas desta etapa (Terraform, CI, métricas, falhas, melhorias) |
