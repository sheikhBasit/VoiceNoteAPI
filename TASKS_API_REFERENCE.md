# Tasks API Quick Reference

## Base URL
`/api/v1/tasks`

---

## Endpoint Summary

### CRUD Operations

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/` | Create new task | ✅ |
| GET | `/` | List all user tasks (with filter) | ✅ |
| GET | `/{task_id}` | Get task details | ✅ |
| PATCH | `/{task_id}` | Update task | ✅ |
| DELETE | `/{task_id}` | Soft/hard delete task | ✅ |

### Quick Actions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PATCH | `/{task_id}/toggle` | Toggle task completion |
| PATCH | `/{task_id}/priority` | Update priority only |
| PATCH | `/{task_id}/deadline` | Update deadline only |

### Task Status Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PATCH | `/{task_id}/approve` | Approve for automation |
| PATCH | `/{task_id}/restore` | Restore soft-deleted task |

### Assignment & Communication

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PATCH | `/{task_id}/assign` | Assign task to contacts |
| PATCH | `/{task_id}/communication-type` | Set communication channel |
| GET | `/{task_id}/communication-options` | Get available channels |
| GET | `/assigned-to-me` | Get tasks assigned to me |

### Multimedia Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/{task_id}/multimedia` | Upload image/document |
| PATCH | `/{task_id}/multimedia/remove` | Remove media file |

### External Links

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/{task_id}/external-links` | Add external link |
| DELETE | `/{task_id}/external-links/{link_index}` | Remove link by index |

### Filtering & Search

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/by-note/{note_id}` | Get tasks for specific note |
| GET | `/due-today` | Get tasks due today |
| GET | `/overdue` | Get overdue tasks |
| GET | `/search` | Full-text search tasks |

### Utilities

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/{task_id}/duplicate` | Clone a task |
| PATCH | `/{task_id}/bulk-update` | Update multiple fields |
| GET | `/stats` | Get task statistics |

---

## Request/Response Examples

### Create Task
```bash
POST /api/v1/tasks
Content-Type: application/json

{
  "note_id": "note_123",
  "description": "Follow up with client",
  "priority": "HIGH",
  "deadline": 1705881600000,
  "assigned_entities": [
    {
      "name": "John Doe",
      "phone": "+1234567890",
      "email": "john@example.com"
    }
  ],
  "communication_type": "WHATSAPP",
  "is_action_approved": false
}
```

### Response (201 Created)
```json
{
  "id": "task_abc123",
  "note_id": "note_123",
  "description": "Follow up with client",
  "priority": "HIGH",
  "deadline": 1705881600000,
  "is_done": false,
  "created_at": 1705795200000,
  "assigned_entities": [...],
  "communication_type": "WHATSAPP",
  "is_action_approved": false,
  "image_urls": [],
  "document_urls": [],
  "external_links": []
}
```

### Get Task Statistics
```bash
GET /api/v1/tasks/stats?user_id=user_123
```

### Response
```json
{
  "total_tasks": 15,
  "completed_tasks": 8,
  "pending_tasks": 7,
  "by_priority": {
    "high": 3,
    "medium": 7,
    "low": 5
  },
  "by_status": {
    "overdue": 2,
    "due_today": 1
  },
  "completion_rate": 53.33
}
```

### Get Tasks Due Today
```bash
GET /api/v1/tasks/due-today?user_id=user_123
```

### Get Communication Options
```bash
GET /api/v1/tasks/task_abc123/communication-options
```

### Response
```json
{
  "available_channels": ["CALL", "SMS", "WHATSAPP", "SLACK"],
  "assigned_entities": [
    {
      "name": "John Doe",
      "phone": "+1234567890",
      "email": "john@example.com"
    }
  ],
  "current_communication_type": "WHATSAPP"
}
```

### Add External Link
```bash
POST /api/v1/tasks/task_abc123/external-links
Content-Type: application/json

