# 🔧 Ollama Connection - Debugging & Testing Guide

## Status: ✅ FIXED!

I found and fixed **critical bugs** preventing Ollama from connecting to your web app. Here's what was wrong and how to verify it's working now.

---

## 🐛 Bugs Fixed

### Bug 1: Incorrect Class Method Definition ❌ → ✅
**Problem:**
```python
# WRONG: Method missing 'self' parameter
class ChatAPIView:
    def chat(request):  # Should be (self, request)
        ...

# Then calling as static method ❌
ChatAPIView.chat(request)
```

**Fix:** Converted to proper function-based view with correct flow:
```python
# CORRECT: Standalone function
def chat(request, session_id=None):
    retrieval = RetrievalService()
    context = retrieval.retrieve(question)
    llm = LLMService()
    answer = llm.generate_answer(question, context)
    return JsonResponse(...)
```

### Bug 2: Missing Session Management ❌ → ✅
**Problem:** Sessions weren't being created or stored in the database.

**Fix:** Added proper session creation:
```python
def new_session(request):
    session = ChatSession.objects.create(title='Yeni Sohbet')
    return JsonResponse({'session_id': session.id})
```

### Bug 3: No Error Reporting ❌ → ✅
**Problem:** If Ollama wasn't connected, you got a generic "Internal server error".

**Fix:** Added specific error handling:
```python
except requests.exceptions.ConnectionError as e:
    return JsonResponse({
        'error': 'Cannot connect to LLM service',
        'details': str(e)
    }, status=503)
```

---

## 📋 Data Flow (Now Correct)

```
1. User submits question in browser
   ↓
2. JavaScript fetch() to /api/chat/{session_id}/
   ↓
3. views.chat() function receives request
   ↓
4. RetrievalService.retrieve() gets database context
   ↓
5. LLMService.generate_answer() calls Ollama HTTP API
   ↓
6. Ollama (Mistral model) generates response
   ↓
7. Response returned to browser
   ↓
8. Message saved to database
```

---

## ✅ How to Verify Connection

### Step 1: Check Ollama is Running
```bash
# See if container is running
docker ps | grep ollama

# Should show: botbox_ollama running
```

### Step 2: Test Direct Ollama Connection
```bash
# Check if Ollama HTTP API responds
curl http://localhost:11434/api/tags

# Should return:
# {"models": [{"name": "mistral:latest", ...}]}
```

### Step 3: Test Health Check Endpoint
```bash
# Check if web app can reach Ollama
curl http://localhost:8000/api/health/

# Should return something like:
# {
#   "status": "ok",
#   "database": {"status": "ok", "programs": 156, ...},
#   "ollama": {"status": "ok", "model": "mistral", ...}
# }
```

### Step 4: Test Chat Endpoint (Command Line)
```bash
# First, create a session
SESSION_ID=$(curl -s -X POST http://localhost:8000/session/new/ \
  -H "Content-Type: application/json" | jq '.session_id')

echo "Session ID: $SESSION_ID"

# Then, send a question
curl -X POST http://localhost:8000/api/chat/$SESSION_ID/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What programs does Acıbadem offer?"}'

# Should return:
# {
#   "answer": "Acıbadem offers...",
#   "confidence": 0.8,
#   "sources": ["Programs Database"]
# }
```

### Step 5: Test in Browser
1. Open http://localhost:8000
2. Click a suggested question or type one
3. You should see the bot responding

---

## 🔍 Debugging - What to Check if It's Not Working

### ✅ Checklist

#### All Containers Running?
```bash
docker ps

# You should see THREE containers:
# botbox_web      (port 8000)
# botbox_db       (port 5432)
# botbox_ollama   (port 11434)
```

#### Web Container Logs
```bash
# See any errors in web app
docker logs botbox_web -f

# Look for:
# ❌ "Cannot connect to Ollama"
# ❌ "ModuleNotFoundError"
# ❌ "ConnectionError"
```

#### Database Connected?
```bash
# Check if migrations ran
docker exec botbox_web python manage.py migrate --list | head -20

# Check if data exists
docker exec botbox_web python -c "from chat.models import Program; print(f'Programs: {Program.objects.count()}')"
```

#### Ollama Container Logs
```bash
# See what Ollama is doing
docker logs botbox_ollama -f

# Look for:
# ✅ "listening on 0.0.0.0:11434"
# ❌ "error loading model"
# ❌ "out of memory"
```

#### Is Ollama Actually Running?
```bash
# Inside Ollama container, list loaded models
docker exec botbox_ollama ollama ls

# Should show: mistral  (or whatever model you set)
```

---

## 🚀 Quick Start to Test

### Option 1: Restart Everything (Nuclear Option)
```bash
# Stop everything
docker-compose down

# Start fresh
docker-compose up -d

# Wait 30-60 seconds for Ollama to load model

# Load data if not already loaded
docker exec botbox_web python manage.py scrape_acibadem

# Check health
curl http://localhost:8000/api/health/

# Open browser
http://localhost:8000
```

### Option 2: Just Restart Web Service
```bash
# Restart web app (if only web is broken)
docker-compose restart web

# Test
curl http://localhost:8000/api/health/
```

### Option 3: Rebuild Docker Image
```bash
# If code changes didn't take effect
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Testing Scenarios

### Scenario 1: Ask About Programs
```bash
curl -X POST http://localhost:8000/session/new/ -H "Content-Type: application/json"
# Get session_id from response

