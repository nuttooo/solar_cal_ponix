#!/bin/bash
# Validation script to test Docker setup

set -e

echo "=========================================="
echo "Docker Setup Validation"
echo "=========================================="
echo ""

# Check Docker availability
echo "✓ Checking Docker..."
docker --version

echo ""
echo "✓ Checking directory structure..."
if [ -d "uploads" ] && [ -f "uploads/.gitkeep" ]; then
    echo "  ✓ uploads/ directory exists with .gitkeep"
else
    echo "  ✗ uploads/ directory or .gitkeep missing"
    exit 1
fi

if [ -d "static/outputs" ] && [ -f "static/outputs/.gitkeep" ]; then
    echo "  ✓ static/outputs/ directory exists with .gitkeep"
else
    echo "  ✗ static/outputs/ directory or .gitkeep missing"
    exit 1
fi

echo ""
echo "✓ Checking configuration files..."
if [ -f "docker-compose.yml" ]; then
    echo "  ✓ docker-compose.yml exists (production)"
else
    echo "  ✗ docker-compose.yml missing"
    exit 1
fi

if [ -f "docker-compose.dev.yml" ]; then
    echo "  ✓ docker-compose.dev.yml exists (development)"
else
    echo "  ✗ docker-compose.dev.yml missing"
    exit 1
fi

if [ -f "Dockerfile" ]; then
    echo "  ✓ Dockerfile exists"
else
    echo "  ✗ Dockerfile missing"
    exit 1
fi

if [ -f "DOCKER_DEPLOYMENT.md" ]; then
    echo "  ✓ DOCKER_DEPLOYMENT.md exists"
else
    echo "  ✗ DOCKER_DEPLOYMENT.md missing"
    exit 1
fi

echo ""
echo "✓ Checking .dockerignore..."
if grep -q "uploads/\*" .dockerignore && grep -q "!uploads/.gitkeep" .dockerignore; then
    echo "  ✓ .dockerignore properly configured for uploads/"
else
    echo "  ✗ .dockerignore not properly configured for uploads/"
    exit 1
fi

if grep -q "static/outputs/\*" .dockerignore && grep -q "!static/outputs/.gitkeep" .dockerignore; then
    echo "  ✓ .dockerignore properly configured for static/outputs/"
else
    echo "  ✗ .dockerignore not properly configured for static/outputs/"
    exit 1
fi

echo ""
echo "✓ Checking .gitignore..."
if grep -q "uploads/\*" .gitignore && grep -q "!uploads/.gitkeep" .gitignore; then
    echo "  ✓ .gitignore properly configured for uploads/"
else
    echo "  ✗ .gitignore not properly configured for uploads/"
    exit 1
fi

if grep -q "static/outputs/\*" .gitignore && grep -q "!static/outputs/.gitkeep" .gitignore; then
    echo "  ✓ .gitignore properly configured for static/outputs/"
else
    echo "  ✗ .gitignore not properly configured for static/outputs/"
    exit 1
fi

echo ""
echo "✓ Validating docker-compose.yml volumes..."
if grep -q "solar-uploads:/app/uploads" docker-compose.yml; then
    echo "  ✓ Named volume for uploads configured"
else
    echo "  ✗ Named volume for uploads not found"
    exit 1
fi

if grep -q "solar-outputs:/app/static/outputs" docker-compose.yml; then
    echo "  ✓ Named volume for outputs configured"
else
    echo "  ✗ Named volume for outputs not found"
    exit 1
fi

echo ""
echo "✓ Checking deploy script..."
if [ -x "deploy.sh" ]; then
    echo "  ✓ deploy.sh is executable"
else
    echo "  ✗ deploy.sh not executable"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All validations passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Production deployment: ./deploy.sh production"
echo "2. Development deployment: ./deploy.sh dev"
echo "3. Read full guide: cat DOCKER_DEPLOYMENT.md"
