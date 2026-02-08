#!/bin/bash
# Master test script for VoiceNote API CI/CD

echo "Starting VoiceNote API Test Suite..."

# 1. Run Logic Tests with Pytest
echo "Running Pytest suite..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest -v --cov=app tests/

# 2. Run API Integration Tests
if [ -f "scripts/test/test_all_endpoints_curl.sh" ]; then
    echo "Running endpoint integration tests..."
    bash scripts/test/test_all_endpoints_curl.sh
fi

echo "Test suite completed."
