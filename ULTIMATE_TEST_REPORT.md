# Ultimate API Test Report
**Date**: 2026-01-24 20:13:05
**Duration**: 0.12 seconds

## Executive Summary
| Metric | Value | Status |
|---|---|---|
| **Total Tests** | 9 | ℹ️ |
| **Passed** | 4 | ✅ |
| **Failed** | 5 | ❌ |
| **Success Rate** | 44.4% | ⚠️ |

## Detailed Results
| Module | Method | Endpoint | Status | Result | Detail |
|---|---|---|---|---|---|
| Auth | POST | `/users/sync (Admin)` | 200 | ✅ | - |
| Auth | POST | `/users/sync (Dev)` | 400 | ❌ | - |
| Auth | POST | `/users/sync (New)` | 400 | ❌ | - |
| Admin | GET | `/admin/status` | 200 | ✅ | - |
| Admin | GET | `/admin/users` | 403 | ❌ | - |
| Admin | GET | `/admin/users/stats` | 403 | ❌ | - |
| Admin | GET | `/admin/admins` | 200 | ✅ | - |
| Admin | GET | `/admin/settings/ai` | 200 | ✅ | - |
| Admin | PATCH | `/admin/settings/ai` | 422 | ❌ | - |