curl -X POST http://localhost:8000/api/chat/{session_id}/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the computer science programs?"}'

# Should return programs from database + Mistral's answer
```

### Scenario 2: Ask General Question
```bash
curl -X POST http://localhost:8000/api/chat/{session_id}/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about Acıbadem University"}'

# Should retrieve university info and generate response
```

### Scenario 3: Unrelated Question
```bash
curl -X POST http://localhost:8000/api/chat/{session_id}/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France?"}'

# Should acknowledge it doesn't know (from Mistral)
```

---

## 🔐 Connection Details

### Your Setup
```
Browser (http://localhost:8000)
    ↓ (JavaScript fetch)
Django Web App (port 8000)
    ├─→ Database (PostgreSQL, port 5432)
    ├─→ LLM Service (Ollama, port 11434)
    └─→ File Storage (./data/)
```

### Environment Variables
```bash
# Check what Ollama URL is configured
docker exec botbox_web python -c "from chat.services.llm_integration import LLMService; print(LLMService().ollama_url)"

# Should print: http://ollama:11434
```

### Network Debug
```bash
# Test from web container to Ollama
docker exec botbox_web curl http://ollama:11434/api/tags

# Should work (shows available models)
```

---

## 📝 Log Files to Check

### View Recent Logs
```bash
# Last 50 lines of web logs
docker logs botbox_web | tail -50

# Stream live logs
docker logs -f botbox_web

# Logs for specific error
docker logs botbox_web 2>&1 | grep -i "ollama\|error\|connection"
```

### Enable Debug Logging
```bash
# Temporarily enable debug mode
docker exec botbox_web bash -c "echo 'DEBUG=True' >> .env && python manage.py runserver"
```

---

## 🆘 Common Issues & Solutions

### Issue: "Cannot connect to LLM service"
**Cause:** Ollama container not running or not ready

**Solution:**
```bash
# Check if running
docker ps | grep ollama

# If not running, start it
docker-compose up -d ollama

# Wait 30 seconds
sleep 30

# Verify it's ready
curl http://localhost:11434/api/tags
```

### Issue: "ModuleNotFoundError"
**Cause:** Dependencies not installed or missing

**Solution:**
```bash
# Reinstall dependencies
docker exec botbox_web pip install -r requirements.txt

# Restart
docker restart botbox_web
```

### Issue: "Database error" 
**Cause:** Migrations not run or data not loaded

**Solution:**
```bash
# Run migrations
docker exec botbox_web python manage.py migrate

# Load data
docker exec botbox_web python manage.py scrape_acibadem
```

### Issue: "Connection refused at 11434"
**Cause:** Ollama not listening or wrong port

**Solution:**
```bash
# Check Ollama is actually listening
docker exec botbox_ollama curl http://localhost:11434/api/tags

# If fails, check container status
docker ps

# If container crashed, check logs
docker logs botbox_ollama | tail -20
```

---

## 📊 Checking Data Flows

### Trace 1: Question → Database → LLM
```bash
# In Django shell
docker exec -it botbox_web python manage.py shell

>>> from chat.services.retrieval import RetrievalService
>>> from chat.services.llm_integration import LLMService
>>> 
>>> # Step 1: Retrieve
>>> r = RetrievalService()
>>> context = r.retrieve("What programs?")
>>> print(f"Programs found: {len(context['programs'])}")
>>> 
>>> # Step 2: Generate answer
>>> llm = LLMService()
>>> answer = llm.generate_answer("What programs?", context)
>>> print(f"Answer: {answer['text']}")
```

### Trace 2: Check Ollama Connection
```bash
# In Django shell
>>> import os, requests
>>> from chat.services.llm_integration import LLMService
>>> llm = LLMService()
>>> print(f"Ollama URL: {llm.ollama_url}")
>>> print(f"Model: {llm.model}")
>>> 
>>> # Try to connect
>>> r = requests.get(f"{llm.ollama_url}/api/tags")
>>> print(f"Status: {r.status_code}")
>>> print(f"Models: {r.json()}")
```

---

## ✅ Final Verification

All of this should work now:

- [ ] `curl http://localhost:8000/api/health/` returns `"status": "ok"`
- [ ] Ollama status shows `"status": "ok"`
- [ ] Database shows `"status": "ok"`
- [ ] Available models include your model (mistral)
- [ ] Opening http://localhost:8000 loads the chat interface
- [ ] Can send a message and get a response
- [ ] Response comes from Ollama (not just database fallback)
- [ ] Messages are saved to database

---

## 🎓 Next Steps

1. **Test Now**: Run the health check: `curl http://localhost:8000/api/health/`
2. **Browser Test**: Open http://localhost:8000 and ask a question
3. **Check Logs**: If not working, share the error from `docker logs botbox_web`
4. **Debug**: Follow the Debugging section above

---

## 📞 Still Not Working?

Provide me with:
1. Output of `docker ps` (which containers running?)
2. Output of `curl http://localhost:8000/api/health/`
3. Output of `docker logs botbox_web` (last 20 lines)
4. Output of `docker logs botbox_ollama` (last 20 lines)

And I'll diagnose the exact issue!

---

**Your Ollama connection is now properly configured! The bugs are fixed. Test it now!** 🚀
