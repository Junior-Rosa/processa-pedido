# Referência dos comandos Make

## Docker Compose — Dev

| Comando | O que faz |
|---------|-----------|
| `make dev` | Sobe todos os serviços com hot reload (runserver + volumes montados). Rebuild automático. |
| `make dev-d` | Mesmo que `dev`, mas em background (detached). |

**Diferença dev vs prod:** dev usa `runserver` do Django (hot reload, sem gunicorn) e monta o código local em `/app` via volume — qualquer alteração no código reflete sem rebuild.

---

## Docker Compose — Prod

| Comando | O que faz |
|---------|-----------|
| `make prod` | Sobe todos os serviços com gunicorn (2 workers). Rebuild da imagem. Roda em background. |

---

## Parar / Limpar

| Comando | O que faz |
|---------|-----------|
| `make down` | Para e remove containers. Mantém volumes (dados do banco preservados). |
| `make down-v` | Para e remove containers **e volumes**. Apaga o banco. Use para reset completo. |

---

## Logs

| Comando | O que faz |
|---------|-----------|
| `make logs` | Segue logs de todos os serviços em tempo real. |
| `make logs-worker` | Segue logs só do worker (ACK/NACK, erros de processamento). |
| `make logs-loja` | Segue logs só da loja (requests recebidos, erros de publicação). |

---

## Django

| Comando | O que faz |
|---------|-----------|
| `make migrate` | Roda `python manage.py migrate` dentro do container loja. Cria/atualiza tabelas. |
| `make shell` | Abre Django shell interativo (`python manage.py shell`) no container loja. Útil para queries manuais via ORM. |

---

## Banco de dados

| Comando | O que faz |
|---------|-----------|
| `make db-shell` | Abre `psql` interativo no container do Postgres. |
| `make db-status` | Lista todos os pedidos (id, cliente, total, status) ordenados por data. |

---

## Testes rápidos (Compose)

| Comando | O que faz |
|---------|-----------|
| `make order` | Envia pedido válido (Notebook + Mouse). Imprime resposta JSON formatada. Espera `{"order_id": "...", "status": "queued"}`. |
| `make order-nack` | Envia pedido com `qty: -1` (inválido). Worker deve imprimir `NACK: qty inválida`. Mensagem descartada (requeue=False). |
| `make health` | GET em `/health`. Resposta esperada: `{"status": "ok"}`. |

### Testar NACK (Compose)
```bash
make order-nack
make logs-worker   # deve mostrar: NACK: qty inválida em XXXX
```
Verificar no RabbitMQ (http://localhost:15672) que mensagem foi descartada — fila `pedidos.queue` com 0 mensagens.

---

## Kubernetes — Setup

| Comando | O que faz |
|---------|-----------|
| `make k8s-cluster` | Cria cluster k3d com 1 server + 2 agents. Mapeia portas 5000→30000 e 3000→30001. Merge kubeconfig. Cria namespace. |
| `make k8s-build` | Builda imagem Docker `pedidos-app:v1` e importa para o cluster k3d. |
| `make k8s-deploy` | Aplica todos os manifests em `k8s/`. Lista recursos no namespace. |
| `make k8s-up` | **Fluxo completo:** `k8s-cluster` → `k8s-build` → `k8s-deploy`. Use para criar tudo do zero. |

**Ordem correta do zero:**
```bash
make k8s-up
# aguardar pods ficarem Running (~2 min)
make k8s-status
make k8s-order
```

---

## Kubernetes — Dia a dia

| Comando | O que faz |
|---------|-----------|
| `make k8s-status` | Lista pods, services e deployments no namespace. |
| `make k8s-logs-worker` | Segue últimas 20 linhas dos logs do worker (ACK/NACK). |
| `make k8s-logs-loja` | Segue últimas 20 linhas dos logs da loja. |
| `make k8s-order` | Envia pedido de teste para o cluster K8s (mesma porta 5000 via k3d loadbalancer). |
| `make k8s-order-nack` | Envia pedido inválido (`qty: -1`) para testar NACK no K8s. |
| `make k8s-scale-worker` | Escala o worker para 2 réplicas. Demonstra processamento paralelo. |

### Testar NACK (K8s)
```bash
make k8s-order-nack
make k8s-logs-worker   # deve mostrar: NACK: qty inválida em XXXX
```

---

## Kubernetes — Destruir

| Comando | O que faz |
|---------|-----------|
| `make k8s-down` | Deleta o cluster k3d inteiro (namespace, pods, volumes, tudo). |

---

## Fluxos completos

### Desenvolvimento local
```bash
make dev          # subir
make order        # testar pedido
make logs-worker  # ver ACK
make db-status    # ver no banco
make down         # parar
```

### Kubernetes do zero
```bash
make k8s-up           # criar cluster + build + deploy
make k8s-status       # aguardar todos Running
make k8s-order        # testar pedido válido
make k8s-order-nack   # testar NACK
make k8s-logs-worker  # ver logs
make k8s-scale-worker # escalar worker
make k8s-down         # destruir tudo
```
