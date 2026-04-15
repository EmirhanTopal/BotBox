
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY webapp/BotBoxWeb/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt



COPY . /app
WORKDIR /app/webapp/BotBoxWeb
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]