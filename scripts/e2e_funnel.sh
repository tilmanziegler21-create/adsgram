#!/usr/bin/env bash
# E2E funnel test — 3 steps (URL → audience → campaign)
set -euo pipefail

API="${API_BASE:-http://localhost:8000/api}"
POLL_INTERVAL="${POLL_INTERVAL:-3}"
POLL_TIMEOUT="${POLL_TIMEOUT:-120}"
KNOWLEDGE_URL="${KNOWLEDGE_URL:-https://example.com}"
AUDIENCE_LINKS="${AUDIENCE_LINKS:-https://t.me/telegram}"
OFFER_TEXT="${OFFER_TEXT:-Тестовое коммерческое предложение для E2E прогона.}"

poll_task() {
  local task_id="$1"
  local elapsed=0
  while (( elapsed < POLL_TIMEOUT )); do
    local resp
    resp=$(curl -sf "${API}/tasks/${task_id}")
    local status
    status=$(python3 -c "import json,sys; print(json.load(sys.stdin)['status'])" <<<"$resp")
    echo "  task ${task_id}: ${status}"
  if [[ "$status" == "SUCCESS" ]]; then
      echo "$resp"
      return 0
    fi
    if [[ "$status" == "FAILURE" ]]; then
      echo "$resp"
      return 1
    fi
    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
  done
  echo "Timeout waiting for task ${task_id}"
  return 1
}

echo "=== TelegramFlow E2E ==="
echo "API: ${API}"

USER_ID="${E2E_USER_ID:-11111111-1111-1111-1111-111111111111}"

if [[ -z "${CAMPAIGN_ID:-}" ]]; then
  echo "[setup] Creating campaign for user ${USER_ID}"
  CAMPAIGN_ID=$(curl -sf -X POST "${API}/campaigns" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"${USER_ID}\"}" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
fi
echo "Campaign: ${CAMPAIGN_ID}"

echo "[step 1] Knowledge URL + parse"
curl -sf -X PATCH "${API}/campaigns/${CAMPAIGN_ID}/knowledge" \
  -H "Content-Type: application/json" \
  -d "{\"knowledge_url\":\"${KNOWLEDGE_URL}\"}" > /dev/null

TASK1=$(curl -sf -X POST "${API}/campaigns/${CAMPAIGN_ID}/knowledge/parse" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])")
poll_task "$TASK1"

CAMPAIGN=$(curl -sf "${API}/campaigns/${CAMPAIGN_ID}")
python3 - <<'PY' "$CAMPAIGN"
import json, sys
c = json.loads(sys.argv[1])
kb = c.get("knowledge_base") or {}
text = c.get("knowledge_text") or ""
assert text.strip(), "knowledge_text is empty"
assert kb.get("text"), "knowledge_base.text is empty"
print(f"  OK: knowledge_text={len(text)} chars, parser={kb.get('parser')}")
PY

echo "[step 2] Audience links + parse"
LINKS_JSON=$(python3 - <<PY
import json, os
links = [x.strip() for x in os.environ.get("AUDIENCE_LINKS", "").split(",") if x.strip()]
print(json.dumps({"audience_links": links}))
PY
)
curl -sf -X PATCH "${API}/campaigns/${CAMPAIGN_ID}/audience" \
  -H "Content-Type: application/json" \
  -d "$LINKS_JSON" > /dev/null

TASK2=$(curl -sf -X POST "${API}/campaigns/${CAMPAIGN_ID}/audience/parse" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])")
poll_task "$TASK2"

CAMPAIGN=$(curl -sf "${API}/campaigns/${CAMPAIGN_ID}")
python3 - <<'PY' "$CAMPAIGN"
import json, sys
c = json.loads(sys.argv[1])
targets = c.get("target_chats") or []
assert targets, "target_chats is empty"
validated = [t for t in targets if t.get("validated")]
print(f"  OK: targets={len(targets)}, validated={len(validated)}")
PY

echo "[step 3] Offer + start campaign"
curl -sf -X PATCH "${API}/campaigns/${CAMPAIGN_ID}/offer" \
  -H "Content-Type: application/json" \
  -d "{\"offer_text\":\"${OFFER_TEXT}\"}" > /dev/null

TASK3=$(curl -sf -X POST "${API}/campaigns/${CAMPAIGN_ID}/start" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])")
poll_task "$TASK3"

CAMPAIGN=$(curl -sf "${API}/campaigns/${CAMPAIGN_ID}")
python3 - <<'PY' "$CAMPAIGN"
import json, sys
c = json.loads(sys.argv[1])
print(f"  messages_sent={c.get('messages_sent')}, active_dialogs={c.get('active_dialogs')}, shield_ok={c.get('smart_shield_ok')}")
PY

echo "=== E2E completed ==="