{
  "title": "Project Documentation",
  "url": "https://docs.example.com/project"
}
```

### Duplicate Task
```bash
POST /api/v1/tasks/task_abc123/duplicate
```

### Bulk Update Task
```bash
PATCH /api/v1/tasks/task_abc123/bulk-update
Content-Type: application/json

{
  "priority": "MEDIUM",
  "deadline": 1705968000000,
  "is_action_approved": true
}
```

---

## Query Parameters

### List Tasks
- `user_id` (required): User identifier
- `priority` (optional): Filter by priority (HIGH, MEDIUM, LOW)

### Get Due Today / Overdue
- `user_id` (required): User identifier

### Search Tasks
- `user_id` (required): User identifier
- `query_text` (required): Search query

### Get Assigned to Me
- `user_email` (optional): User email
- `user_phone` (optional): User phone number
- *At least one of email or phone required*

### Get Statistics
- `user_id` (required): User identifier

### Delete Task
- `hard` (optional): Boolean, default=false
  - `false`: Soft delete (keeps data, marks as deleted)
  - `true`: Hard delete (permanently removes from database)

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (GET, PATCH) |
| 201 | Created (POST) |
| 400 | Bad Request (validation error) |
| 404 | Not Found (resource doesn't exist) |
| 500 | Server Error |

---

## Error Responses

### Example: Task Not Found
```json
{
  "detail": "Task not found"
}
```

### Example: Invalid Deadline
```json
{
  "detail": "Deadline must be in the future"
}
```

### Example: Missing Parameters
```json
{
  "detail": "Provide either user_email or user_phone"
}
```

---

## Data Types & Enums

### Priority
- `HIGH`
- `MEDIUM`
- `LOW`

### CommunicationType
- `WHATSAPP`
- `SMS`
- `CALL`
- `MEET`
- `SLACK`

### ContactEntity
```json
{
  "name": "string (optional)",
  "phone": "string (optional)",
  "email": "string (optional, must be valid email)"
}
```

### LinkEntity
```json
{
  "title": "string (required)",
  "url": "string (required, must be valid URL)"
}
```

---

## Features

✅ **Soft Delete Support**: Tasks marked as deleted but data preserved  
✅ **Restore Capability**: Deleted tasks can be restored  
✅ **JSONB Arrays**: Multiple images, documents, links per task  
✅ **JSONB Search**: Query tasks by assigned contact info  
✅ **Flexible Assignment**: Multiple contacts per task (JSONB)  
✅ **Time-based Filtering**: Due today, overdue, deadline ranges  
✅ **Full-text Search**: Search descriptions case-insensitively  
✅ **Statistics Dashboard**: Priority, status, completion metrics  
✅ **Bulk Operations**: Create, update, duplicate, search  
✅ **Background Processing**: Async multimedia upload & compression  

---

## Rate Limiting

Multimedia upload endpoint has rate limiting:
- `5 requests per minute` per IP address

---

## Timestamp Format

All timestamps use **milliseconds since Unix epoch**:
- Current time: `int(time.time() * 1000)`
- Example: `1705795200000` = Jan 21, 2024

---

## Notes for Mobile Integration

1. **Quick Actions**: Use `/priority` and `/deadline` endpoints for fast updates
2. **Offline Support**: Use `bulk-update` for syncing multiple changes
3. **Communication**: Check `/communication-options` before triggering automation
4. **Statistics**: Cache `/stats` response for dashboard performance
5. **Search**: Implement debouncing for `/search` endpoint
6. **Upload**: `/multimedia` provides immediate response, processing happens async

---

## TODO: Optional Future Enhancements

- [ ] Comment/notes history on tasks
- [ ] Task custom sorting/reordering
- [ ] Recurring tasks
- [ ] Task templates
- [ ] Collaborative tasks with multiple owners
- [ ] Task attachments metadata (size, type)
- [ ] Advanced search filters (date range, multiple priorities)
- [ ] Export tasks (PDF, CSV)
- [ ] Task history/changelog
- [ ] WebSocket support for real-time updates
