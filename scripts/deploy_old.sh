#!/bin/bash

# Exit on any error
set -e

# Define variables
BACKUP_FILE="backup.sql"
NETWORK_NAME="alphabench__network"

echo "🚀 Starting Deployment Script..."

# Step 1: Backup Database
echo "📦 Backing up database..."
docker exec alphabench__postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE
echo "✅ Database backup saved to $BACKUP_FILE."

# Step 2: Stop and Remove Existing Containers
echo "🛑 Stopping all running containers..."
docker compose down --volumes
echo "🧹 Removed containers, networks, and volumes."

# Step 3: Recreate Docker Network
echo "🌐 Creating Docker network..."
docker network create $NETWORK_NAME || echo "ℹ️ Network already exists, skipping creation."
echo "✅ Docker network created."

# Step 4: Deploy Services in Logical Order

# Step 4.1: Start Database Service
echo "📊 Starting PostgreSQL service..."
docker compose up -d alphabench__postgres
echo "⏳ Waiting for PostgreSQL to initialize..."
until docker exec alphabench__postgres pg_isready -U $POSTGRES_USER; do
  sleep 2
done
echo "✅ PostgreSQL is ready."

# Step 4.2: Restore Database Backup
echo "🛠️ Restoring database from backup..."
docker exec -i alphabench__postgres psql -U $POSTGRES_USER $POSTGRES_DB < $BACKUP_FILE
echo "✅ Database restored from $BACKUP_FILE."

# Step 4.3: Start Redis Service
echo "📡 Starting Redis service..."
docker compose up -d alphabench__redis
echo "⏳ Waiting for Redis to be ready..."
until docker exec alphabench__redis redis-cli -a $REDIS_PASSWORD ping | grep -q "PONG"; do
  sleep 2
done
echo "✅ Redis is ready."

# Step 4.4: Start Backend and Worker Services
echo "🖥️ Starting FastAPI service..."
docker compose up -d alphabench__fastapi
echo "✅ FastAPI service started."

echo "🔨 Starting Celery workers..."
docker compose up -d celery_worker_script_generator celery_worker_script_validator celery_worker_backtest celery_worker_report
echo "✅ Celery workers started."

# Step 4.5: Start Monitoring Services
echo "📊 Starting monitoring services..."
docker compose up -d prometheus grafana
echo "✅ Monitoring services started."

# Step 5: Confirm Deployment
echo "🎉 Deployment completed successfully!"
docker compose ps

# Final Note
echo "📂 Logs are available for review using: docker logs <container_name>"
echo "📂 To check application status, visit your monitoring endpoints."

# Done!