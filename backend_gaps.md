# Backend Gaps Audit: Missing Components & Inconsistencies

This document identifies backend features and endpoints that are defined/expected by the mobile frontend but are currently missing or inconsistent in the FastAPI implementation.

## 1. Missing Routers & Large Features

| Feature | Frontend Requirement | Backend Status | Gap |
| :--- | :--- | :--- | :--- |
| **Meeting Intelligence** | `POST meetings/join` | **Missing** | No meeting router or service implementation exists. |
| **Integrations** | `integrations/google/connect` | Partially Mocked | Backend exists but is mostly mock logic; needs real OAuth flow. |

---

## 2. Missing or Mismatched Endpoints

| Endpoint | Mobile Expectation | Backend Actual | status |
| :--- | :--- | :--- | :--- |
| **Task Completion** | `PATCH /tasks/{id}/complete` | **Missing** | Backend uses generic `PATCH /tasks/{id}` for all updates. |
| **Login Alias** | `POST /users/login` | **Missing** | Backend only uses `/users/sync` for authentication. |
| **Task Stats** | `GET /tasks/statistics` | `GET /tasks/stats` | **Path Mismatch** (Mobile wants long name). |

---

## 3. Schema & Data Gaps

### [Authentication]
- **`password`**: Mobile's `SyncRequest` includes a `password` field for device-independent login, but the backend's `UserCreate` schema and `sync_user` logic do not yet handle it.

### [Notes & Transcription]
- **Comparison Views**: Backend stores `transcript_groq`, `transcript_deepgram`, and `transcript_android` separately in the DB, but only returns a single merged `transcript` to the mobile app. The app cannot currently show a "Comparison" view.
- **Audio URLs**: Backend stores `raw_audio_url` but doesn't consistently expose it in all response summaries where it might be needed for fallback playback.

### [Tasks]
- **Bulk Actions**: Mobile code hints at bulk operations (e.g., deleting multiple tasks at once), but the backend lacks a bulk task delete endpoint (it only has bulk note delete).

---

## 4. Operational Inconsistencies

- **Timeouts**: Some AI-heavy endpoints (like `semantic-analysis`) are offloaded to background tasks, which is good, but the mobile app doesn't always have a "polling" or "webhook" mechanism to know precisely when they finish (depends on WebSockets).
- **Encryption**: `Note` model has `is_encrypted`, but the backend lacks the cryptographic service/logic to actually handle field-level encryption/decryption.

## Recommendations
1.  **Implement `meetings` Router**: Add a basic meeting join/bot management service.
2.  **Add Endpoint Aliases**: Support `/complete` for tasks and `/login` for users to improve mobile compatibility.
3.  **Update `UserCreate` Schema**: Add optional `password` field and implement hashing logic in `sync_user`.
4.  **Expose Full Transcripts**: Add an optional `?verbose=true` flag to the Note Detail endpoint to return all transcript variations.
