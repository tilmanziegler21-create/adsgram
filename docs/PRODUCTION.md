# Production Checklist — TelegramFlow

## 1. Smart-Shield (задержки)

**Удалить E2E-ускорения** из `.env` перед деплоем:

```env
# НЕ использовать в production:
# SMART_SHIELD_MIN_DELAY=3
# SMART_SHIELD_MAX_DELAY=8

# Штатные значения (по умолчанию):
SMART_SHIELD_MIN_DELAY=30
SMART_SHIELD_MAX_DELAY=120
```

При `ENVIRONMENT=production` backend и workers **не запустятся**, если `SMART_SHIELD_MIN_DELAY < 30` или `SMART_SHIELD_MAX_DELAY < 60`.

## 2. Admin API

```env
ENVIRONMENT=production
ENABLE_ADMIN_API=false
DEBUG=false
```

- Роуты `/api/admin/*` **не регистрируются**, если не `development` + `ENABLE_ADMIN_API=true`.
- Дополнительная проверка в каждом handler — 403 при нарушении.

## 3. Мониторинг сессий

- Celery Beat: задача `workers.monitor_sessions` каждые 5 минут.
- Проверяет: наличие `.session`, `get_me()`, ошибки:
  - `FloodWait` → `flood_wait` + ротация
  - `UserDeactivated` / `UserDeactivatedBan` → `banned`
  - `AuthKeyUnregistered` / `AuthKeyDuplicated` → `disabled`

Запуск beat в Docker:

```bash
docker compose up beat
```

Ручной прогон:

```bash
celery -A workers.celery_app.celery_app call workers.monitor_sessions
```

## 4. Сессии

- Файлы: `data/sessions/<session_path>.session`
- Отсутствующий файл → статус `disabled`
- Не коммитить `.session` в git
