# BotBox - Acıbadem University AI Chatbot

A containerized AI-powered chatbot designed to answer questions about **Acıbadem University** using intelligent retrieval and a locally hosted LLM.

The system combines web scraping, vector search, and LLM integration to provide accurate, context-aware responses about university programs, departments, courses, and general information. Developed as part of the **CSE 322 – Cloud Computing** course.

---

# Project Overview

The goal of this project is to create a chatbot that can answer questions about Acıbadem University such as:

* Academic programs
* Course information
* Campus facilities
* Admissions
* Contact information
* General university information

The chatbot retrieves relevant information from collected website data and uses a locally hosted LLM to generate natural-language responses.

---

# System Architecture

The system consists of three main services running in separate Docker containers:

```
User
  ↓
Frontend (Chat Interface)
  ↓
Django Backend API
  ↓
Retrieval Service (Vector Search + FAISS)
  ↓
PostgreSQL Database + Vector Embeddings
  ↓
LLM Service (Ollama - llama3.1:8b)
```

### Services

* **Web Application**
  * Django REST API
  * Chat interface
  * Retrieval and augmented generation pipeline
  * Session and message management

* **Database**
  * PostgreSQL 15
  * Stores university data (departments, programs, courses, instructors)
  * Stores chat history and sessions
  * Vector embeddings for semantic search

* **LLM Service**
  * Ollama with llama3.1:8b (customizable)
  * Generates context-aware answers
  * Integrated via HTTP API

* **Data Pipeline**
  * Web scraper (BeautifulSoup + Playwright)
  * Data loader for database population
  * Vector embedding generation (Sentence-Transformers)

All services are orchestrated using **Docker Compose**.

---

# Key Features

* **Intelligent Retrieval**: Vector-based semantic search using FAISS and Sentence-Transformers
* **RAG Pipeline**: Retrieval-Augmented Generation for accurate, context-grounded responses
* **Multi-source Data**: Scrapes both static (BeautifulSoup) and dynamic (Playwright) university websites
* **Comprehensive Data Model**: University info, departments, programs, courses, instructors, and more
* **Conversation Management**: Session-based chat history and message threading
* **Local LLM Integration**: Ollama-based LLM with customizable models
* **REST API**: Full-featured API for chat interactions
* **Containerized**: Complete Docker Compose setup for easy deployment
* **Kubernetes Ready**: K8s manifests included for cloud deployment
* **Audit Trail**: Scraping logs for data quality tracking

---

# Project Structure

```
BotBox/

├── docker-compose.yml          # Docker Compose orchestration
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── conftest.py                 # Pytest fixtures
├── test.sh                     # Test script
│
├── scraper/                    # Web scraping module
│   ├── __init__.py
│   ├── config.py              # Scraper configuration
│   ├── acibadem_dual_scraper.py  # Main scraper (static + dynamic)
│   └── data_loader.py         # Database population
│
├── webapp/                     # Django web application
│   └── BotBoxWeb/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── manage.py
│       ├── db.sqlite3
│       ├── BotBoxWeb/         # Project settings
│       │   ├── settings.py
│       │   ├── urls.py
│       │   ├── wsgi.py
│       │   └── asgi.py
│       └── chat/              # Chat application
│           ├── models.py      # Data models
│           ├── api_views.py   # REST API endpoints
│           ├── services/      # Business logic
│           ├── urls.py
│           ├── views.py
│           └── templates/
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_acibadem_dual_scraper.py
│   ├── test_data_loader.py
│   ├── test_api.py
│   ├── test_models.py
│   ├── test_retrieval.py
│   └── test_llm_integration.py
│
├── k8s/                        # Kubernetes manifests
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── db-deployment.yaml
│   ├── db-service.yaml
│   ├── web-deployment.yaml
│   ├── web-service.yaml
│   ├── ollama-deployment.yaml
│   ├── ollama-service.yaml
│   └── serviceaccount.yaml
│
└── data/                       # Data storage
    └── acibadem_complete_data.json
```

---

# Setup Instructions

## Prerequisites

* Docker and Docker Compose
* Python 3.8+
* At least 8GB RAM for Ollama

## 1. Clone the repository

```bash
git clone <repository_url>
cd BotBox
```

## 2. Environment variables

Create a `.env` file:

```
POSTGRES_DB=botbox
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DJANGO_SECRET_KEY=your_django_secret_key
OLLAMA_MODEL=llama3.1:8b
```

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 4. Build and start containers

```bash
docker-compose up --build
```

This starts:
* Django web application (port 8000)
* PostgreSQL database
* Ollama LLM service (port 11434)

## 5. Run database migrations

```bash
docker-compose exec web python manage.py migrate
```

Create a superuser:

```bash
docker-compose exec web python manage.py createsuperuser
```

## 6. Populate database with scraped data

```bash
docker-compose exec web python -m scraper.data_loader
```

## 7. Access the application

* **Web Interface**: http://localhost:8000
* **Admin Panel**: http://localhost:8000/admin
* **API**: http://localhost:8000/api/

