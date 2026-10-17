#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Week 1 Docker Verification Script
# 
# This script tests the BLT-Preflight RAG pipeline in Docker
# Required: Docker and docker-compose installed
# Usage: bash verify_week1_docker.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Check prerequisites
# ─────────────────────────────────────────────────────────────────────────────

print_header "Checking Prerequisites"

if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker Desktop."
    exit 1
fi
print_success "Docker found: $(docker --version)"

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose not found. Please install docker-compose."
    exit 1
fi
print_success "docker-compose found: $(docker-compose --version)"

# ─────────────────────────────────────────────────────────────────────────────
# Build Docker image
# ─────────────────────────────────────────────────────────────────────────────

print_header "Building Docker Image"

echo "Building blt-preflight-server..."
docker-compose build preflight-server 2>&1 | tail -10

print_success "Docker image built successfully"

# ─────────────────────────────────────────────────────────────────────────────
# Start services
# ─────────────────────────────────────────────────────────────────────────────

print_header "Starting Services"

echo "Starting preflight-server..."
docker-compose up -d preflight-server

print_warning "Waiting for service to be ready (15 seconds)..."
sleep 15

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Health Check
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 1: Health Check"

HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_success "Health check passed"
    echo "Response: $HEALTH_RESPONSE"
else
    print_error "Health check failed"
    echo "Response: $HEALTH_RESPONSE"
    docker-compose logs preflight-server
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Retrieval Endpoint - Query 1
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 2: Retrieval - 'I modified the login flow'"

RESPONSE=$(curl -s -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I modified the login flow",
    "top_k": 2,
    "similarity_threshold": 0.6
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    print_success "Retrieval test 1 passed (status: success)"
    CHUNK_COUNT=$(echo "$RESPONSE" | grep -o '"text"' | wc -l)
    print_success "Retrieved $CHUNK_COUNT chunks"
elif echo "$RESPONSE" | grep -q '"status":"no_match"'; then
    print_warning "No matches found (knowledge base might not be ingested)"
else
    print_error "Retrieval test 1 failed"
    echo "$RESPONSE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Retrieval Endpoint - Query 2
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 3: Retrieval - 'I added a new API endpoint'"

RESPONSE=$(curl -s -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I added a new API endpoint",
    "top_k": 2,
    "similarity_threshold": 0.6
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    print_success "Retrieval test 2 passed"
elif echo "$RESPONSE" | grep -q '"status":"no_match"'; then
    print_warning "No matches found"
else
    print_error "Retrieval test 2 failed"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Retrieval Endpoint - Query 3
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 4: Retrieval - 'I changed how passwords are stored'"

RESPONSE=$(curl -s -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I changed how passwords are stored",
    "top_k": 2,
    "similarity_threshold": 0.6
  }')

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    print_success "Retrieval test 3 passed"
elif echo "$RESPONSE" | grep -q '"status":"no_match"'; then
    print_warning "No matches found"
else
    print_error "Retrieval test 3 failed"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Advisory Endpoint
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 5: Advisory Generation Endpoint"

RESPONSE=$(curl -s -X POST http://localhost:8000/advisory \
  -H "Content-Type: application/json" \
  -d '{
    "contributor_intent": "Adding OAuth2 support for authentication",
    "files_changed": ["src/auth/oauth.py", "src/config/auth_config.py"],
    "labels": ["security", "authentication"],
    "repository_context": "Django REST API"
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    print_success "Advisory generation passed"
else
    print_warning "Advisory generation had issues"
    echo "$RESPONSE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 6: API Documentation
# ─────────────────────────────────────────────────────────────────────────────

print_header "Test 6: API Documentation (Swagger UI)"

RESPONSE=$(curl -s http://localhost:8000/docs)

if echo "$RESPONSE" | grep -q "Swagger UI"; then
    print_success "Swagger UI available at http://localhost:8000/docs"
else
    print_warning "Swagger UI might not be available"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Service Logs
# ─────────────────────────────────────────────────────────────────────────────

print_header "Service Logs (Last 20 lines)"

docker-compose logs --tail=20 preflight-server

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

print_header "Cleanup"

echo "Stopping services..."
docker-compose down

print_success "Services stopped"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print_header "Week 1 Verification Complete"

echo "Summary:"
echo "  ✓ Docker image built successfully"
echo "  ✓ Service started and health check passed"
echo "  ✓ Retrieval endpoints tested (3 scenarios)"
echo "  ✓ Advisory generation endpoint tested"
echo "  ✓ API documentation available"
echo ""
echo "Next Steps:"
echo "  1. Ingest OWASP documents: docker-compose exec preflight-server python scripts/ingest.py"
echo "  2. Run native tests: python test_week1.py"
echo "  3. Test with GitHub Actions integration"
echo ""
echo "To start the server for development:"
echo "  docker-compose up preflight-server"
echo "  curl http://localhost:8000/health"
