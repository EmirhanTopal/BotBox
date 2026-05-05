FROM mcr.microsoft.com/playwright/python:v1.59.0-jammy

WORKDIR /app

ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install sentence-transformers faiss-cpu

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]