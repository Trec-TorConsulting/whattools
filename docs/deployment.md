# WhatTools Deployment Guide

## Prerequisites

- K3S cluster with Traefik ingress controller
- `kubectl` configured to access the cluster
- Docker registry accessible from the cluster
- Domain `whattools.trector.com` pointing to the cluster's ingress IP
- cert-manager with `letsencrypt-prod` ClusterIssuer (for TLS)

## Local Development

### Quick Start

```bash
# Clone and set up
git clone <repo-url> && cd whattools
cp .env.example .env

# Start all services
make dev-up

# Run migrations
make db-upgrade

# Seed test data
make db-seed

# Verify everything is running
curl http://localhost:5000/api/v1/health
```

### Local Services

| Service    | URL                      |
|------------|--------------------------|
| Gateway    | http://localhost:5000     |
| Auth       | http://localhost:5001     |
| Inventory  | http://localhost:5002     || Sales      | http://localhost:5003     |
| Analytics  | http://localhost:5004     |
| Shipping   | http://localhost:5005     |
| PostgreSQL | localhost:5432            |
| Redis      | localhost:6379            |

### Development Commands

```bash
make dev-up       # Start all services
make dev-down     # Stop all services
make dev-logs     # Tail logs from all services
make test         # Run full test suite
make lint         # Run linter
make lint-fix     # Auto-fix lint issues
make coverage     # Generate HTML coverage report
make clean        # Remove caches and build artifacts
```

### Database Commands

```bash
make db-upgrade                        # Run migrations
make db-migrate msg="add_new_column"   # Generate new migration
make db-seed                           # Seed development data
```

## Production Deployment (K3S)

### 1. Build and Push Docker Images

```bash
# Build images
docker build -t whattools/auth:latest -f services/auth/Dockerfile .
docker build -t whattools/inventory:latest -f services/inventory/Dockerfile .
docker build -t whattools/sales:latest -f services/sales/Dockerfile .
docker build -t whattools/analytics:latest -f services/analytics/Dockerfile .
docker build -t whattools/shipping:latest -f services/shipping/Dockerfile .
docker build -t whattools/gateway:latest -f services/gateway/Dockerfile .

# Tag and push to your registry
docker tag whattools/auth:latest <registry>/whattools/auth:latest
docker push <registry>/whattools/auth:latest
# ... repeat for inventory and gateway
```

### 2. Configure Secrets

**Before deploying**, update `k8s/prod/secrets.yaml` with production values:

```bash
# Generate a strong secret key
openssl rand -base64 32

# Base64 encode for the secrets.yaml
echo -n 'your-strong-secret-key' | base64
```

Update all base64-encoded values in `k8s/prod/secrets.yaml`:
- `SECRET_KEY` — Flask secret key
- `JWT_SECRET_KEY` — JWT signing secret
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`

### 3. Deploy

```bash
# Apply all manifests
make deploy

# Check status
make deploy-status
```

Or apply individually:

```bash
kubectl apply -f k8s/prod/namespace.yaml
kubectl apply -f k8s/prod/configmap.yaml
kubectl apply -f k8s/prod/secrets.yaml
kubectl apply -f k8s/prod/postgres.yaml
kubectl apply -f k8s/prod/redis.yaml
kubectl apply -f k8s/prod/auth.yaml
kubectl apply -f k8s/prod/inventory.yaml
kubectl apply -f k8s/prod/sales.yaml
kubectl apply -f k8s/prod/analytics.yaml
kubectl apply -f k8s/prod/shipping.yaml
kubectl apply -f k8s/prod/gateway.yaml
kubectl apply -f k8s/prod/ingress.yaml
```

### 4. Run Migrations on Production

```bash
# Get a running auth pod name
POD=$(kubectl get pod -n whattools -l app=auth -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -n whattools $POD -- alembic upgrade head

# Seed data (optional, for initial setup)
kubectl exec -n whattools $POD -- python -m scripts.seed
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n whattools

# Check services
kubectl get svc -n whattools

# Check ingress
kubectl get ingress -n whattools

# Test health endpoint
curl https://whattools.trector.com/api/v1/health
```

## Monitoring

### Logs

All services output structured JSON logs via structlog. View logs with:

```bash
# All services
kubectl logs -n whattools -l app.kubernetes.io/part-of=whattools -f

# Specific service
kubectl logs -n whattools -l app=auth -f
kubectl logs -n whattools -l app=inventory -f
kubectl logs -n whattools -l app=sales -f
kubectl logs -n whattools -l app=analytics -f
kubectl logs -n whattools -l app=shipping -f
kubectl logs -n whattools -l app=gateway -f
```

### Health Checks

- **Liveness**: `/health` — returns 200 if the process is running
- **Readiness**: `/ready` — returns 200 if the service can handle requests (DB connected)
- **Aggregated**: `GET /api/v1/health` — checks all services, returns 503 if any are down

### Resource Usage

```bash
kubectl top pods -n whattools
kubectl top nodes
```

## Scaling

Scale services independently:

```bash
kubectl scale deployment auth -n whattools --replicas=3
kubectl scale deployment inventory -n whattools --replicas=3
kubectl scale deployment gateway -n whattools --replicas=3
```

## Rollback

```bash
# Check rollout history
kubectl rollout history deployment/auth -n whattools

# Rollback to previous version
kubectl rollout undo deployment/auth -n whattools

# Rollback to specific revision
kubectl rollout undo deployment/auth -n whattools --to-revision=2
```
