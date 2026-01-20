# 1. Run all functional tests
pytest tests/test_core.py -v

# 2. Check Security Middleware Coverage
pytest --cov=app --cov-report=term-missing

# 3. Check for specific AI API Key leaks
grep -r "sk-" .  # Ensure no OpenAI/Groq keys are hardcoded