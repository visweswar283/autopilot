#!/bin/bash
# EC2 bootstrap — installs Docker, pulls images from ECR, starts containers
set -e

# --- Install Docker ---
yum update -y
yum install -y docker
systemctl enable docker
systemctl start docker

# --- Install docker-compose plugin ---
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# --- Login to ECR ---
aws ecr get-login-password --region ${aws_region} | \
  docker login --username AWS --password-stdin ${ecr_registry}

# --- Write .env ---
cat > /opt/applypilot/.env <<EOF
DATABASE_URL=${db_url}
REDIS_URL=${redis_url}
JWT_SECRET=${jwt_secret}
PORT=8080
HEADLESS=true
SCRAPER_INTERVAL_HOURS=2
APPLY_INTERVAL_HOURS=4
MAX_APPLIES_PER_USER=20
SESSIONS_DIR=/tmp/sessions
ML_SERVICE_URL=http://ml-service:8001
EOF

# --- Write docker-compose for production (no build, pull from ECR) ---
mkdir -p /opt/applypilot
cat > /opt/applypilot/docker-compose.yml <<EOF
services:
  backend:
    image: ${ecr_registry}/${app_name}/backend:latest
    ports:
      - "8080:8080"
    env_file: .env
    restart: unless-stopped

  ml-service:
    image: ${ecr_registry}/${app_name}/ml-service:latest
    ports:
      - "8001:8001"
    env_file: .env
    volumes:
      - ml_models:/root/.cache
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      retries: 3

  scraper:
    image: ${ecr_registry}/${app_name}/workers:latest
    env_file: .env
    volumes:
      - /tmp/sessions:/tmp/sessions
    depends_on:
      ml-service:
        condition: service_healthy
    restart: unless-stopped

volumes:
  ml_models:
EOF

cd /opt/applypilot
docker compose pull
docker compose up -d

# --- Auto-update cron (pulls new images every hour) ---
echo "0 * * * * root cd /opt/applypilot && docker compose pull && docker compose up -d" \
  > /etc/cron.d/applypilot-update
