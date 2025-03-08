#!/bin/bash
# Script to run the application in production mode

# Check if the .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it first."
    exit 1
fi

# Build and start the containers
echo "Building and starting containers..."
docker-compose up -d --build

# Wait for the containers to be ready
echo "Waiting for containers to be ready..."
sleep 10

# Check if the containers are running
if [ "$(docker-compose ps -q app)" ] && [ "$(docker-compose ps -q postgres)" ]; then
    echo "Containers are running."
    echo "API is available at http://localhost:8000"
    echo "Swagger documentation is available at http://localhost:8000/docs"
else
    echo "Error: Containers failed to start."
    docker-compose logs
    exit 1
fi 