## Kubernetes Deployment

For Kubernetes deployment, use the provided manifests:

```bash
kubectl apply -f k8s/
```

Make sure to configure the secrets and configmaps appropriately.

---

# Chat API

The REST API provides endpoints for chat interactions:

### Chat Endpoint

```
POST /api/chat/
```

**Request:**
```json
{
  "message": "Where is Acıbadem University located?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "session_id": "session-uuid",
  "message": {
    "id": "msg-uuid",
    "content": "Acıbadem University is located in Istanbul, Turkey...",
    "timestamp": "2026-05-12T10:30:00Z"
  },
  "retrieval_context": {
    "sources": 3,
    "confidence": 0.95
  }
}
```

### Endpoints

* `POST /api/chat/` - Send a message and get a response
* `GET /api/sessions/` - List chat sessions
* `GET /api/sessions/{session_id}/` - Get session messages
* `DELETE /api/sessions/{session_id}/` - Delete a session

---

# Data Model

BotBox uses a comprehensive data model to represent Acıbadem University information:

* **UniversityInfo**: General university metadata
* **Department**: Faculties and institutes
* **Program**: Academic degrees (Bachelor, Master, PhD, Associate)
* **Course**: Courses linked to programs and semesters
* **Instructor**: Faculty members with expertise areas
* **ChatSession**: Conversation threads
* **ChatMessage**: Individual messages in conversations
* **ScrapingLog**: Audit trail for data collection

---

# Data Sources

BotBox scrapes from two Acıbadem University sources:

1. **Static Pages** (BeautifulSoup)
   * https://www.acibadem.edu.tr
   * General university information, programs, contact details

2. **Dynamic Pages** (Playwright)
   * https://obs.acibadem.edu.tr
   * Requires JavaScript rendering for dynamic content

Data collection is performed responsibly with appropriate delays between requests.

---

# AI Integration

BotBox implements a **Retrieval-Augmented Generation (RAG)** pipeline:

1. **Vector Embedding**: User queries and database content are embedded using Sentence-Transformers
2. **Semantic Search**: FAISS performs fast similarity search on vector embeddings
3. **Context Retrieval**: Top-K relevant documents are retrieved from PostgreSQL
4. **Prompt Augmentation**: Retrieved context is combined with the user query
5. **LLM Generation**: Ollama generates contextual answers using the augmented prompt

### Supported LLM Models

* **Default**: llama3.1:8b
* **Alternatives**: Mistral, Gemma, Phi-3, Qwen (all via Ollama)

### Example Prompt Structure

```
You are an assistant for Acıbadem University.
Use the provided context to answer the question accurately.
If the context doesn't contain relevant information, 
state that you don't have that information.

Context:
{retrieved_context}

Question:
{user_question}
```

---

# Development Workflow

1. **Setup**: Clone repository and configure environment
2. **Dependencies**: Install Python packages and set up Docker
3. **Database**: Create PostgreSQL database and initialize schema
4. **Data Pipeline**: Run scraper and data loader
5. **LLM Service**: Start Ollama with desired model
6. **Testing**: Run test suite to validate components
7. **API Development**: Implement and test chat endpoints
8. **Frontend**: Build user interface for chat interaction
9. **Integration**: Connect all components via Docker Compose
10. **Deployment**: Deploy to Docker Compose or Kubernetes

---

# Testing

BotBox includes comprehensive test coverage:

* **Scraper Tests**: Validate web scraping functionality
* **Data Loader Tests**: Verify database population
* **API Tests**: Test all REST endpoints
* **Model Tests**: Validate data models and relationships
* **Retrieval Tests**: Test vector search and RAG pipeline
* **LLM Integration Tests**: Verify LLM service integration

Run tests with:
```
pytest
```

Or use the provided test script:
```
./test.sh
```

---

# Evaluation Criteria

The system will be evaluated on:

* **Data Accuracy**: Correctness of scraped information
* **Response Quality**: Relevance and accuracy of LLM answers
* **Coverage**: Breadth of university information available
* **Performance**: Response time and retrieval efficiency
* **User Experience**: Chat interface usability
* **Reliability**: System uptime and error handling

---

# Technologies Used

* **Backend**: Python 3.x, Django 5.2
* **Database**: PostgreSQL 15
* **LLM**: Ollama (llama3.1:8b)
* **Vector Search**: FAISS, Sentence-Transformers
* **Web Scraping**: BeautifulSoup 4, Playwright
* **API**: Django REST Framework
* **Testing**: pytest, pytest-django
* **Containerization**: Docker, Docker Compose
* **Orchestration**: Kubernetes
* **Frontend**: HTML, CSS, JavaScript

---

# Future Improvements

* Enhanced RAG pipeline with advanced chunking strategies
* Cloud deployment (AWS, Azure, GCP)
* Advanced monitoring and logging
* Multi-language support
* Caching layer for improved response times
* User feedback mechanism for continuous improvement
* Advanced analytics dashboard

---

# License

This project is developed for educational purposes as part of the CSE 322 – Cloud Computing course at Acıbadem University.
