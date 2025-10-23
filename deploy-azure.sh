#!/bin/bash

# Azure Deployment Script for Solar Analyzer Pro
# This script builds and deploys the application to Azure Web App for Containers

set -e

# Configuration
RESOURCE_GROUP="solar-analyzer-rg"
LOCATION="southeastasia"
APP_NAME="solar-analyzer-pro"
ACR_NAME="solaranalyzeracr"
IMAGE_TAG="latest"

echo "🚀 Starting Azure deployment for Solar Analyzer Pro..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Login to Azure (uncomment if not already logged in)
# az login

# Create resource group if it doesn't exist
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry if it doesn't exist
echo "🏭 Creating Azure Container Registry..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Build and push Docker image to ACR
echo "🔨 Building Docker image..."
az acr build --registry $ACR_NAME --image solar-analyzer:$IMAGE_TAG .

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)

# Create App Service Plan
echo "📋 Creating App Service Plan..."
az appservice plan create \
    --name "$APP_NAME-plan" \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku B1 \
    --is-linux

# Create Web App for Containers
echo "🌐 Creating Web App..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan "$APP_NAME-plan" \
    --name $APP_NAME \
    --deployment-container-image-name "$ACR_LOGIN_SERVER/solar-analyzer:$IMAGE_TAG"

# Configure Web App
echo "⚙️ Configuring Web App..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
    WEBSITES_PORT=8000 \
    DOCKER_CUSTOM_IMAGE_NAME="$ACR_LOGIN_SERVER/solar-analyzer:$IMAGE_TAG"

# Enable HTTP/2 and always-on
az webapp update \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --https-only true \
    --http20-enabled true

# Get ACR admin credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Configure container registry credentials
az webapp config container set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --docker-custom-image-name "$ACR_LOGIN_SERVER/solar-analyzer:$IMAGE_TAG" \
    --docker-registry-server-url "https://$ACR_LOGIN_SERVER" \
    --docker-registry-server-user $ACR_USERNAME \
    --docker-registry-server-password $ACR_PASSWORD

# Get the Web App URL
WEBAPP_URL=$(az webapp show --resource-group $RESOURCE_GROUP --name $APP_NAME --query defaultHostName --output tsv)

echo "✅ Deployment completed successfully!"
echo "🌍 Your application is now available at: https://$WEBAPP_URL"
echo "📊 You can monitor your app at: https://portal.azure.com/#blade/HubsExtension/BrowseResource/resourceGroup/Microsoft.Web/sites/$APP_NAME"