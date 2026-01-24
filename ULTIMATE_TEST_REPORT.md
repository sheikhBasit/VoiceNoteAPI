# Ultimate API Test Report
**Date**: 2026-01-24 23:44:37
**Duration**: 11.20 seconds

## Executive Summary
| Metric | Value | Status |
|---|---|---|
| **Total Tests** | 38 | ℹ️ |
| **Passed** | 29 | ✅ |
| **Failed** | 9 | ❌ |
| **Success Rate** | 76.3% | ⚠️ |

## Detailed Results
| Module | Method | Endpoint | Status | Result | Detail |
|---|---|---|---|---|---|
| Infra | GET | `/test/redis` | 404 | ❌ | - |
| Infra | GET | `/test/celery (Enqueue)` | 404 | ❌ | - |
| Comm | POST | `/webhooks/stripe` | 404 | ❌ | - |
| Comm | POST | `/meetings/join` | 404 | ❌ | - |
| Comm | POST | `/webhooks/recall` | 404 | ❌ | - |
| Auth | POST | `/users/sync (Admin)` | 200 | ✅ | - |
| Auth | POST | `/users/sync (Dev)` | 200 | ✅ | - |
| Auth | POST | `/users/sync (New)` | 200 | ✅ | - |
| Users | GET | `/users/me` | 200 | ✅ | - |
| Users | PATCH | `/users/me` | 200 | ✅ | - |
| Users | GET | `/users/search` | 200 | ✅ | - |
| Users | DELETE | `/users/me` | 200 | ✅ | - |
| Users | PATCH | `/users/{id}/restore` | 200 | ✅ | - |
| Notes | GET | `/notes` | 200 | ✅ | - |
| Notes | GET | `/notes/{id}` | 200 | ✅ | - |
| Notes | PATCH | `/notes/{id}` | 200 | ✅ | - |
| Notes | POST | `/notes/{id}/ask` | 200 | ✅ | - |
| Notes | POST | `/notes/{id}/semantic-analysis` | 200 | ✅ | - |
| Notes | GET | `/notes/{id}/whatsapp` | 200 | ✅ | - |
| Notes | GET | `/notes/dashboard` | 200 | ✅ | - |
| Notes | POST | `/notes/search` | 500 | ❌ | - |
| Tasks | GET | `/tasks` | 200 | ✅ | - |
| Tasks | GET | `/tasks/{id}` | 200 | ✅ | - |
| Tasks | PATCH | `/tasks/{id}` | 200 | ✅ | - |
| Tasks | POST | `/tasks/{id}/duplicate` | 201 | ✅ | - |
| Tasks | GET | `/tasks/{id}/comms` | 200 | ✅ | - |
| Tasks | GET | `/tasks/due-today` | 200 | ✅ | - |
| Tasks | GET | `/tasks/overdue` | 200 | ✅ | - |
| Tasks | GET | `/tasks/assigned-to-me` | 400 | ❌ | - |
| Tasks | GET | `/tasks/stats` | 200 | ✅ | - |
| Tasks | GET | `/tasks/search` | 422 | ❌ | - |
| AI | GET | `/ai/stats` | 422 | ❌ | - |
| Admin | GET | `/admin/status` | 200 | ✅ | - |
| Admin | GET | `/admin/users` | 200 | ✅ | - |
| Admin | GET | `/admin/users/stats` | 200 | ✅ | - |
| Admin | GET | `/admin/admins` | 200 | ✅ | - |
| Admin | GET | `/admin/settings/ai` | 200 | ✅ | - |
| Admin | PATCH | `/admin/settings/ai` | 200 | ✅ | - |
