#!/bin/bash

# Quick Backend Test Script
# Tests backend connectivity and API endpoints

echo "========================================"
echo "UMV Backend API - Local Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "Testing backend connectivity..."
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running"
else
    echo -e "${RED}✗${NC} Backend is not running"
    echo -e "${YELLOW}Start backend with: ./run.sh${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo "Health Check"
echo "========================================"
curl -s http://localhost:5000/api/health | python3 -m json.tool

echo ""
echo "========================================"
echo "API Status"
echo "========================================"
curl -s http://localhost:5000/api/status | python3 -m json.tool

echo ""
echo "========================================"
echo "CORS Test"
echo "========================================"
curl -s -H "Origin: http://localhost:3000" http://localhost:5000/api/cors-test | python3 -m json.tool

echo ""
echo "========================================"
echo "All Tests Complete!"
echo "========================================"
echo ""
echo "Backend is ready for frontend integration."
echo "See FRONTEND_INTEGRATION_GUIDE.md for details."
echo ""
