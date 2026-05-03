# Data Loading & Integration Guide

## Overview
Your project has successfully scraped data from Acıbadem University. This guide explains how to load that data into PostgreSQL and use it in the chatbot.

---

## 📊 Data Structure

### What was Scraped
The scraper collects data into this JSON structure:
```json
{
  "static_content": {
    "general_info": { /* University metadata */ },
    "contact_info": { /* Phone, email, etc */ },
    "departments": [ /* List of departments */ ]
  },
  "dynamic_content": {
    "courses": [ /* OBS System courses */ ]
  },
  "merged_data": {
    "all_programs": [ /* All academic programs */ ],
    "all_departments": [ /* Consolidated departments */ ]
  },
  "metadata": { /* Scraping timestamps, sources */ }
}
```

### File Location
- **Scraped Data**: `data/acibadem_complete_data.json`
- **Database Models**: `webapp/BotBoxWeb/chat/models.py`
- **Data Loader**: `scraper/data_loader.py`

---

## 🔄 Loading Data into Database

### Method 1: Docker Management Command (Recommended)
```bash
# Load data into PostgreSQL via Docker container
docker exec botbox_web python manage.py scrape_acibadem

# Output will show:
# ✓ Scraping completed! Items scraped: 245
```

### Method 2: REST API Endpoint
```bash
# Trigger scraping and loading via API
curl -X POST http://localhost:8000/api/scrape/trigger/ \
  -H "Content-Type: application/json"

# Response:
# {
#   "status": "success",
#   "message": "Scraping completed",
#   "items_scraped": 245,
#   "log_id": 1
# }

# Check status
curl http://localhost:8000/api/scrape/status/

# View statistics
curl http://localhost:8000/api/data/stats/
```

### Method 3: Django Shell (Manual)
```bash
# Enter Django shell inside container
docker exec -it botbox_web python manage.py shell

# Inside shell:
>>> from scraper.data_loader import DataLoader
>>> from scraper.acibadem_dual_scraper import AcibademDualScraper
>>> 
>>> # Run scraper
>>> scraper = AcibademDualScraper(use_headless=True)
>>> data = scraper.scrape_all()
>>> scraper.save_to_json('data/acibadem_complete_data.json')
>>> 
>>> # Load into database
>>> loader = DataLoader('data/acibadem_complete_data.json')
>>> loader.load_json()
>>> loader.load_into_db()
>>> print("Data loaded successfully!")
>>>
>>> # Verify
>>> from chat.models import Program, Course, Department
>>> print(f"Programs: {Program.objects.count()}")
>>> print(f"Courses: {Course.objects.count()}")
>>> print(f"Departments: {Department.objects.count()}")
```

---

## 📋 Database Tables & Schema

### UniversityInfo
Stores general university information
```sql
SELECT * FROM chat_universityinfo;

-- Fields:
-- id, title, description, mission, vision, phone, email
-- created_at, updated_at
```

**Example:**
```python
from chat.models import UniversityInfo

uni = UniversityInfo.objects.first()
print(f"University: {uni.title}")
print(f"Phone: {uni.phone}")
print(f"Email: {uni.email}")
```

### Department
Stores all university departments
```sql
SELECT name, email, phone FROM chat_department LIMIT 5;
```

**Example:**
```python
from chat.models import Department

depts = Department.objects.all()
for dept in depts[:3]:
    print(f"{dept.name}: {dept.email}")
```

### Program
Stores academic programs (Bachelor, Master, PhD, etc.)
```sql
SELECT name, level, department FROM chat_program LIMIT 5;
```

**Example:**
```python
from chat.models import Program

# Get all master's programs
masters = Program.objects.filter(level='Master')
print(f"Found {masters.count()} master's programs")

# Search specific program
eng = Program.objects.filter(name__icontains='Engineering').first()
if eng:
    print(f"Program: {eng.name}")
    print(f"Duration: {eng.duration}")
    print(f"Department: {eng.department}")
```

### Course
Stores individual courses from OBS system
```sql
SELECT code, name, credits FROM chat_course LIMIT 5;
```

**Example:**
```python
from chat.models import Course

# Get specific course
course = Course.objects.filter(code='CS101').first()
if course:
    print(f"Course: {course.name}")
    print(f"Credits: {course.credits}")
```

---

## 🤖 Using Data in Chatbot Responses

### How the Chatbot Retrieves Data

#### 1. User Asks Question
```
"What programs does Acıbadem offer?"
```

#### 2. LLM Service Retrieves Context
```python
# In chat/services/retrieval.py (needs to be created)
def retrieve_context(question):
    # Search programs
    programs = Program.objects.all()[:3]
    
    # Search departments
    departments = Department.objects.all()[:3]
    
    # Get university info
    uni_info = UniversityInfo.objects.first()
    
    return {
        'programs': [p.__dict__ for p in programs],
        'departments': [d.__dict__ for d in departments],
        'general_info': uni_info.__dict__ if uni_info else {}
    }
```

#### 3. LLM Generates Response
Using the context and Mistral model.

#### 4. Response Saved to Database
```python
ChatMessage.objects.create(
    question="What programs does Acıbadem offer?",
    answer="Acıbadem offers Bachelor, Master, and PhD programs...",
    sources=['all_programs', 'general_info'],
    confidence=0.95
)
```

### Example Interaction Flow

```python
from chat.models import ChatMessage, Program
from chat.services.llm_integration import LLMService

# User question
question = "What programs does Acıbadem offer?"

# 1. Retrieve context from database
programs = Program.objects.all()[:5]
context = {
    'programs': [
        {'name': p.name, 'level': p.level}
        for p in programs
    ]
}

# 2. Generate response using LLM
llm = LLMService()
response = llm.generate_answer(question, context)

# 3. Save to chat history
ChatMessage.objects.create(
    question=question,
    answer=response['text'],
    sources=response['sources'],
    confidence=response['confidence']
)
```

