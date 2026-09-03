-- E2E seed for TelegramFlow
-- Usage: docker exec -i teleflow-postgres psql -U teleflow -d teleflow < scripts/seed_e2e.sql
-- Replace proxy credentials and session_path before running.

BEGIN;

INSERT INTO users (id, email, hashed_password, is_active)
VALUES ('11111111-1111-1111-1111-111111111111', 'e2e@test.local', 'e2e-test-not-used', true)
ON CONFLICT (email) DO NOTHING;

INSERT INTO proxies (id, host, port, protocol, username, password, is_active)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '127.0.0.1',
    1080,
    'socks5',
    'PROXY_USER',
    'PROXY_PASS',
    true
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO telegram_accounts (
    id,
    phone,
    session_path,
    status,
    proxy_id,
    daily_sent_count,
    daily_limit
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '+10000000000',
    'test_session',
    'reserved',
    '22222222-2222-2222-2222-222222222222',
    0,
    40
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- Expected session file: data/sessions/test_session.session
