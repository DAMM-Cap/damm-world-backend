
# Stop and remove all containers, networks, volumes
echo "Stopping and removing all containers and volumes..."
docker-compose down -v

# Remove any leftover volumes, images, networks
echo "Cleaning up unused Docker resources..."
docker system prune -af --volumes

# Build fresh images
echo "Building images with no cache..."
docker-compose build --no-cache

# Start containers
echo "Starting containers..."
docker-compose up -d

# Wait for Postgres to become healthy
echo "Waiting for Postgres to be healthy..."
while [[ $(docker inspect --format='{{.State.Health.Status}}' damm_postgres) != "healthy" ]]; do
  echo -n "."
  sleep 1
done
echo "Postgres is healthy!"

# Create tables
echo "Recreating tables..."
docker-compose run --rm indexer python create_table.py

echo "Done! All tables recreated and services restarted."
