#!/bin/bash

# Enable Docker Compose to delegate builds to Buildx Bake
export COMPOSE_BAKE=true

echo "Stopping project containers except database..."
docker stop damm_bot damm_world_api lagoon_indexer_base

echo "Removing stopped project containers..."
docker rm damm_bot damm_world_api lagoon_indexer_base

echo "Cleaning up unused Docker resources (images, networks)..."
docker system prune -af

echo "Pruning dangling volumes (keeps active volumes like database)..."
docker volume prune -f

echo "Building images with no cache..."
docker-compose build --no-cache

echo "Checking Postgres health..."
while [[ $(docker inspect --format='{{.State.Health.Status}}' damm_postgres) != "healthy" ]]; do
  echo -n "."
  sleep 1
done
echo "Postgres is healthy!"

echo "Starting Lagoon services: indexer, api, bot..."
docker-compose up damm-api indexer-base lagoon-bot
