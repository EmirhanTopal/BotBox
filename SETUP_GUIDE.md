# BotBox Setup & Deployment Guide

## 📋 Table of Contents
1. [Quick Start with Docker Compose](#quick-start-with-docker-compose)
2. [Local Development Setup](#local-development-setup)
3. [Kubernetes Deployment (Azure)](#kubernetes-deployment-azure)
4. [Data Loading & Scraping](#data-loading--scraping)
5. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start with Docker Compose

### Prerequisites
- Windows 10/11 with WSL 2 enabled
- Docker Desktop installed and running
- WSL Ubuntu installed

### Step 1: Setup Environment Variables
```bash
cd /path/to/BotBox
cp .env.example .env
```

Edit `.env` and set your values:
```env
POSTGRES_DB=botboxdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DJANGO_SECRET_KEY=your_django_secret_key
DEBUG=True
OLLAMA_MODEL=mistral
```

### Step 2: Build and Start Services
```bash
# In PowerShell or WSL Ubuntu
docker-compose up -d

# Wait for services to start (30-60 seconds)
docker-compose logs -f
```

### Step 3: Run Initial Migrations
```bash
docker exec botbox_web python manage.py migrate
```

### Step 4: Load Data
```bash
# Option 1: Using management command
docker exec botbox_web python manage.py scrape_acibadem

# Option 2: Using API endpoint
curl -X POST http://localhost:8000/api/scrape/trigger/ \
  -H "Content-Type: application/json"
```

### Step 5: Access the Application
- Web UI: http://localhost:8000
- API: http://localhost:8000/api/
- Database: Connect to localhost:5432 with psql

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 15
- Docker Desktop (for Ollama container)

### Step 1: Setup Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Or in WSL Ubuntu
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
cd webapp/BotBoxWeb
pip install -r requirements.txt
pip install -r ../../requirements.txt  # For scraper
```

### Step 3: Setup Database
```bash
# Create PostgreSQL database
createdb botboxdb

# Run migrations
python manage.py migrate
```

### Step 4: Start Ollama Container
```bash
# In separate terminal
docker run -d -p 11434:11434 ollama/ollama:latest
```

### Step 5: Start Django Server
```bash
python manage.py runserver
```

---

## ☸️ Kubernetes Deployment (Azure)

### Prerequisites
- Azure subscription
- Azure CLI installed
- kubectl installed
- Helm (optional)

### Step 1: Create AKS Cluster
```bash
az group create --name botbox-rg --location eastus

az aks create \
  --resource-group botbox-rg \
  --name botbox-aks \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --enable-managed-identity

az aks get-credentials \
  --resource-group botbox-rg \
  --name botbox-aks \
  --admin
```

### Step 2: Create Namespaces and Secrets
```bash
# Create namespace
kubectl create namespace botbox

# Create secrets
kubectl create secret generic botbox-secrets \
  --from-literal=DJANGO_SECRET_KEY='your-key' \
  --from-literal=DB_PASSWORD='your-password' \
  -n botbox

# Create Azure storage secret (if using Azure Blob Storage)
kubectl create secret generic azure-credentials \
  --from-literal=AZURE_STORAGE_ACCOUNT_NAME='your-account' \
  --from-literal=AZURE_STORAGE_ACCOUNT_KEY='your-key' \
  -n botbox
```

### Step 3: Update K8s Manifests
Edit `k8s/*.yaml` files and replace:
- `your-secret-key-*` with actual values
- `your-account-*` with Azure account details
- Image registry URLs if using private registry

### Step 4: Deploy Services
```bash
# Create Azure Database for PostgreSQL
az postgres server create \
  --resource-group botbox-rg \
  --name botbox-db-server \
  --admin-user dbadmin \
  --admin-password 'your-secure-password'

# Get K8s cluster credentials
kubectl config use-context botbox-aks

# Apply K8s manifests
kubectl apply -f k8s/secret.yaml -n botbox
kubectl apply -f k8s/configmap.yaml -n botbox
kubectl apply -f k8s/db-pvc.yaml -n botbox
kubectl apply -f k8s/db-service.yaml -n botbox
kubectl apply -f k8s/db-deployment.yaml -n botbox
kubectl apply -f k8s/ollama-pvc.yaml -n botbox
kubectl apply -f k8s/ollama-service.yaml -n botbox
kubectl apply -f k8s/ollama-deployment.yaml -n botbox
kubectl apply -f k8s/web-deployment.yaml -n botbox
kubectl apply -f k8s/web-service.yaml -n botbox
kubectl apply -f k8s/serviceaccount.yaml -n botbox

# Wait for pods to be ready
kubectl get pods -n botbox -w

# Check deployment status
kubectl describe deployment web -n botbox
```

### Step 5: Access Application
```bash
# Get service IP
kubectl get svc -n botbox

# Port forward for local testing
kubectl port-forward svc/web 8000:8000 -n botbox
```

---

## 📊 Data Loading & Scraping

### Understanding the Data Flow
```
1. Web Scraper (Playwright/BeautifulSoup)
   ↓
2. JSON Files (data/acibadem_complete_data.json)
   ↓
3. DataLoader
   ↓
4. Django Models
   ↓
5. PostgreSQL Database
```

### Manual Data Loading

#### Option 1: Using Management Command
```bash
docker exec botbox_web python manage.py scrape_acibadem --headless
```

#### Option 2: Using API Endpoint
```bash
# Trigger scrape
curl -X POST http://localhost:8000/api/scrape/trigger/ \
  -H "Authorization: Bearer your_token"

# Check status
curl http://localhost:8000/api/scrape/status/

# View database stats
curl http://localhost:8000/api/data/stats/
```

#### Option 3: Django Shell
```bash
docker exec -it botbox_web python manage.py shell

>>> from scraper.data_loader import DataLoader
>>> loader = DataLoader('data/acibadem_complete_data.json')
>>> loader.load_json()
>>> loader.load_into_db()
```

### Viewing Loaded Data
```bash
# Django admin panel
http://localhost:8000/admin

# PostgreSQL query
docker exec -it botbox_db psql -U postgres -d botboxdb -c "
  SELECT COUNT(*) as programs FROM chat_program;
  SELECT COUNT(*) as courses FROM chat_course;
  SELECT COUNT(*) as departments FROM chat_department;
"
```

### Database Schema
```
UniversityInfo
  - title
  - description
  - mission
  - vision
  - phone
  - email

Department
  - name
  - description
  - email
  - phone
  - link
  - source

Program
  - name
  - level (Bachelor/Master/PhD/Certificate)
  - duration
  - department
  - description
  - sources (JSON)

Course
  - code
  - name
  - credits
  - type
  - source

ChatMessage
  - question
  - answer
  - sources (JSON)
  - confidence
```

---

## 🔧 Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker-compose logs botbox_web
docker-compose restart

# Nuclear option
docker-compose down -v  # Remove volumes too
docker-compose up -d
```

**Port already in use:**
```bash
# Windows
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process

# WSL/Linux
lsof -i :8000
kill -9 <PID>
```

### Database Issues

**Migrations failed:**
```bash
docker exec botbox_web python manage.py makemigrations
docker exec botbox_web python manage.py migrate --fake
docker exec botbox_web python manage.py migrate
```

**Can't connect to database:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec botbox_db pg_isready
```

### Ollama Issues

**Model not loading:**
```bash
# SSH into Ollama container
docker exec -it botbox_ollama /bin/bash

# Pull mistral model manually
ollama pull mistral

# Check loaded models
ollama ls
```

**Connection error from web:**
```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Check docker network
docker network inspect botbox_default
```

### Kubernetes Issues

**Pod stuck in pending:**
```bash
kubectl describe pod <pod-name> -n botbox
kubectl logs <pod-name> -n botbox
```

**PersistentVolume not mounting:**
```bash
kubectl get pvc -n botbox
kubectl describe pvc ollama-pvc -n botbox
```

**Check service connectivity:**
```bash
kubectl exec -it <pod-name> -n botbox -- /bin/sh
curl http://ollama:11434/
curl postgresql://db:5432/
```

---

## 📝 Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| DEBUG | Django debug mode | True/False |
| DJANGO_SECRET_KEY | Django secret key | random-secret-key |
| POSTGRES_DB | Database name | botboxdb |
| POSTGRES_USER | DB username | postgres |
| POSTGRES_PASSWORD | DB password | secure_password |
| OLLAMA_URL | Ollama service URL | http://ollama:11434 |
| OLLAMA_MODEL | LLM model name | mistral |
| AZURE_STORAGE_ACCOUNT_NAME | Azure storage account | myaccount |
| AZURE_STORAGE_ACCOUNT_KEY | Azure storage key | access-key |

---

## 🔐 Security Notes

### For Production
1. **Never commit .env files** - Already in .gitignore
2. **Use Kubernetes Secrets** - Defined in `k8s/secret.yaml`
3. **Enable HTTPS** - Add ingress with TLS
4. **Disable DEBUG** - Set to False
5. **Use strong passwords** - For databases
6. **Setup Azure Key Vault** - For secret management

### Example Production Secret Creation
```bash
kubectl create secret generic botbox-secrets \
  --from-file=django-secret-key=/path/to/secret \
  --from-file=db-password=/path/to/db-pass \
  -n botbox
```

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Check database: `docker exec botbox_db psql -U postgres`
3. Test APIs: Use Postman or curl
4. Review Django admin: http://localhost:8000/admin
