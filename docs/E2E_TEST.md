# E2E Test Cycle — TelegramFlow

Сквозная проверка воронки: URL → аудитория → запуск кампании.

## 1. Конфигурация `.env`

```bash
cp .env.example .env
```

Заполнить:

```env
TELEGRAM_API_ID=<your_api_id>
TELEGRAM_API_HASH=<your_api_hash>
DEEPSEEK_API_KEY=<your_key>
# или: LLM_PROVIDER=openai + OPENAI_API_KEY

# Для ускорения E2E (только development, удалить перед production):
# SMART_SHIELD_MIN_DELAY=3
# SMART_SHIELD_MAX_DELAY=8
```

## 2. Сессия и прокси

### 2.1. Файл сессии

Поместить рабочий `.session` в локальную директорию:

```text
data/sessions/test_session.session
```

`session_path` в БД = имя **без** расширения (`test_session`).

### 2.2. Вариант A — SQL seed

Отредактировать `scripts/seed_e2e.sql` (прокси, телефон) и выполнить:

```bash
docker compose up -d postgres
docker exec -i teleflow-postgres psql -U teleflow -d teleflow < scripts/seed_e2e.sql
```

Фиксированные ID для E2E:

| Сущность | UUID |
| :--- | :--- |
| User | `11111111-1111-1111-1111-111111111111` |
| Proxy | `22222222-2222-2222-2222-222222222222` |
| Account | `33333333-3333-3333-3333-333333333333` |

### 2.3. Вариант B — Admin API (development only)

```bash
curl -X POST http://localhost:8000/api/admin/users \
  -H "Content-Type: application/json" \
  -d '{"email":"e2e@test.local"}'

curl -X POST http://localhost:8000/api/admin/proxies \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":1080,"protocol":"socks5","username":"user","password":"pass"}'

curl -X POST http://localhost:8000/api/admin/telegram-accounts \
  -H "Content-Type: application/json" \
  -d '{"session_path":"test_session","phone":"+10000000000","proxy_id":"<proxy_uuid>"}'
```

## 3. Запуск стека

```bash
docker compose up --build
```

Сервисы: Postgres, Redis, Backend (`:8000`), Workers.

## 4. Тестовый прогон

### Автоматический скрипт

```bash
chmod +x scripts/e2e_funnel.sh

export KNOWLEDGE_URL="https://example.com"
export AUDIENCE_LINKS="https://t.me/telegram"
./scripts/e2e_funnel.sh
```

Скрипт выполняет все 3 шага, поллит Celery-задачи и проверяет поля в БД.

### Ручной прогон

| Шаг | Действие | Проверка |
| :--- | :--- | :--- |
| 1 | `PATCH /api/campaigns/{id}/knowledge` + `POST .../knowledge/parse` | `knowledge_base`, `knowledge_text` не пусты |
| 2 | `PATCH /api/campaigns/{id}/audience` + `POST .../audience/parse` | `target_chats` заполнен |
| 3 | `PATCH /api/campaigns/{id}/offer` + `POST .../start` | `messages_sent` > 0, Smart-Shield активен |

Статус задачи Celery:

```bash
curl http://localhost:8000/api/tasks/<task_id>
```

## 5. Типичные ошибки

| Симптом | Причина |
| :--- | :--- |
| `no_account` | Нет записи в `telegram_accounts` или аккаунт в flood_wait |
| `llm_config_error` | Пустой `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` |
| Hydrogram auth error | Неверный `.session` или API ID/Hash |
| `flood_wait` | Лимиты Telegram; ждать или ротировать аккаунт |

## 6. Перед production

См. `docs/PRODUCTION.md` — снять E2E-ускорения, `ENABLE_ADMIN_API=false`, `ENVIRONMENT=production`.
