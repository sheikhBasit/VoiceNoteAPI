# VoiceNote API Documentation

This document lists all available endpoints in the VoiceNote API.

## Base URL
The API is served at the root URL (e.g., `http://localhost:8000` or production URL).
Most endpoints are prefixed with `/api/v1`.

## Authentication
Most endpoints require authentication.
- **Header**: `Authorization: Bearer <your_access_token>`
- **Token**: Get an access token via the `/api/v1/users/sync` or `/api/v1/users/refresh` endpoints.

---

## 🚀 Public & Root

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API Root (Status, Version, Service Map) |
| `GET` | `/health` | Health Check (DB Connectivity) |
| `GET` | `/docs` | Swagger UI Documentation |
| `GET` | `/redoc` | ReDoc Documentation |

---

## 👤 Users (`/api/v1/users`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/sync` | **Email-First Auth**. Register or Login. |
| `POST` | `/logout` | Terminate session for current device. |
| `GET` | `/verify-device` | Confirm new device (via email token). |
| `POST` | `/refresh` | Refresh Access Token. |
| `GET` | `/me` | Get current user profile. |
| `PATCH` | `/me` | Update current user profile. |
| `DELETE` | `/me` | Soft-delete current user account. |
| `PATCH` | `/me/profile-picture` | Upload profile picture. |
| `GET` | `/balance` | Get current wallet balance. |
| `GET` | `/search` | Search for users (with role filtering). |
| `GET` | `/{user_id}` | Get public profile of another user. |
| `PATCH` | `/{user_id}/restore` | Restore soft-deleted user. |
| `PATCH` | `/{user_id}/role` | Update user role (**Admin Only**). |

---

## 📝 Notes (`/api/v1/notes`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | List all notes (paginated). |
| `DELETE`| `/` | Bulk delete notes. |
| `POST` | `/create` | Create a text-only note manually. |
| `POST` | `/process` | **Process Audio**. Uploads audio for processing (STT + AI). |
| `GET` | `/presigned-url` | Get direct-to-S3/MinIO upload URL. |
| `GET` | `/dashboard` | Get productivity metrics (Pulse). |
| `GET` | `/autocomplete` | Search suggestion for titles/tags. |
| `POST` | `/search` | **Unified V-RAG Search**. Semantic + Full-text search. |
| `PATCH` | `/move` | Bulk move notes to folder. |
| `GET` | `/{note_id}` | Get full note details. |
| `PATCH` | `/{note_id}` | Update note (Title, content, soft-delete). |
| `DELETE`| `/{note_id}` | Delete note (Soft or Hard). |
| `PATCH` | `/{note_id}/restore` | Restore soft-deleted note. |
| `POST` | `/{note_id}/ask` | Q&A with AI about the note. |
| `GET` | `/{note_id}/whatsapp` | Generate WhatsApp draft/link. |
| `POST` | `/{note_id}/semantic-analysis`| Trigger deep analysis background task. |

---

## ✅ Tasks (`/api/v1/tasks`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | List tasks (filtering by note, user, etc.). |
| `POST` | `/` | Create a new manual task. |
| `DELETE`| `/` | Bulk delete tasks. |
| `GET` | `/due-today` | Get tasks due today. |
| `GET` | `/overdue` | Get overdue tasks. |
| `GET` | `/assigned-to-me` | Get tasks assigned to current user. |
| `GET` | `/search` | Search tasks active description. |
| `GET` | `/stats` | Task completion statistics. |
| `GET` | `/{task_id}` | Get single task details. |
| `PATCH` | `/{task_id}` | Update task. |
| `DELETE`| `/{task_id}` | Delete task. |
| `PATCH` | `/{task_id}/restore` | Restore soft-deleted task. |
| `POST` | `/{task_id}/duplicate` | Duplicate a task. |
| `PATCH` | `/{task_id}/complete` | Toggle completion status. |
| `POST` | `/{task_id}/multimedia` | Upload attachment (Image/Doc). |
| `PATCH` | `/{task_id}/multimedia` | Remove attachment. |
| `POST` | `/{task_id}/external-links` | Add external link. |
| `DELETE`| `/{task_id}/external-links/{index}`| Remove external link. |
| `GET` | `/{task_id}/communication-options`| Get channels to contact assignees. |

---

## 📂 Folders (`/api/v1/folders`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | List all folders. |
| `POST` | `/` | Create a new folder. |
| `PATCH` | `/{folder_id}` | Update folder details. |
| `DELETE`| `/{folder_id}` | Delete folder (Notes moved to Uncategorized). |

---

## 🤖 AI & Insights (`/api/v1/ai`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/search` | (Deprecated/Proxy) Helper for semantic search. |
| `GET` | `/stats` | User/Admin level insights. |

