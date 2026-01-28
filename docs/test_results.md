# Comprehensive API Test Report
**Generated**: 2026-01-24 19:10:05

## Summary
- **Total Tests**: 13
- **Passed**: 10 ✅
- **Failed**: 3 ❌
- **Success Rate**: 76.9%

## Authentication

| Endpoint | Method | Status | Result | Detail |
|----------|--------|--------|--------|--------|
| /users/sync | POST | 200 | ✅ |  |
| /users/sync (Admin) | POST | 200 | ✅ |  |

## Users

| Endpoint | Method | Status | Result | Detail |
|----------|--------|--------|--------|--------|
| /users/me | GET | 200 | ✅ |  |
| /users/me | PATCH | 200 | ✅ |  |
| /users/search | GET | 200 | ✅ |  |

## Notes

| Endpoint | Method | Status | Result | Detail |
|----------|--------|--------|--------|--------|
| /notes | GET | 200 | ✅ |  |
| /notes/dashboard | GET | 404 | ❌ |  |
| /notes/search | POST | 500 | ❌ |  |

## Tasks

| Endpoint | Method | Status | Result | Detail |
|----------|--------|--------|--------|--------|
| /tasks | GET | 200 | ✅ |  |

## Admin

| Endpoint | Method | Status | Result | Detail |
|----------|--------|--------|--------|--------|
| /admin/status | GET | 200 | ✅ |  |
| /admin/settings/ai | GET | 200 | ✅ |  |
| /admin/settings/ai | PATCH | 200 | ✅ |  |
| /admin/users | GET | 403 | ❌ |  |

