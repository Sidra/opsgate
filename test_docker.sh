#!/bin/bash
# OpsGate — Build, run, and test Docker container
# Usage: bash test_docker.sh

set -e

echo "=== Building Docker image ==="
docker build -t opsgate .

echo ""
echo "=== Starting container ==="
docker run -d --name opsgate-test -p 8000:8000 opsgate
echo "  Container started. Waiting for health check..."
sleep 5

echo ""
echo "=== Testing health endpoint ==="
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "=== Testing reset endpoint ==="
RESET=$(curl -s -X POST http://localhost:8000/reset)
echo "$RESET" | python3 -m json.tool

echo ""
echo "=== Testing step endpoint (CRM get_user) ==="
STEP=$(curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "crm", "action": "get_user", "parameters": {"user_id": 101}}')
echo "$STEP" | python3 -m json.tool

echo ""
echo "=== Testing step endpoint (Billing issue_refund) ==="
STEP2=$(curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "billing", "action": "issue_refund", "parameters": {"invoice_id": 1001, "user_id": 101, "amount": 79.99, "reason": "test"}}')
echo "$STEP2" | python3 -m json.tool

echo ""
echo "=== Testing step endpoint (Email send) ==="
STEP3=$(curl -s -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "email", "action": "send", "parameters": {"to": "bob@company.com", "subject": "Test", "body": "Test email"}}')
echo "$STEP3" | python3 -m json.tool

echo ""
echo "=== Testing state endpoint ==="
curl -s http://localhost:8000/state | python3 -m json.tool

echo ""
echo "=== Cleaning up ==="
docker stop opsgate-test
docker rm opsgate-test
echo ""
echo "=== All Docker tests passed! ==="
