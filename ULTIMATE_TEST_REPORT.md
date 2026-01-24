# Ultimate API Test Report
**Date**: 2026-01-25 00:47:39
**Duration**: 22.52 seconds

## Executive Summary
| Metric | Value | Status |
|---|---|---|
| **Total Tests** | 30 | ℹ️ |
| **Passed** | 28 | ✅ |
| **Failed** | 2 | ❌ |
| **Success Rate** | 93.3% | ⚠️ |

## Detailed Results
| Module | Method | Endpoint | Status | Result | Detail |
|---|---|---|---|---|---|
| Infra | GET | `/test/redis` | 200 | ✅ | - |
| Infra | GET | `/test/celery (Enqueue)` | 200 | ✅ | - |
| Infra | GET | `/test/celery/86e79aad-7262-4dd4-be24-3b38181e3b2d (Result)` | 200 | ✅ | - |
| Comm | POST | `/webhooks/stripe` | 400 | ❌ | - |
| Comm | POST | `/meetings/join` | 500 | ❌ | - |
| Comm | POST | `/webhooks/recall` | 200 | ✅ | - |
| Auth | POST | `/users/sync (Admin)` | 200 | ✅ | - |
| Auth | POST | `/users/sync (Dev)` | 200 | ✅ | - |
| Auth | POST | `/users/sync (New)` | 200 | ✅ | - |
| Users | GET | `/users/me` | 200 | ✅ | - |
| Users | PATCH | `/users/me` | 200 | ✅ | - |
| Users | GET | `/users/search` | 200 | ✅ | - |
| Users | DELETE | `/users/me` | 200 | ✅ | - |
| Users | PATCH | `/users/{id}/restore` | 200 | ✅ | - |
| Notes | GET | `/notes` | 200 | ✅ | - |
| Notes | GET | `/notes/dashboard` | 200 | ✅ | - |
| Notes | POST | `/notes/search` | 200 | ✅ | - |
| Tasks | GET | `/tasks` | 200 | ✅ | - |
| Tasks | GET | `/tasks/assigned-to-me` | 200 | ✅ | - |
| Tasks | GET | `/tasks/due-today` | 200 | ✅ | - |
| Tasks | GET | `/tasks/overdue` | 200 | ✅ | - |
| Tasks | GET | `/tasks/stats` | 200 | ✅ | - |
| Tasks | GET | `/tasks/search` | 200 | ✅ | - |
| AI | GET | `/ai/stats` | 200 | ✅ | - |
| Admin | GET | `/admin/status` | 200 | ✅ | - |
| Admin | GET | `/admin/users` | 200 | ✅ | - |
| Admin | GET | `/admin/users/stats` | 200 | ✅ | - |
| Admin | GET | `/admin/admins` | 200 | ✅ | - |
| Admin | GET | `/admin/settings/ai` | 200 | ✅ | - |
| Admin | PATCH | `/admin/settings/ai` | 200 | ✅ | - |
