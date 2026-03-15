# ACU AI Chatbot

A containerized AI-powered chatbot designed to answer questions about **Acıbadem University** using publicly available information from the university’s websites.

This project was developed as part of the **CSE 322 – Cloud Computing** course. The system integrates a locally running Large Language Model (LLM) with a Django-based web application and a PostgreSQL database. The entire system is containerized using **Docker** and **Docker Compose**.

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
PostgreSQL Database
  ↓
LLM Service (Ollama)
```

### Containers

* **Web Application**

  * Django backend
  * REST API
  * Chat interface
  * Data retrieval and prompt generation

* **Database**

  * PostgreSQL
  * Stores scraped website content
  * Stores chat history

* **LLM Service**

  * Runs a local open-source model using Ollama
  * Generates answers based on context provided by the backend

All services are orchestrated using **Docker Compose**.

---

# Key Features

* AI-powered chatbot for Acıbadem University information
* Django web application with chat interface
* REST API for chat requests
* Chat history stored in PostgreSQL
* Local LLM integration via HTTP API
* Containerized architecture using Docker
* Responsible scraping of publicly available university data

---

# Project Structure

```
acibadem-chatbot/

docker-compose.yml
README.md
.env.example

webapp/
│
├── Dockerfile
├── requirements.txt
├── manage.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│
├── chat/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── services/
│
├── templates/
├── static/

scraper/
│
├── scrape_acibadem.py
├── data_loader.py

docs/
│
└── report.pdf
```

---

# Setup Instructions

## 1. Clone the repository

```
git clone <repository_url>
cd acibadem-chatbot
```

---

## 2. Environment variables

Create a `.env` file based on the example:

```
cp .env.example .env
```

Example environment variables:

```
POSTGRES_DB=chatbot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DJANGO_SECRET_KEY=changeme
```

---

## 3. Build and start containers

Start the entire system using Docker Compose:

```
docker-compose up --build
```

This will start:

* Django web application
* PostgreSQL database
* LLM service (Ollama)

---

## 4. Run database migrations

Inside the Django container:

```
docker-compose exec web python manage.py migrate
```

Create an admin user:

```
docker-compose exec web python manage.py createsuperuser
```

---

## 5. Access the application

Web interface:

```
http://localhost:8000
```

Django admin panel:

```
http://localhost:8000/admin
```

---

# Chat API

Example API endpoint:

```
POST /api/chat/
```

Request:

```
{
  "question": "Where is Acibadem University located?"
}
```

Response:

```
{
  "answer": "Acibadem University is located in Istanbul, Turkey..."
}
```

---

# Data Collection

The chatbot uses publicly available information from the following sources:

* https://www.acibadem.edu.tr
* https://obs.acibadem.edu.tr

Data is collected using Python scraping tools such as:

* requests
* BeautifulSoup
* Selenium (if necessary for dynamic pages)

Scraping is performed responsibly with appropriate delays between requests.

---

# AI Integration

The chatbot uses a **locally running open-source LLM** served through Ollama.

Example models:

* Mistral
* Gemma
* Phi-3
* Qwen

The Django backend sends prompts to the LLM service using an HTTP API.

Example prompt structure:

```
You are an assistant for Acibadem University.

Use the following context to answer the question.

Context:
{retrieved_information}

Question:
{user_question}
```

---

# Development Workflow

Recommended development steps:

1. Set up Docker environment
2. Initialize Django project
3. Configure PostgreSQL connection
4. Implement basic chat API
5. Build frontend chat interface
6. Implement chat history storage
7. Collect website data via scraper
8. Implement retrieval mechanism
9. Integrate local LLM service
10. Improve prompts and answer quality

---

# Team Responsibilities

Example task distribution:

Backend Development

* Django API
* Database models
* Retrieval system
* Scraping scripts

AI Integration

* LLM model selection
* Ollama setup
* Prompt engineering
* Model evaluation

Frontend Development

* Chat interface
* API integration
* UI improvements

---

# Evaluation

The chatbot will be evaluated using sample questions about:

* University information
* Departments and programs
* Course descriptions
* Admission details
* Campus life

Accuracy and relevance of responses will be analyzed in the final report.

---

# Technologies Used

* Python
* Django
* PostgreSQL
* Docker
* Docker Compose
* Ollama
* HTML / CSS / JavaScript
* BeautifulSoup

---

# Future Improvements

Possible enhancements include:

* Vector database for semantic search
* RAG (Retrieval Augmented Generation)
* Cloud deployment
* Kubernetes deployment
* Streaming responses
* Monitoring and logging

---

# License

This project is developed for educational purposes as part of the CSE 322 course.
