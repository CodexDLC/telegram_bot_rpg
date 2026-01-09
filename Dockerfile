FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей (если нужны для psycopg2/asyncpg)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# По умолчанию ничего не запускаем, ждем команду из compose
