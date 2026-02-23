# Production Deployment Guide

This guide covers deploying the Airbnb/VRBO Hosting Automation platform to production.

## Deployment Options

### Option 1: Docker Compose (Single Server)

Suitable for small to medium deployments.

### Option 2: Kubernetes

Suitable for large-scale, high-availability deployments.

### Option 3: Cloud Platforms

- AWS (ECS, EKS, or Elastic Beanstalk)
- Google Cloud (Cloud Run, GKE)
- Azure (Container Apps, AKS)

---

## Prerequisites

- Domain name with DNS access
- SSL certificate (or use Let's Encrypt)
- Server with at least 2GB RAM, 2 vCPUs
- Docker and Docker Compose installed
- PostgreSQL 14+ (managed or self-hosted)
- Redis 6+ (managed or self-hosted)

---

## Docker Compose Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Clone Repository

```bash
git clone <repository-url> /opt/airbnb-automation
cd /opt/airbnb-automation
```

### 3. Configure Environment

Create production environment file:

```bash
cp .env.example .env.production
```

Edit `.env.production`:

```env
# Application
ENVIRONMENT=production
DEBUG=false

# Database (use managed PostgreSQL in production)
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/airbnb_automation

# Redis (use managed Redis in production)
REDIS_URL=redis://:password@redis-host:6379/0

# Security
JWT_SECRET_KEY=<generate-secure-random-string>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# RentAHuman API
RENTAHUMAN_API_KEY=<your-production-api-key>
RENTAHUMAN_MOCK_MODE=false
RENTAHUMAN_BASE_URL=https://api.rentahuman.com

# Google OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=<generate-secure-random-string>

# Celery
CELERY_BROKER_URL=redis://:password@redis-host:6379/1
CELERY_RESULT_BACKEND=redis://:password@redis-host:6379/2

# Logging
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=https://yourdomain.com
```

Generate secure secrets:
```bash
# Generate JWT secret
openssl rand -hex 32

# Generate NextAuth secret
openssl rand -base64 32
```

### 4. Create Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - RENTAHUMAN_API_KEY=${RENTAHUMAN_API_KEY}
      - RENTAHUMAN_MOCK_MODE=false
    ports:
      - "8000:8000"
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A main.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    restart: always
    depends_on:
      - backend
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A main.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    restart: always
    depends_on:
      - backend
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    ports:
      - "3000:3000"
    environment:
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    restart: always
    depends_on:
      - backend
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/certbot:/var/www/certbot:ro
    depends_on:
      - backend
      - frontend
    restart: always
```

### 5. Create Production Dockerfiles

**backend/Dockerfile.prod:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

**frontend/Dockerfile.prod:**
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build arguments
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy source and build
COPY . .
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built assets
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
```

### 6. Configure Nginx

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com api.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # Frontend
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }

    # API
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        location / {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;

            # CORS headers
            add_header Access-Control-Allow-Origin "https://yourdomain.com" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

            if ($request_method = OPTIONS) {
                return 204;
            }
        }

        # WebSocket support
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }
    }
}
```

### 7. SSL Setup with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --webroot -w ./nginx/certbot \
  -d yourdomain.com -d api.yourdomain.com \
  --email your@email.com --agree-tos

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./nginx/ssl/
sudo chown -R $USER:$USER ./nginx/ssl/
```

### 8. Database Migration

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 9. Deploy

```bash
# Build and start
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check health
curl https://api.yourdomain.com/health
```

---

## Kubernetes Deployment

### 1. Create Kubernetes Manifests

**k8s/namespace.yaml:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: airbnb-automation
```

**k8s/secrets.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: airbnb-automation
type: Opaque
stringData:
  DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/db
  JWT_SECRET_KEY: your-secret-key
  RENTAHUMAN_API_KEY: your-api-key
```

**k8s/backend-deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: airbnb-automation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/airbnb-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: airbnb-automation
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
```

### 2. Deploy to Kubernetes

```bash
# Create namespace and secrets
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy applications
kubectl apply -f k8s/

# Check status
kubectl get pods -n airbnb-automation
kubectl get services -n airbnb-automation
```

---

## Monitoring & Logging

### Application Monitoring

Add Prometheus metrics to the backend:

```python
# backend/monitoring.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import APIRouter

router = APIRouter()

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Log Aggregation

Configure centralized logging with ELK or Loki:

```yaml
# docker-compose.prod.yml - add logging service
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana-data:/var/lib/grafana
```

---

## Backup Strategy

### Database Backups

```bash
# Create backup script
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/opt/backups
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/db_$DATE.sql.gz
# Keep last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/backup.sh" | crontab -
```

### Automated Backups with S3

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Backup script with S3 upload
cat > /opt/backup-s3.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/tmp/backups
DATE=$(date +%Y%m%d_%H%M%S)
BUCKET=your-backup-bucket

pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/db_$DATE.sql.gz
aws s3 cp $BACKUP_DIR/db_$DATE.sql.gz s3://$BUCKET/database/
rm $BACKUP_DIR/db_$DATE.sql.gz
EOF
```

---

## Security Checklist

- [ ] All secrets stored in environment variables or secret manager
- [ ] HTTPS enabled with valid SSL certificates
- [ ] Database accessible only from application servers
- [ ] Redis password protected
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers set (CSP, HSTS, etc.)
- [ ] Regular security updates applied
- [ ] Logging and monitoring enabled
- [ ] Backup strategy implemented and tested
- [ ] Firewall rules configured (only 80/443 exposed)

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check container status
docker ps -a

# Shell into container
docker-compose -f docker-compose.prod.yml exec backend /bin/bash
```

### Database Connection Issues

```bash
# Test database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "
from sqlalchemy import create_engine
engine = create_engine('$DATABASE_URL')
conn = engine.connect()
print('Connected successfully')
conn.close()
"
```

### Celery Tasks Not Running

```bash
# Check Celery worker logs
docker-compose -f docker-compose.prod.yml logs celery_worker

# Check Redis connection
docker-compose -f docker-compose.prod.yml exec backend python -c "
import redis
r = redis.from_url('$REDIS_URL')
r.ping()
print('Redis connected')
"
```

### SSL Certificate Renewal

```bash
# Renew certificates
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem ./nginx/ssl/

# Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=5
```

### Load Balancer Configuration

For multiple backend instances, Nginx automatically load balances. For Kubernetes, use Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: airbnb-automation
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: api-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
```
