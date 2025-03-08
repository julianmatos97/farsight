#!/bin/bash
# Script to reset the database

# Stop the containers
echo "Stopping containers..."
docker-compose down

# Remove the PostgreSQL volume
echo "Removing PostgreSQL volume..."
docker volume rm farsight2_postgres_data

# Start the containers
echo "Starting containers..."
docker-compose up -d

# Wait for the containers to be ready
echo "Waiting for containers to be ready..."
sleep 10

echo "Database reset complete." 