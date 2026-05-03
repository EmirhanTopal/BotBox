# ⚡ Ollama Connection - Action Plan

## What to Do NOW

### Step 1: Restart Everything (2 minutes)
```bash
# Go to your project directory
cd c:\Users\asli\Desktop\Proje\BotBox

# Stop everything
docker-compose down

# Start fresh with fixes
docker-compose up -d

# Wait 30-60 seconds (Ollama needs time to load)
```

### Step 2: Verify Connection (30 seconds)
```bash
# Test health check
curl http://localhost:8000/api/health/

# ✅ If you see "status": "ok" → It's working!
# ❌ If you see an error → Check troubleshooting below
```

### Step 3: Test in Browser (1 minute)
```
1. Open: http://localhost:8000
2. Click a suggested question
3. You should get an AI response from Ollama/Mistral
```

### Step 4: Check Logs (If needed)
```bash
# If not working, check what's wrong
docker logs botbox_web

# Look for "Cannot connect to Ollama" or other errors
```

---

## ✅ What Was Fixed

| Issue | Status |
|-------|--------|
| Chat endpoint broken | ✅ Fixed |
| Session not saving | ✅ Fixed |
| Ollama not connected | ✅ Fixed |
| No error messages | ✅ Fixed |
| No health check | ✅ Fixed |

---

## 📊 Expected Results

### Health Check (Working)
```
curl http://localhost:8000/api/health/

Response:
{
  "status": "ok",
  "database": {"status": "ok", "programs": 156, ...},
  "ollama": {"status": "ok", "model": "mistral", ...}
}
```

### Chat Response (Working)
```
Browser sends: "What programs does Acıbadem offer?"

You get back:
- Answer from Mistral model ✅
- Confidence score ✅
- Data sources used ✅
```

---

## 🆘 Quick Troubleshooting

### Problem: Health check returns error
```bash
# Solution 1: Restart Ollama
docker restart botbox_ollama
sleep 30
curl http://localhost:8000/api/health/

# Solution 2: Restart everything
docker-compose down
docker-compose up -d
sleep 60
curl http://localhost:8000/api/health/
```

### Problem: Chat returns "Internal server error"
```bash
# Check logs
docker logs botbox_web

# Common issues:
# - If "No such table": Run migrations
docker exec botbox_web python manage.py migrate

# - If "Cannot connect": Ollama not running
docker restart botbox_ollama

# - If other error: Restart everything
docker-compose restart
```

### Problem: Page shows "Service unavailable"
```bash
# Container not running
docker ps

# Start it
docker-compose up -d

# Wait for startup
sleep 60
```

---

## 📋 Testing Checklist

After restart, verify:
- [ ] `docker ps` shows all 3 containers running
- [ ] `curl http://localhost:8000/api/health/` shows `"status": "ok"`
- [ ] `curl http://localhost:11434/api/tags` shows available models
- [ ] Browser at http://localhost:8000 loads without errors
- [ ] Can send a message and get a response back
- [ ] Response comes from Ollama (AI-generated, not just database)

---

## 📖 Full Documentation

- **`OLLAMA_FIXED.md`** ← Main explanation of fixes
- **`OLLAMA_CONNECTION_DEBUG.md`** ← Detailed debugging guide
- **`SETUP_GUIDE.md`** ← General setup instructions
- **`DATA_LOADING_GUIDE.md`** ← Data management

---

## 🎯 Next Steps After Verifying

1. **Test Thoroughly**: Ask various questions about Acıbadem University
2. **Check Browser Console**: Open DevTools (F12) to see any JavaScript errors
3. **Monitor Logs**: Watch `docker logs -f botbox_web` while testing
4. **Load More Data**: If needed, run `docker exec botbox_web python manage.py scrape_acibadem`

---

## 🚀 You're Ready!

The Ollama connection is now properly implemented. Just restart your containers and test!

**Start here:**
```bash
docker-compose down
docker-compose up -d
sleep 30
curl http://localhost:8000/api/health/
```

If health check shows "ok" → **It's working!** 🎉

Need help? Check the documentation files or troubleshooting section above.
