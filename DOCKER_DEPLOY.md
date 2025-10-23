# Docker Deployment Guide for Solar Analyzer Pro

This guide explains how to deploy the Solar Analyzer Pro application using Docker, both locally and to Azure.

## Prerequisites

- Docker installed on your machine
- For Azure deployment: Azure CLI installed and configured

## Local Docker Deployment

### Using Docker Compose (Recommended)

1. Build and run the application:
```bash
docker-compose up --build
```

2. Access the application at: http://localhost:8000

### Using Docker directly

1. Build the Docker image:
```bash
docker build -t solar-analyzer .
```

2. Run the container:
```bash
docker run -p 8000:8000 -v $(pwd)/uploads:/app/uploads -v $(pwd)/static/outputs:/app/static/outputs solar-analyzer
```

3. Access the application at: http://localhost:8000

## Azure Deployment

### Option 1: Using the Deployment Script (Recommended)

1. Make the deployment script executable:
```bash
chmod +x deploy-azure.sh
```

2. Run the deployment script:
```bash
./deploy-azure.sh
```

This script will:
- Create a resource group
- Create an Azure Container Registry (ACR)
- Build and push the Docker image to ACR
- Create an App Service Plan
- Create and configure a Web App for Containers

### Option 2: Manual Azure Deployment

1. Create a resource group:
```bash
az group create --name solar-analyzer-rg --location southeastasia
```

2. Create an Azure Container Registry:
```bash
az acr create --resource-group solar-analyzer-rg --name solaranalyzeracr --sku Basic --admin-enabled true
```

3. Build and push the image to ACR:
```bash
az acr build --registry solaranalyzeracr --image solar-analyzer:latest .
```

4. Create an App Service Plan:
```bash
az appservice plan create --name solar-analyzer-plan --resource-group solar-analyzer-rg --location southeastasia --sku B1 --is-linux
```

5. Create the Web App:
```bash
az webapp create --resource-group solar-analyzer-rg --plan solar-analyzer-plan --name solar-analyzer-pro --deployment-container-image-name solaranalyzeracr.azurecr.io/solar-analyzer:latest
```

6. Configure the Web App:
```bash
az webapp config appsettings set --resource-group solar-analyzer-rg --name solar-analyzer-pro --settings WEBSITES_PORT=8000
```

## Configuration

### Environment Variables

The application can be configured with the following environment variables:

- `FLASK_ENV`: Set to `production` for production deployment
- `PYTHONUNBUFFERED`: Set to `1` for better logging
- `WEBSITES_PORT`: Set to `8000` for Azure App Service

### Persistent Storage

For Azure deployment, consider using Azure Files for persistent storage of uploaded files and generated outputs:

```bash
# Create a storage account
az storage account create --name solaranalyzerstorage --resource-group solar-analyzer-rg --location southeastasia --sku Standard_LRS

# Create a file share
az storage share create --name uploads --account-name solaranalyzerstorage
az storage share create --name outputs --account-name solaranalyzerstorage

# Mount the file shares to your web app
az webapp config storage-account add --resource-group solar-analyzer-rg --name solar-analyzer-pro \
  --custom-id uploads --storage-type AzureFiles --share-name uploads \
  --account-name solaranalyzerstorage --access-key "<storage-key>" --mount-path /app/uploads

az webapp config storage-account add --resource-group solar-analyzer-rg --name solar-analyzer-pro \
  --custom-id outputs --storage-type AzureFiles --share-name outputs \
  --account-name solaranalyzerstorage --access-key "<storage-key>" --mount-path /app/static/outputs
```

## Monitoring and Logs

### Local Docker

View logs:
```bash
docker-compose logs -f
```

### Azure

View logs:
```bash
az webapp log tail --name solar-analyzer-pro --resource-group solar-analyzer-rg
```

Enable application logging:
```bash
az webapp log config --name solar-analyzer-pro --resource-group solar-analyzer-rg --application-logging true --detailed-error-messages true
```

## Scaling

### Horizontal Scaling

For Azure App Service, you can scale out manually or enable auto-scaling:

```bash
# Scale out to 2 instances
az appservice plan update --name solar-analyzer-plan --resource-group solar-analyzer-rg --number-of-workers 2
```

### Vertical Scaling

Upgrade the App Service Plan for better performance:

```bash
# Upgrade to S2 tier
az appservice plan update --name solar-analyzer-plan --resource-group solar-analyzer-rg --sku S2
```

## Security Considerations

1. **HTTPS Only**: The application is configured to use HTTPS only in production
2. **File Uploads**: File size is limited to 16MB
3. **Session Security**: Flask sessions are secured with a random secret key
4. **Container Security**: The application runs as a non-root user in the container

## Troubleshooting

### Common Issues

1. **Port Issues**: Ensure the application is running on port 8000 inside the container
2. **File Permissions**: The application runs as a non-root user, ensure proper permissions
3. **Memory Issues**: For large datasets, consider increasing the memory allocation
4. **Storage Issues**: Ensure persistent storage is properly configured for production

### Health Checks

The application includes a health check endpoint. You can test it:

```bash
curl -f http://localhost:8000/
```

For Azure, the health check is automatically configured and will restart the container if it fails.

## Cost Optimization

1. **Use B1 tier for development/testing**
2. **Enable auto-stop for dev environments**
3. **Monitor resource usage and scale appropriately**
4. **Use Azure Reservations for predictable workloads**