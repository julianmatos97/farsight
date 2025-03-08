#!/bin/bash
# Script to completely reset the Docker environment
# This will remove all containers, images, and volumes related to the Farsight2 project

# Set bold text
bold=$(tput bold)
normal=$(tput sgr0)

echo "${bold}🚨 WARNING: This will delete ALL Farsight2 containers, images, and volumes! 🚨${normal}"
echo "This is a destructive operation and cannot be undone."
echo ""
read -p "Are you sure you want to continue? (y/N): " confirmation

if [[ $confirmation != "y" && $confirmation != "Y" ]]; then
    echo "Operation cancelled."
    exit 0
fi

echo ""
echo "${bold}Step 1: Stopping all containers...${normal}"
docker-compose down

echo ""
echo "${bold}Step 2: Removing all Docker volumes...${normal}"
docker volume rm farsight2_postgres_data 2>/dev/null || echo "- No Farsight2 volumes found"
# List all volumes with 'farsight' in the name
farsight_volumes=$(docker volume ls --filter name=farsight -q)
if [ -n "$farsight_volumes" ]; then
    echo "Removing additional Farsight2 volumes:"
    echo "$farsight_volumes" | while read volume; do
        echo "- Removing $volume"
        docker volume rm $volume
    done
fi

echo ""
echo "${bold}Step 3: Removing all Docker images...${normal}"
# Get image IDs for any images created from our docker-compose file
image_ids=$(docker images | grep 'farsight' | awk '{print $3}')
if [ -n "$image_ids" ]; then
    echo "Removing Farsight2 images:"
    for id in $image_ids; do
        echo "- Removing image $id"
        docker rmi -f $id
    done
else
    echo "- No Farsight2 images found"
fi

# Also remove postgres images if they exist
postgres_images=$(docker images | grep 'postgres' | awk '{print $3}')
if [ -n "$postgres_images" ]; then
    echo "Removing PostgreSQL images:"
    for id in $postgres_images; do
        echo "- Removing image $id"
        docker rmi -f $id
    done
fi

echo ""
echo "${bold}Step 4: Cleaning up Docker system...${normal}"
echo "- Removing unused networks"
docker network prune -f

echo ""
echo "${bold}Step 5: Checking for any remaining Farsight2 resources...${normal}"
containers=$(docker ps -a | grep 'farsight' | awk '{print $1}')
if [ -n "$containers" ]; then
    echo "Removing leftover containers:"
    for container in $containers; do
        echo "- Removing container $container"
        docker rm -f $container
    done
else
    echo "- No leftover containers found"
fi

echo ""
echo "${bold}✅ Reset complete!${normal}"
echo "All Farsight2 Docker resources have been removed."
echo ""
echo "To rebuild the environment from scratch, run:"
echo "  ./scripts/run_dev.sh    # For development"
echo "  ./scripts/run_prod.sh   # For production" 