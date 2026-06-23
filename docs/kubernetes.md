# Kubernetes / k3d

## Criar o cluster

```bash
k3d cluster create processador-pedidos \
  --servers 1 --agents 2 \
  --port "5000:30000@loadbalancer" \
  --port "3000:30001@loadbalancer"

kubectl create namespace processador-pedidos
```

## Build e importar a imagem

```bash
# Uma imagem para todos os serviços
make k8s-build

# Ou manualmente:
docker build -t pedidos-app:v1 .
k3d image import pedidos-app:v1 -c processador-pedidos
```

## Aplicar os manifests

```bash
# Tudo de uma vez
make k8s-up

# Ou por ordem:
kubectl apply -f k8s/db-secret.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl wait --for=condition=ready pod -l app=db -n processador-pedidos --timeout=90s

kubectl apply -f k8s/rabbitmq-deployment.yaml
kubectl wait --for=condition=ready pod -l app=rabbitmq -n processador-pedidos --timeout=120s

kubectl apply -f k8s/loja-deployment.yaml
kubectl apply -f k8s/painel-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
```

## Verificação

```bash
kubectl get all -n processador-pedidos

# Criar pedido
curl -s -X POST http://localhost:5000/order \
  -H "Content-Type: application/json" \
  -d '{"cliente":"Teste K8s","itens":[{"produto":"Cadeira","qty":1,"preco":890.00}]}'

# Acompanhar worker
make k8s-logs-worker
```

## Checklist K8s

- [ ] 5 pods Running: `db`, `rabbitmq`, `loja×2`, `worker`, `painel`
- [ ] Loja responde em **localhost:5000**
- [ ] Painel em **localhost:3000** exibe pedidos processados
- [ ] Worker tem `livenessProbe` configurado — sem Service exposto
- [ ] Secret `db-secret` contém credenciais separadas do código
- [ ] `loja` rodou `migrate` no startup — tabelas criadas

## Escalar o worker

```bash
kubectl scale deployment worker --replicas=2 -n processador-pedidos
kubectl get pods -n processador-pedidos -l app=worker
```

## Destruir o cluster

```bash
make k8s-down
k3d cluster delete processador-pedidos
```

## Diferenças vs Docker Compose

| | Compose | Kubernetes |
|---|---|---|
| Imagem | 1 por serviço (build: .) | 1 imagem `pedidos-app:v1` importada |
| Credenciais | Env vars inline no compose | Secret `db-secret` (secretRef) |
| Persistência | Named volume `db_data` | PersistentVolumeClaim `db-pvc` (1Gi) |
| Health | `healthcheck:` | `readinessProbe` + `livenessProbe` |
| Escala | `docker compose up --scale` | `kubectl scale deployment` |
