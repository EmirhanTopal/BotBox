# 🚀 BotBox Quick Reference Card

## Your Setup (Windows + WSL + Docker Desktop)

```
Windows PowerShell / Terminal
    ↓
docker-compose up -d
    ↓
Docker Desktop
    ↓
WSL 2 (Ubuntu)
    ↓
3 Containers:
├─ botbox_web (Django) → http://localhost:8000
├─ botbox_db (PostgreSQL) → localhost:5432
└─ botbox_ollama (Mistral LLM) → http://localhost:11434
```

---

## Essential Commands

### Start Everything
```bash
docker-compose up -d           # Start services
docker-compose logs -f         # View logs
docker-compose down            # Stop services
```

### Load Data
```bash
# Option 1 (Recommended)
docker exec botbox_web python manage.py scrape_acibadem

# Option 2 (API)
curl -X POST http://localhost:8000/api/scrape/trigger/

# Check status
curl http://localhost:8000/api/data/stats/
```

### Access Services
```
Web Application:   http://localhost:8000
Admin Panel:       http://localhost:8000/admin
API Endpoint:      http://localhost:8000/api/
Database Shell:    docker exec -it botbox_db psql -U postgres -d botboxdb
Ollama API:        http://localhost:11434/api/tags
```

### Debugging
```bash
docker-compose logs botbox_web     # Web logs
docker-compose logs botbox_db      # Database logs
docker-compose logs botbox_ollama  # Ollama logs
docker ps                          # List containers
docker exec botbox_web python manage.py shell  # Django shell
```

---

## File Locations

```
Repository Root (BotBox/)
├── .env.example              ← COPY TO .env
├── docker-compose.yml        ← Local setup
├── QUICK_ANSWER.md          ← START HERE ⭐
├── SETUP_GUIDE.md           ← Detailed setup
├── DATA_LOADING_GUIDE.md    ← Data management
├── PROJECT_STATUS.md        ← Full report

Key Files:
├── webapp/BotBoxWeb/chat/models.py          ← Database schema
├── webapp/BotBoxWeb/chat/services/llm_integration.py  ← LLM config
├── scraper/data_loader.py   ← Data loading logic
└── data/acibadem_complete_data.json         ← Scraped data
```

---

## Environment Variables

```env
POSTGRES_DB=botboxdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

DEBUG=True
DJANGO_SECRET_KEY=your_django_secret_key

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=mistral
```

---

## Database Tables

| Table | Purpose | Count |
|-------|---------|-------|
| chat_universityinfo | University info | 1 |
| chat_department | Departments | 15+ |
| chat_program | Academic programs | 156+ |
| chat_course | Courses | 342+ |
| chat_chatmessage | Chat history | Growing |

---

## API Endpoints

```bash
# Data Management
POST   /api/scrape/trigger/       ← Trigger scraping
GET    /api/scrape/status/        ← Scraping status
GET    /api/data/stats/           ← Database statistics

# Chat Interface
GET    /                          ← Web interface
POST   /api/chat/<session_id>/    ← Chat API
```

---

## Kubernetes Commands (Azure)

```bash
# Setup
az aks create --resource-group botbox-rg --name botbox-aks
az aks get-credentials --resource-group botbox-rg --name botbox-aks

# Deploy
kubectl create namespace botbox
kubectl create secret generic botbox-secrets ... -n botbox
kubectl apply -f k8s/ -n botbox

# Debug
kubectl get pods -n botbox
kubectl logs -f deployment/web -n botbox
kubectl port-forward svc/web 8000:8000 -n botbox
```

---

## Common Issues & Fixes

### Port Already in Use
```bash
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
```

### Container Won't Start
```bash
docker-compose down -v
docker-compose up -d
```

### Model Not Loading
```bash
docker exec botbox_ollama ollama pull mistral
```

### Database Error
```bash
docker exec botbox_web python manage.py migrate --fake
docker exec botbox_web python manage.py migrate
```

---

## Architecture at a Glance

```
┌──────────────┐
│  Your Browser│
└──────┬───────┘
       │ http://localhost:8000
       ↓
┌────────────────────────────────┐
│     Django Web Server           │
│  ├─ Chat Interface (HTML)       │
│  ├─ API Endpoints               │
│  └─ LLM Service Integration     │
└────────┬───────────────┬────────┘
         │               │
         ↓               ↓
    ┌────────────┐  ┌──────────────┐
    │ PostgreSQL │  │ Ollama+       │
    │ Database   │  │ Mistral Model │
    │ (Data)     │  │ (Intelligence)│
    └────────────┘  └──────────────┘
```

---

## Data Flow

```
1. User Question
   ↓
2. Django retrieves data from PostgreSQL
   ↓
3. Context sent to Ollama/Mistral
   ↓
4. Mistral generates response
   ↓
5. Response saved to ChatMessage table
   ↓
6. User sees answer
```

---

## Setup Checklist

```bash
□ Copy .env.example to .env
□ Edit .env with your passwords
□ docker-compose up -d
□ docker exec botbox_web python manage.py migrate
□ docker exec botbox_web python manage.py scrape_acibadem
□ Visit http://localhost:8000
□ Test chatbot
□ Check admin: http://localhost:8000/admin
```

---

## Important Notes

⚠️ **Remember**
- Never commit `.env` file (it's in .gitignore)
- Change `POSTGRES_PASSWORD` in production
- Change `DJANGO_SECRET_KEY` in production
- Ollama model downloads automatically (~7GB)
- First run takes 30-60 seconds to start

✅ **You Have**
- Docker Compose setup (ready to use)
- K8s manifests (ready for Azure AKS)
- Data loading pipeline (fully functional)
- API endpoints (for programmatic access)
- Complete documentation (3 detailed guides)

---

## Where to Start

1. **⭐ Read**: `QUICK_ANSWER.md` (5 minutes)
2. **⚙️ Setup**: Follow Quick Start section
3. **📖 Learn**: `SETUP_GUIDE.md` for details
4. **💾 Manage**: `DATA_LOADING_GUIDE.md` for data

---

## Questions?

All answers are in the docs:
- **Setup issues** → `SETUP_GUIDE.md` → Troubleshooting
- **Data issues** → `DATA_LOADING_GUIDE.md` → Troubleshooting
- **General info** → `QUICK_ANSWER.md`
- **Full report** → `PROJECT_STATUS.md`

---

**You're all set! Everything is configured and documented. Just run the Quick Start commands and you'll have a working chatbot! 🚀**
