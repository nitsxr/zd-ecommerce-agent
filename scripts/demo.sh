#!/usr/bin/env bash
# Demo script for the E-commerce Assistant API.
# Prerequisites: docker-compose up -d, OPENAI_API_KEY in .env
# Usage: ./scripts/demo.sh [BASE_URL]
set -e
BASE_URL="${1:-http://localhost:8000}"

echo "=== 1. Health ==="
curl -s "$BASE_URL/health" | head -1
echo ""

echo "=== 2. Order tracking ==="
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "Track my order ORD-1234"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Agent:', d.get('agent')); print('Response:', (d.get('response') or '')[:200])"
echo ""

echo "=== 3. Cancellation (eligible) ==="
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "Cancel order ORD-6789"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Agent:', d.get('agent')); print('Response:', (d.get('response') or '')[:200])"
echo ""

echo "=== 4. Multi-turn (reference: that order) ==="
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "What is the status of ORD-1234?"}' > /dev/null
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "Cancel that order"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Agent:', d.get('agent')); print('Response:', (d.get('response') or '')[:200])"
echo ""

echo "=== 5. Product / FAQ ==="
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "What is your return policy?"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Agent:', d.get('agent')); print('Response:', (d.get('response') or '')[:150])"
echo ""

echo "=== 6. Fallback (out of scope) ==="
curl -s -X POST "$BASE_URL/chat" -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "What is the weather?"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('Response:', (d.get('response') or '')[:150])"
echo ""

echo "=== 7. Stats ==="
curl -s "$BASE_URL/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Sessions:', d.get('total_sessions')); print('Messages:', d.get('total_messages')); print('Success rate:', d.get('success_rate'))"
echo ""

echo "Demo complete. Open $BASE_URL for Chat UI, $BASE_URL/docs for API docs."
