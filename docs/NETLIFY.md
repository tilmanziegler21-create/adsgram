# Деплой frontend на Netlify

Сайт собирается как **статический экспорт** (`out/`) — без серверных функций, быстро и бесплатно.

## 1. Подготовка backend

Backend (FastAPI + bot) должен быть доступен по HTTPS, например:
- Railway / Fly.io / Render / VPS
- Локально для теста: `ngrok http 8000`

В `.env` backend добавьте домен Netlify в CORS:

```env
CORS_ORIGINS=["https://your-site.netlify.app","http://localhost:3000"]
```

## 2. Netlify (через Git)

1. [app.netlify.com](https://app.netlify.com) → **Add new site** → Import from Git  
2. **Base directory:** `frontend`  
3. Build command и publish подтянутся из `frontend/netlify.toml`  
4. В `frontend/netlify.toml` замените `YOUR-BACKEND-URL` на реальный URL API  

Или в Netlify UI → **Site configuration** → **Redirects** добавьте:

```
/api/*  https://api.example.com/api/:splat  200!
```

## 3. Переменные окружения (Netlify UI)

| Переменная | Значение |
| :--- | :--- |
| `NEXT_PUBLIC_API_URL` | оставить **пустой** (для прокси `/api`) |

Альтернатива без прокси: `NEXT_PUBLIC_API_URL=https://api.example.com` + CORS на backend.

## 4. Деплой без Git (CLI)

```bash
npm install -g netlify-cli
cd frontend
# отредактируйте netlify.toml (URL backend)
npm run build
netlify deploy --prod --dir=out
```

## 5. Локальная разработка

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Схема

```text
Пользователь → your-site.netlify.app
                    │
                    ├─ /          статика (каталог)
                    ├─ /buy/      оформление заказа
                    └─ /api/*  →  proxy → ваш FastAPI backend
```

Backend и Telegram-бот Netlify **не** хостит — только фронтенд.
