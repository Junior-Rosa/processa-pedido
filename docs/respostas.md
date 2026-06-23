# Respostas — Evolução DevOps do processador de pedidos

## 1. Qual parte da sua solução passou a ser responsabilidade do Terraform e por quê?

O Terraform (`terraform/`) passou a ser responsável por **todo o ciclo de vida da infraestrutura local**:

- **Criação e destruição do cluster k3d** (`cluster.tf`) — antes feito manualmente via `k3d cluster create`/`delete` no Makefile.
- **Build e import da imagem Docker no cluster** (`image.tf`), com `triggers` baseados em hash do `Dockerfile`/`pyproject.toml`, garantindo rebuild só quando necessário.
- **Aplicação declarativa de todos os manifests Kubernetes** (`manifests.tf`), via `for_each` sobre os arquivos em `k8s/` (cada arquivo contém um único recurso, para o provider `kubectl_manifest` aplicar 1:1 sem parsing de YAML multi-documento).

Por quê: isso elimina a sequência manual de passos do Makefile (`k8s-cluster` → `k8s-build` → `k8s-deploy`), tornando o ambiente **reprodutível** com um único `terraform apply` — qualquer pessoa (ou pipeline) recria exatamente o mesmo cluster, mesma imagem, mesmos recursos, sem depender de memória de "quais comandos rodar em qual ordem". Também versiona a infraestrutura junto do código-fonte, e o `terraform destroy` garante limpeza simétrica do ambiente.

O que **não** foi para o Terraform: a definição dos recursos k8s em si continua em YAML puro (não convertida para HCL) — decisão deliberada para manter a infraestrutura mínima e não duplicar/reescrever manifests já existentes; o Terraform orquestra o *quando* e *como aplicar*, não o *o quê*.

## 2. Quais validações foram automatizadas no GitHub Actions e quais testes foram criados para a aplicação e o que eles garantem?

Quatro workflows, cada um cobrindo uma camada diferente:

- **`app-tests.yml`** — testes unitários (`pytest-django`) contra SQLite em memória e cache local (sem dependências externas reais):
  - `loja/tests.py`: validação do `OrderSerializer` (payload válido, itens vazios, qty inválida, cliente default) e do `OrderView.post` com `publish_order` mockado (garante que pedido válido publica e retorna 201, payload invalido retorna 400 sem publicar, e falha do RabbitMQ retorna 500).
  - `pedidos/tests.py`: modelos `Pedido`/`ItemPedido`, e a função `processar` do worker com canal pika mockado — cobre os 3 caminhos críticos: ACK + persistência em pedido válido, NACK sem requeue em qty inválida, NACK com requeue em erro inesperado (mensagem malformada).
  - `painel/tests.py`: `OrdersJsonView` com cache Redis — cache miss popula e cache hit não reflete updates dentro do TTL.

  Isso garante que a regra de negócio central (validação de pedido + decisão de ACK/NACK, que é o que evita perda ou duplicação de pedidos) não regride silenciosamente.

- **`app-integration.yml`** — sobe a stack completa via `docker compose`, faz `POST /order` real, espera o worker processar, e confirma via `GET /orders` que o pedido apareceu. Garante que a integração real entre os serviços (loja → RabbitMQ → worker → Postgres → painel) funciona de ponta a ponta, algo que mocks não cobrem.

- **`terraform-ci.yml`** — `terraform fmt -check`, `validate` e `plan` (best-effort, sem cluster real no runner). Garante que a IaC está sintaticamente correta e que o grafo de dependências resolve antes de qualquer `apply` real.

- **`k8s-lint.yml`** — `kubeconform` validando todos os manifests em `k8s/` contra o schema oficial do Kubernetes. Garante que nenhum YAML malformado ou com campo inválido chegue a ser aplicado no cluster.

## 3. Quais métricas foram escolhidas e por que elas são relevantes para o tema da aplicação? Como o dashboard no Grafana ajuda a entender o comportamento do sistema?

Métricas customizadas (via `prometheus_client`/`django-prometheus`):

