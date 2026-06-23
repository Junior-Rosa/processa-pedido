# Django — Notas do Projeto

## Por que Django em vez de Flask?

| | Flask | Django |
|---|---|---|
| ORM | Manual (psycopg2 raw SQL) | Built-in — modelos Python ↔ tabelas |
| Validação | Manual (dicts) | DRF Serializers com tipos e regras |
| Migrations | Script `init_db()` manual | `manage.py migrate` — versionado |
| Management commands | Não tem | `manage.py run_worker` — setup automático |
| Templates | f-strings com HTML | Sistema de templates com filtros |

## Estrutura do monorepo

```
Um projeto Django, três apps:

pedidos/   ← modelos compartilhados + worker command
loja/      ← app de entrada de pedidos (DRF)
painel/    ← app de visualização (templates)
```

Todos os serviços Docker usam **a mesma imagem** e **o mesmo projeto Django**.
O comando muda por serviço:

```yaml
loja:   gunicorn config.wsgi:application --bind 0.0.0.0:5000
worker: python manage.py run_worker
painel: gunicorn config.wsgi:application --bind 0.0.0.0:3000
```

## ORM vs psycopg2 direto

**Antes (Flask / psycopg2):**
```python
conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute("INSERT INTO pedidos (id, cliente, total, status) VALUES (%s,%s,%s,'processado')", ...)
conn.commit()
```

**Depois (Django ORM):**
```python
with transaction.atomic():
    pedido = Pedido.objects.create(id=order_id, cliente=cliente, total=total, status='processado')
    ItemPedido.objects.bulk_create([ItemPedido(pedido=pedido, ...) for item in itens])
```

Vantagens do ORM:
- `transaction.atomic()` garante rollback se qualquer INSERT falhar
- `bulk_create()` faz um único INSERT para todos os itens
- Sem SQL manual — sem risco de SQL injection
- Migrações versionadas no repositório

## DRF Serializers

```python
class ItemSerializer(serializers.Serializer):
    produto = serializers.CharField(max_length=100)
    qty     = serializers.IntegerField(min_value=1)   # já valida qty > 0
    preco   = serializers.DecimalField(max_digits=10, decimal_places=2)

class OrderSerializer(serializers.Serializer):
    cliente = serializers.CharField(max_length=100, default='anonimo')
    itens   = ItemSerializer(many=True)
```

Na view:
```python
serializer = OrderSerializer(data=request.data)
serializer.is_valid(raise_exception=True)  # retorna 400 automaticamente se inválido
```

## Management command — run_worker

Django gerencia o setup do ORM automaticamente quando se usa `BaseCommand`.
Não precisa de `django.setup()` manual:

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # aqui já pode usar Pedido.objects, transaction.atomic(), etc.
        while True:
            try:
                run()   # conecta pika e fica consumindo
            except Exception as e:
                time.sleep(5)  # reconecta em caso de queda do RabbitMQ
```

## Migrations — como funciona

```bash
# 1. Criar migration (já incluída no repo: pedidos/migrations/0001_initial.py)
python manage.py makemigrations

# 2. Aplicar ao banco (cria tabelas pedidos e itens_pedido)
python manage.py migrate

# No Docker: loja roda migrate no startup
# sh -c "python manage.py migrate --noinput && gunicorn ..."
```

A migration `0001_initial.py` cria:
- Tabela `pedidos` (`db_table = 'pedidos'`)
- Tabela `itens_pedido` (`db_table = 'itens_pedido'`)

Os nomes de tabela são explícitos via `Meta.db_table` para compatibilidade com o guia original.

## Rodar localmente sem Docker

```bash
# Instalar dependências com uv
uv sync

# Banco local (requer Postgres rodando localmente)
export DB_HOST=localhost POSTGRES_DB=pedidosdb POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres
export RABBIT_HOST=localhost

uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:5000   # loja

# Em outro terminal:
uv run python manage.py runserver 0.0.0.0:3000   # painel

# Em outro terminal:
uv run python manage.py run_worker                # worker
```

Ou com `uv run` individual para cada comando sem ativar o venv manualmente.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` | Módulo de settings |
| `DJANGO_SECRET_KEY` | `dev-secret-key-...` | Chave secreta (troque em produção!) |
| `DJANGO_DEBUG` | `False` | Ativa modo debug |
| `DB_HOST` | `db` | Host do Postgres |
| `POSTGRES_DB` | `pedidosdb` | Nome do banco |
| `POSTGRES_USER` | `postgres` | Usuário do banco |
| `POSTGRES_PASSWORD` | `postgres` | Senha do banco |
| `RABBIT_HOST` | `rabbitmq` | Host do RabbitMQ |
| `RABBIT_USER` | `guest` | Usuário RabbitMQ |
| `RABBIT_PASS` | `guest` | Senha RabbitMQ |