---

## 🔍 Querying Data Examples

### Find All Programs in Engineering
```python
from chat.models import Program

eng_programs = Program.objects.filter(
    department__icontains='Engineering'
)

for prog in eng_programs:
    print(f"- {prog.name} ({prog.level})")
```

### Find Contact Information
```python
from chat.models import UniversityInfo, Department

uni = UniversityInfo.objects.first()
print(f"Main Phone: {uni.phone}")
print(f"Email: {uni.email}")

# Get specific department
cs = Department.objects.filter(name__icontains='Computer').first()
if cs:
    print(f"CS Department: {cs.email}")
```

### Search Courses by Code
```python
from chat.models import Course

cs_courses = Course.objects.filter(code__startswith='CS')
print(f"Found {cs_courses.count()} Computer Science courses")

for course in cs_courses[:5]:
    print(f"- {course.code}: {course.name}")
```

### Get Chat History
```python
from chat.models import ChatMessage

# Latest 10 messages
recent = ChatMessage.objects.all()[:10]

for msg in recent:
    print(f"Q: {msg.question}")
    print(f"A: {msg.answer[:100]}...")
    print(f"Confidence: {msg.confidence}\n")
```

---

## ✅ Verification Checklist

After loading data, verify everything is working:

### 1. Check Django Admin
- Visit: http://localhost:8000/admin
- Login with admin credentials
- Check each model has data:
  - [ ] UniversityInfo (1 record)
  - [ ] Departments (10+ records)
  - [ ] Programs (50+ records)
  - [ ] Courses (100+ records)

### 2. Check API Endpoints
```bash
# Data statistics
curl http://localhost:8000/api/data/stats/

# Should return:
# {
#   "programs": 156,
#   "courses": 342,
#   "departments": 15,
#   "university_info": 1
# }
```

### 3. Test Database Connection
```bash
# From container
docker exec botbox_web python manage.py dbshell

# Run query
SELECT COUNT(*) FROM chat_program;

# Should return: count > 0
```

### 4. Test Chatbot Integration
```bash
# Visit web interface
http://localhost:8000

# Ask question like:
"What programs does Acıbadem offer?"

# Should get an answer using the loaded data
```

---

## 🛠️ Troubleshooting Data Loading

### Issue: "No data loaded" error
```
Error: No data loaded. Call load_json() first.
```
**Solution:**
```bash
# Verify JSON file exists
ls -la data/acibadem_complete_data.json

# If missing, run scraper first
docker exec botbox_web python manage.py scrape_acibadem
```

### Issue: Data not appearing in database
```bash
# Check database connection
docker exec botbox_web python manage.py dbshell

# Verify tables exist
\dt

# Count records
SELECT COUNT(*) FROM chat_program;
```

### Issue: "Database locked" error
```bash
# Restart web container
docker restart botbox_web

# Or restart all services
docker-compose restart
```

### Issue: JSON parsing error
```
JSONDecodeError: Expecting value
```
**Solution:**
- Verify `data/acibadem_complete_data.json` is valid JSON
- Check file isn't corrupted: `cat data/acibadem_complete_data.json | jq .`
- Re-run scraper to regenerate

---

## 📈 Performance Tips

### Optimize Database Queries
```python
# Use select_related for foreign keys
programs = Program.objects.select_related('department')

# Use prefetch_related for reverse relations
departments = Department.objects.prefetch_related('programs')

# Use only() to limit fields
courses = Course.objects.only('code', 'name')
```

### Add Database Indexes
```sql
-- Add index for faster searches
CREATE INDEX idx_program_level ON chat_program(level);
CREATE INDEX idx_course_code ON chat_course(code);
CREATE INDEX idx_dept_name ON chat_department(name);
```

### Batch Load Large Datasets
```python
# Instead of looping
for item in items:
    Model.objects.create(**item)

# Use bulk_create (100x faster)
Model.objects.bulk_create([
    Model(**item) for item in items
], batch_size=1000)
```

---

## 🔄 Updating Data

### Refresh All Data
```bash
# Drop all data
docker exec botbox_web python manage.py flush --no-input

# Reload from scraper
docker exec botbox_web python manage.py scrape_acibadem
```

### Incremental Update
```bash
# Run scraper (will update existing records)
docker exec botbox_web python manage.py scrape_acibadem
```

### Manual Data Entry
```python
from chat.models import Program

Program.objects.create(
    name="New Program",
    level="Master",
    department="Engineering",
    duration="2 Years",
    sources=["manual_entry"]
)
```

---

## 🔐 Data Privacy & Compliance

Your project scrapes from public university websites. Ensure:

1. **Robots.txt Compliance**
   - Check `https://www.acibadem.edu.tr/robots.txt`
   - Respect `Crawl-delay` and `User-agent` rules

2. **Data Retention Policy**
   - Document why data is collected
   - Implement data expiration
   - Allow data deletion on request

3. **GDPR Compliance** (if in EU)
   - No personal data should be stored
   - Clear privacy policy required
   - User consent for chat history

4. **Ethical Scraping**
   - Don't overload servers
   - Implement rate limiting
   - Cache responses

Example rate limiting:
```python
import time
from urllib.parse import urljoin

class EthicalScraper:
    def __init__(self, delay=1):
        self.delay = delay  # seconds between requests
        
    def scrape_page(self, url):
        time.sleep(self.delay)  # Rate limit
        # ... scraping code
```
