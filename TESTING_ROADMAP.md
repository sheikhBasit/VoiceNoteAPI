# VoiceNote API — Testing Roadmap

Future testing improvements to build on the current foundation. Each item describes what to implement, which tools to use, and what value it provides.

## 1. Contract Testing (OpenAPI Schema Validation)

Use `schemathesis` to automatically generate test cases from the OpenAPI schema (`/openapi.json`). This catches endpoints that return unexpected status codes or response shapes without writing individual tests.

```bash
pip install schemathesis
schemathesis run http://localhost:8000/openapi.json --base-url http://localhost:8000
```

## 2. Visual Regression / Snapshot Testing

Add Playwright `toHaveScreenshot()` assertions to E2E tests. Catches unintended UI changes (layout shifts, missing icons, broken styles) across dashboard pages.

```typescript
await expect(page).toHaveScreenshot('dashboard-overview.png', { maxDiffPixels: 100 });
```

## 3. Load Testing Expansion

Create a new Locust file targeting admin API endpoints (analytics, audit logs, bulk operations). The existing `locustfile.py` covers user-facing endpoints but admin paths are untested under load.

## 4. Factory Pattern for Test Data

Replace ad-hoc fixture creation (`models.User(id=..., email=...)`) with `factory_boy` factories. Reduces boilerplate and ensures consistent test data across all test modules.

```python
class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.User
    id = factory.LazyFunction(lambda: f"user_{uuid4().hex[:8]}")
    email = factory.Faker("email")
```

## 5. Response Schema Validation

Assert that API response bodies match their Pydantic `response_model` schemas. Catches serialization bugs where the endpoint returns data that doesn't match the documented shape.

## 6. Celery Pipeline End-to-End Tests

Test the full note processing pipeline: upload audio -> Celery task -> transcription -> AI analysis -> embedding generation. Use mock audio fixtures and verify each stage produces expected output.

## 7. SSE and WebSocket Tests

Dedicated tests using `httpx_sse` for Server-Sent Events and `websockets` for WebSocket connections. Verify real-time notification delivery and connection lifecycle.

```python
async with httpx_sse.aconnect_sse(client, "GET", "/api/v1/sse") as event_source:
    async for event in event_source.aiter_sse():
        assert event.event == "heartbeat"
        break
```

## 8. Dashboard Unit Tests (React Components)

Add `@testing-library/react` tests for hooks (`useUsers`, `useBilling`, etc.) and key components. Tests run without a browser, giving faster feedback than Playwright.

```bash
cd dashboard && npm install --save-dev @testing-library/react @testing-library/jest-dom
```

## 9. Security Penetration Tests

Targeted tests for:
- **IDOR**: Access notes/tasks belonging to other users
- **JWT manipulation**: Expired tokens, tampered payloads, algorithm confusion
- **Rate limit bypass**: Verify rate limiting can't be circumvented with header tricks
- **Privilege escalation**: Non-admin accessing admin endpoints with crafted requests

## 10. Migration Data Integrity

Verify that real data survives migration up/down cycles. Seed a database with representative data, run `alembic upgrade head`, verify data is intact, run `alembic downgrade -1`, verify data is still intact (or gracefully handled).