- `pedidos_recebidos_total` (loja) — volume de demanda chegando no sistema.
- `pedidos_processados_total` / `pedidos_processamento_falhas_total` (worker) — saúde do processamento: quantos pedidos completam com sucesso vs. falham (qty inválida, erro de banco, etc).
- `pedidos_tempo_processamento_seconds` (histogram, worker) — latência de processamento, indicador de SLA/gargalo.
- `cache_hits_total` / `cache_misses_total` (painel) — eficiência do cache Redis.
- Métricas padrão do `django-prometheus` (latência e contagem de requisições HTTP por view, queries de banco) em `loja` e `painel`.

Por que são relevantes: o tema da aplicação é **processamento de pedidos**, então as métricas de negócio (recebidos/processados/falhos/latência) medem diretamente se o sistema está cumprindo sua função — não apenas "o processo está de pé", mas "pedidos estão sendo processados corretamente e dentro de um tempo aceitável". Métricas técnicas (HTTP, cache) complementam mostrando onde um problema de negócio se origina (ex.: lentidão na API vs. lentidão no worker).

Grafana ajuda porque transforma essas séries temporais isoladas em **painéis correlacionados** (`k8s/grafana-dashboard-json-configmap.yaml`): throughput recebido vs. processado lado a lado revela se o worker está acumulando atraso; a taxa de falhas isolada revela picos de erro que um log entre milhares passaria despercebido; a latência p95 mostra degradação de performance antes que vire reclamação de usuário; o hit ratio do cache mostra se o Redis está realmente sendo útil. Sem o dashboard, essas correlações exigiriam grep manual em logs de serviços diferentes.

## 4. Se sua aplicação falhar em produção, quais sinais observáveis ajudariam a identificar a causa?

- **`pedidos_processamento_falhas_total` subindo** — problema na lógica de validação ou no banco (worker rejeitando mensagens).
- **`pedidos_processados_total` parado, mas `pedidos_recebidos_total` continuando a subir** — worker travado ou desconectado do RabbitMQ; fila acumulando (visível também na management UI do RabbitMQ, porta 15672).
- **Restarts/CrashLoopBackOff em `kubectl get pods`** — liveness probe falhando (worker sem conexão pika, ou loja/painel sem responder `/health`).
- **Spike de latência ou erro 5xx em `loja`/`painel`** (métricas padrão do `django-prometheus`) — sobrecarga, conexão com Postgres lenta/indisponível.
- **Queda no `cache_hits_total` / aumento de `cache_misses_total`** — Redis indisponível, o que joga carga extra no Postgres (efeito em cascata observável nas métricas de DB do `django-prometheus`).
- **Logs do worker** (`print` de ACK/NACK/erro) correlacionados com o horário do pico nas métricas — para a causa raiz exata (ex.: qual exceção disparou o NACK com requeue).

## 5. Que melhorias futuras você faria no pipeline ou na infraestrutura?

- **Alertmanager** com regras sobre as métricas já coletadas (ex.: alertar se `pedidos_processamento_falhas_total` crescer acima de X/min), em vez de depender de olhar o dashboard manualmente.
- **Tracing distribuído** (OpenTelemetry) para rastrear um pedido específico através de loja → RabbitMQ → worker → Postgres.
- **Agregação de logs** (Loki ou equivalente) em vez de `print()`/stdout cru, permitindo correlacionar logs com métricas no próprio Grafana.
- **E2E real em CI**: usar `AbsaOSS/k3d-action` para criar um cluster efêmero no runner e rodar `terraform apply` de verdade (hoje o `terraform-ci.yml` só faz `plan` best-effort) — evitado nesta etapa para não introduzir flakiness antes de o pipeline básico estar estável.
- **GitOps** (ArgoCD/Flux) substituindo `terraform apply` manual por reconciliação contínua a partir do repositório.
- **Terraform remote state + workspaces** para suportar múltiplos ambientes (dev/staging/prod) em vez do state local atual.
- **Secrets**: mover de `kind: Secret` em texto claro (`db-secret.yaml`) para Sealed Secrets ou Vault.
