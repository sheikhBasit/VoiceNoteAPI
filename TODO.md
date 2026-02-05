# Project TODOs

## ✅ Completed

- [x] **Database Schema Sync**: Verified all columns match models (secondary_role exists)
- [x] **Admin Audit Logging**: Implemented persistent logging to database with `AdminActionLog` model
- [x] **N+1 Query Fixes**: Added eager loading to admin endpoints
- [x] **Schema Validation**: Created utility to detect schema mismatches

## ⏭️ Future Work

### Billing API
- [ ] **Billing API**: The `BillingService` logic exists, but there are no public API endpoints exposed for client-side billing operations (e.g., `POST /checkout` to initiate a Stripe session). Currently, the system relies solely on Stripe Webhooks.
  - **Action**: Implement `BillingRouter` with endpoints for creating checkout sessions and fetching wallet balance.

### Meetings Module
- [ ] **Meetings Module**: The endpoint `POST /meetings/join` returns 500/401 because the Recall.ai API Key is missing.
  - **Action**: Obtain Recall.ai credentials and add `RECALL_API_KEY` to the `.env` file / Docker environment variables.

### Future Improvements
- [ ] **Browser Testing**: Troubleshoot `Failed to fetch` errors in Playwright tests (likely CORS or network binding in Docker).
- [ ] **Speaker Continuity Detection**: Implement logic in `audio_chunker.py` to detect when same speaker continues across chunks.
