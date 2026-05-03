FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . .

EXPOSE 8000

