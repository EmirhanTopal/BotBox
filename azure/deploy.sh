#!/bin/bash
# Docker image build et, ACR'a push et, AKS'e deploy et

ACR_NAME="botboxacr"
ACR_SERVER="${ACR_NAME}.azurecr.io"

# ACR'a login
az acr login --name $ACR_NAME

# Image build ve push
docker build -t ${ACR_SERVER}/botbox-web:latest ./webapp/BotBoxWeb
docker push ${ACR_SERVER}/botbox-web:latest

# Kubernetes'e deploy et
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/db-pvc.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/db-service.yaml
kubectl apply -f k8s/web-deployment.yaml
kubectl apply -f k8s/web-service.yaml

echo "Deploy tamamlandı!"
kubectl get pods -n botbox
kubectl get svc -n botbox