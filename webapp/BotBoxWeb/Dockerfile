FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
```

---

### 3. `webapp/requirements.txt`
```
Django==4.2
psycopg2-binary==2.9.9
requests==2.31.0
djangorestframework==3.14.0