---

## 🔌 Integrations (`/api/v1/integrations`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/list` | List connected services. |
| `POST` | `/google/connect` | Connect Google account. |
| `POST` | `/notion/connect` | Connect Notion account. |
| `DELETE`| `/{provider}/disconnect` | Disconnect a service. |

---

## 🛡️ Admin (`/api/v1/admin`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/users` | List all users. |
| `GET` | `/users/stats` | Global user statistics. |
| `GET` | `/users/{user_id}` | Get full user details (Admin view). |
| `PATCH` | `/users/{user_id}` | Update any user. |
| `DELETE`| `/users/{user_id}` | Soft delete user. |
| `DELETE`| `/users/{user_id}/hard` | **Permanently** delete user. |
| `PATCH` | `/users/{user_id}/restore` | Restore deleted user. |
| `POST` | `/users/{user_id}/make-admin` | Promote user to Admin. |
| `POST` | `/users/{user_id}/remove-admin`| Revoke Admin privileges. |
| `GET` | `/users/{user_id}/devices` | View user devices. |
| `PUT` | `/permissions/{user_id}` | Update granular admin permissions. |
| `GET` | `/notes` | View all notes (content moderation). |
| `DELETE`| `/notes/{note_id}` | Moderate/Delete content. |

---

## 🔄 Sync (`/api/v1/sync`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/upload-batch` | Batch upload multiple files (Mobile Sync). |

---

## 🪝 Webhooks (`/api/v1/webhooks`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/stripe` | Stripe Payment Events. |

---

## 📡 WebSockets (`/api/ws`)

| Endpoint | Description |
| :--- | :--- |
| `/{user_id}` | General real-time events. |
| `/audio/{user_id}` | Real-time Audio Streaming & Transcription. |

---

## 🧪 Testing Lab (`/api/v1/test`)
*Non-production environments only*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/stt-comparison` | Compare Groq vs Deepgram results. |
| `POST` | `/preprocess` | Test Audio Enhancement Pipeline. |
| `GET` | `/celery` | Test Celery Queue. |
| `GET` | `/celery/{task_id}` | Check Celery Task Status. |
| `GET` | `/redis` | Test Redis Connectivity. |

---

## 💻 Frontend Integration Guide

This section outlines standard workflows for clients (Web & Mobile) integrating with the VoiceNote API.

### 1. Authentication Flow (Email-First)
The API uses passwordless, email-based authentication or direct dev/testing sync.

1.  **Initiate Login/Register**:
    *   Call `POST /api/v1/users/sync` with `{ "email": "...", "device_id": "...", "name": "..." }`.
    *   **Response**:
        *   `is_new_user: true` -> Account created. Store `access_token`.
        *   `is_new_user: false` -> Check your email for a verification link (if device is new).
        *   `access_token` returned -> Login successful.

2.  **Verify Device (If required)**:
    *   User clicks email link -> `GET /api/v1/users/verify-device?token=...`.
    *   Client retries `/sync` -> Successful login.

3.  **Session Management**:
    *   Include `Authorization: Bearer <access_token>` in all requests.
    *   On `401 Unauthorized`, call `POST /api/v1/users/refresh` with your refresh token.

### 2. Audio Processing Workflow
The core feature is capturing and processing audio.

**A. Short Audio (< 5MB) / Web Client**:
*   Call `POST /api/v1/notes/process` directly with `multipart/form-data` (field `file`).
*   Receive `note_id` immediately (Accepted).
*   Poll `GET /api/v1/notes/{note_id}` until `status` is `DONE`.

**B. Large Audio / Mobile Client (Recommended)**:
1.  **Get Upload URL**: Call `GET /api/v1/notes/presigned-url`.
    *   Returns: `upload_url`, `storage_key`, `note_id`.
2.  **Upload to Cloud**: PUT the file binary directly to `upload_url`.
3.  **Trigger Processing**: Call `POST /api/v1/notes/process`.
    *   Body: `storage_key` (from step 1), `note_id` (from step 1).

### 3. Real-Time Transcription (WebSocket)
For live transcription feedback:
1.  Connect to `ws://BASE_URL/api/ws/audio/{user_id}?token={access_token}`.
2.  Send audio chunks (binary int16 PCM, 16kHz).
3.  Receive JSON events:
    ```json
    {
      "type": "transcript",
      "text": "Hello world",
      "is_final": false
    }
    ```

### 4. Search & Retrieval (RAG)
1.  **Quick Search**: `POST /api/v1/notes/search` with `{ "query": "..." }`.
2.  **Autocomplete**: `GET /api/v1/notes/autocomplete?q=...` for search bar suggestions.
