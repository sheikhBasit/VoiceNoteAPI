# Project TODOs

## Missing Implementations

- [ ] **Billing API**: The `BillingService` logic exists, but there are no public API endpoints exposed for client-side billing operations (e.g., `POST /checkout` to initiate a Stripe session). Currently, the system relies solely on Stripe Webhooks.
  - **Action**: Implement `BillingRouter` with endpoints for creating checkout sessions and fetching wallet balance.

## Configuration Required

- [ ] **Meetings Module**: The endpoint `POST /meetings/join` returns 500/401 because the Recall.ai API Key is missing.
  - **Action**: Obtain Recall.ai credentials and add `RECALL_API_KEY` to the `.env` file / Docker environment variables.

## Database Schema

- [ ] **User Role Alignment**: The `users` table might be missing the `secondary_role` column (observed in logs).
  - **Action**: Verify `alembic` migrations are up to date and sync the schema.

## Future Improvements

- [ ] **Browser Testing**: Troubleshoot `Failed to fetch` errors in Playwright tests (likely CORS or network binding in Docker).
