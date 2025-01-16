#!/bin/bash

# Function to log messages with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Build all containers
log "🚀 Starting the build process..."
docker compose build
if [ $? -ne 0 ]; then
    log "❌ Build failed"
    exit 1
fi
log "✅ Build completed successfully!"

# Stop all containers except Postgres
log "🛑 Stopping all containers except PostgreSQL..."
docker compose stop \
    alphabench__redis \
    alphabench__fastapi \
    celery_worker_script_generator \
    celery_worker_script_validator \
    celery_worker_backtest \
    celery_worker_report_generator \
    celery_flower \
    alphabench__prometheus \
    alphabench__grafana

# Start containers in sequence
log "🔄 Starting containers in sequence..."

# 1. Start Redis
log "📦 Starting Redis..."
docker compose up -d alphabench__redis
sleep 5  # Brief pause to allow Redis to initialize

# 2. Start FastAPI
log "🚀 Starting FastAPI service..."
docker compose up -d alphabench__fastapi
sleep 5  # Brief pause to allow FastAPI to initialize

# 3. Start Celery workers in sequence
for worker in celery_worker_script_generator celery_worker_script_validator celery_worker_backtest celery_worker_report_generator; do
    log "👷 Starting $worker..."
    docker compose up -d $worker
    sleep 3  # Brief pause between workers
done

# 4. Start monitoring stack
log "📊 Starting monitoring services..."
docker compose up -d alphabench__prometheus
sleep 3

docker compose up -d alphabench__grafana
sleep 3

# 5. Start Flower last
log "🌸 Starting Celery Flower..."
docker compose up -d celery_flower

log "✨ Deployment completed successfully! 🎉"
log "🌐 Services are available at their respective ports"