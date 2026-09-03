# Маркетплейс рекламы в Telegram-каналах

## Сценарий

1. Владелец добавляет бота в канал/группу **админом с правом постить**
2. Бот регистрирует канал → появляется в каталоге
3. Рекламодатель видит каталог: статистика, рейтинг, цены по срокам
4. Создаёт заказ → оплачивает **тестовым балансом**
5. Владельцу приходит сообщение в Telegram с превью поста
6. Владелец жмёт **Одобрить** → ему начисляется баланс, бот публикует пост

## API

| Метод | Эндпоинт | Описание |
| :--- | :--- | :--- |
| GET | `/api/marketplace/channels` | Каталог каналов |
| GET | `/api/marketplace/channels/{id}` | Карточка канала |
| POST | `/api/marketplace/orders` | Создать заказ |
| POST | `/api/marketplace/orders/{id}/pay` | Оплатить с баланса |
| POST | `/api/marketplace/orders/{id}/approve` | Одобрить (владелец) |
| POST | `/api/marketplace/orders/{id}/reject` | Отклонить |
| GET | `/api/wallet/balance?user_id=` | Баланс |
| POST | `/api/wallet/topup-test` | Тестовое пополнение (dev) |

## Быстрый тест

```bash
# 1. TELEGRAM_BOT_TOKEN в .env, docker compose up
# 2. Добавить бота админом в канал
# 3. Создать пользователя и пополнить баланс
curl -X POST http://localhost:8000/api/admin/users -H "Content-Type: application/json" -d '{"email":"adv@test.local"}'
curl -X POST "http://localhost:8000/api/wallet/topup-test" -H "Content-Type: application/json" -d '{"user_id":"<uuid>","amount":10000}'
# 4. Каталог
curl http://localhost:8000/api/marketplace/channels
# 5. Заказ + оплата
curl -X POST http://localhost:8000/api/marketplace/orders -H "Content-Type: application/json" -d '{
  "advertiser_user_id":"<uuid>",
  "channel_id":"<channel_uuid>",
  "post_text":"Тестовый рекламный пост",
  "duration_hours": 24
}'
curl -X POST "http://localhost:8000/api/marketplace/orders/<order_id>/pay?advertiser_user_id=<uuid>"
```

Владелец подтверждает в Telegram-кнопках бота.

## Цены по умолчанию (на канал)

| Срок | Цена (кредиты) |
| :--- | :--- |
| 24 ч | 500 |
| 48 ч | 900 |
| 7 дней | 2500 |

## Запуск сайта

```bash
# Backend + bot + frontend
docker compose up --build

# Или локально frontend:
cd frontend && cp .env.local.example .env.local && npm run dev
```

Сайт: http://localhost:3000

## Страницы

| URL | Описание |
| :--- | :--- |
| `/` | Каталог каналов |
| `/channels/{id}` | Оформление рекламы |
| `/wallet` | Баланс и тестовое пополнение |
| `/orders` | Мои заказы |
| `/login` | Вход по email (dev) |

## Что ещё не сделано

- ~~UI каталога и оформления заказа (frontend)~~ ✅
- Автоудаление поста по `expires_at`
- Реальная оплата (CryptoBot)
- Привязка `telegram_id` к аккаунту пользователя
