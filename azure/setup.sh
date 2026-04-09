#!/bin/bash
# Azure BotBox Kurulum Scripti

RESOURCE_GROUP="botbox-rg"
LOCATION="westeurope"
ACR_NAME="botboxacr"
AKS_NAME="botbox-aks"

# Resource Group oluştur
az group create --name $RESOURCE_GROUP --location $LOCATION

# Container Registry oluştur
az acr create --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME --sku Basic

# AKS cluster oluştur (1 node, ücretsiz tier)
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --node-count 1 \
  --node-vm-size Standard_B2s \
  --attach-acr $ACR_NAME \
  --generate-ssh-keys

# kubectl bağlantısı
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME

echo "Kurulum tamamlandı!"
echo "ACR Login Server: $(az acr show --name $ACR_NAME --query loginServer -o tsv)"