# Adsgram — всё в одном контейнере: API + бот + фронтенд
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=""
ENV NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=$NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STATIC_DIR=/app/static

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY bot/requirements.txt /app/bot-requirements.txt
RUN pip install --no-cache-dir -r /app/bot-requirements.txt

COPY backend/app /app/backend/app
COPY bot/bot /app/bot
COPY docker/start.sh /app/start.sh
COPY --from=frontend-builder /app/frontend/out /app/static

RUN chmod +x /app/start.sh

WORKDIR /app/backend
EXPOSE 8000

CMD ["/app/start.sh"]
