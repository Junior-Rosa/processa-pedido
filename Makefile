COMPOSE      = docker compose
COMPOSE_DEV  = docker compose -f docker-compose.yml -f docker-compose.dev.yml
CLUSTER      = processador-pedidos
NS           = processador-pedidos
IMAGE        = pedidos-app:v1

# ── Dev ───────────────────────────────────────────────────────────────────────
dev:
	$(COMPOSE_DEV) up --build

dev-d:
	$(COMPOSE_DEV) up --build -d

# ── Prod ──────────────────────────────────────────────────────────────────────
prod:
	$(COMPOSE) up --build -d

# ── Parar ─────────────────────────────────────────────────────────────────────
down:
	$(COMPOSE) down

down-v:
	$(COMPOSE) down -v

# ── Logs ──────────────────────────────────────────────────────────────────────
logs:
	$(COMPOSE) logs -f

logs-worker:
	$(COMPOSE) logs -f worker

logs-loja:
	$(COMPOSE) logs -f loja

# ── Django ────────────────────────────────────────────────────────────────────
migrate:
	$(COMPOSE) exec loja python manage.py migrate

shell:
	$(COMPOSE) exec loja python manage.py shell

# ── Banco ─────────────────────────────────────────────────────────────────────
db-shell:
	$(COMPOSE) exec db psql -U postgres -d pedidosdb

db-status:
	$(COMPOSE) exec db psql -U postgres -d pedidosdb \
	  -c "SELECT id, cliente, total, status FROM pedidos ORDER BY criado_em DESC;"

# ── Testes rápidos ────────────────────────────────────────────────────────────
order:
	curl -s -X POST http://localhost:5000/order \
	  -H "Content-Type: application/json" \
	  -d '{"cliente":"Teste","itens":[{"produto":"Notebook","qty":1,"preco":3500.00},{"produto":"Mouse","qty":2,"preco":89.90}]}' \
	  | python3 -m json.tool

order-nack:
	curl -s -X POST http://localhost:5000/order \
	  -H "Content-Type: application/json" \
	  -d '{"cliente":"Invalido","itens":[{"produto":"X","qty":-1,"preco":10}]}'

health:
	curl -s http://localhost:5000/health | python3 -m json.tool

# ── K8s — setup completo via Terraform ─────────────────────────────────────────
# Terraform agora é responsável pelo ciclo de vida do cluster k3d (create/destroy),
# build+import da imagem e aplicação declarativa de todos os manifests em k8s/.
infra-up:
	terraform -chdir=terraform init
	# 1ª apply cria cluster k3d + imagem (gera o contexto kubeconfig "k3d-$(CLUSTER)")
	# 2ª apply aplica os manifests — precisa do contexto já existente p/ o provider kubectl
	terraform -chdir=terraform apply -auto-approve -target=null_resource.k3d_cluster -target=null_resource.app_image
	terraform -chdir=terraform apply -auto-approve

infra-down:
	terraform -chdir=terraform destroy -auto-approve

infra-plan:
	terraform -chdir=terraform plan

k8s-up: infra-up
	kubectl get all -n $(NS)

# ── K8s — dia a dia ───────────────────────────────────────────────────────────
k8s-status:
	kubectl get all -n $(NS)

k8s-logs-worker:
	kubectl logs -l app=worker -n $(NS) --tail=20 -f

k8s-logs-loja:
	kubectl logs -l app=loja -n $(NS) --tail=20 -f

k8s-order:
	curl -s -X POST http://localhost:5000/order \
	  -H "Content-Type: application/json" \
	  -d '{"cliente":"Teste K8s","itens":[{"produto":"Cadeira","qty":1,"preco":890.00}]}' \
	  | python3 -m json.tool

k8s-order-nack:
	curl -s -X POST http://localhost:5000/order \
	  -H "Content-Type: application/json" \
	  -d '{"cliente":"Invalido","itens":[{"produto":"X","qty":-1,"preco":10}]}'

k8s-rabbitmq:
	kubectl port-forward svc/rabbitmq 15672:15672 -n $(NS)

k8s-scale-worker:
	kubectl scale deployment worker --replicas=2 -n $(NS)
	kubectl get pods -n $(NS) -l app=worker

# ── K8s — destruir ────────────────────────────────────────────────────────────
k8s-down: infra-down

.PHONY: dev dev-d prod down down-v logs logs-worker logs-loja \
        migrate shell db-shell db-status order order-nack health \
        infra-up infra-down infra-plan k8s-up \
        k8s-status k8s-logs-worker k8s-logs-loja k8s-order k8s-order-nack \
        k8s-rabbitmq k8s-scale-worker k8s-down
