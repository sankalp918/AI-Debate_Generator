#!/bin/bash

echo "Setting up AI Debate Generator..."

# Ensure required directories exist
mkdir -p {assets,output}

# Add default face images (you need to provide these)
if [ ! -f "assets/person1.jpg" ]; then
    echo "WARNING: Please add person1.jpg to assets/ folder"
fi

if [ ! -f "assets/person2.jpg" ]; then
    echo "WARNING: Please add person2.jpg to assets/ folder"
fi

# Remove version line from docker-compose.yml (it's deprecated)
sed -i '/^version:/d' docker-compose.yml

echo "Building Docker images..."
docker-compose build --no-cache

echo "Starting services..."
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 30

# Test services
echo "Testing services..."
curl -f http://localhost:8001/health 2>/dev/null && echo "✓ Text Generation: Ready" || echo "✗ Text Generation: Failed"
curl -f http://localhost:8002/health 2>/dev/null && echo "✓ TTS: Ready" || echo "✗ TTS: Failed"
curl -f http://localhost:8003/health 2>/dev/null && echo "✓ Lip Sync: Ready" || echo "✗ Lip Sync: Failed"

echo "Setup complete!"