#!/bin/bash
# Script to run the application in development mode

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if the OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY is not set. Please set it in the .env file."
    exit 1
fi

# Start the PostgreSQL container
echo "Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Initialize the database
echo "Initializing the database..."
python -m farsight2.database.init_db

# Run the application
echo "Starting the application..."
python -m farsight2.main api 