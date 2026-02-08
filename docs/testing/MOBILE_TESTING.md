# Mobile App Testing Guide (Ngrok)

Since the backend is running locally on your laptop/server, your mobile phone cannot access `http://localhost:8000`. We use **ngrok** to create a secure public tunnel to your local API.

## 1. Start the Backend
Ensure your Docker stack is running:
```bash
docker compose up -d
```
*Verify that the API is available at `http://localhost:8000` on your computer.*

## 2. Start Ngrok Tunnel
Run the following command in your terminal to expose port **8000** (where the API lives):

```bash
ngrok http 8000
```

You will see output like this:
```
Forwarding                    https://a1b2-c3d4.ngrok-free.app -> http://localhost:8000
```

**Copy the `https://...ngrok-free.app` URL.** This is your new "Public API URL".

## 3. Configure the Mobile App
1.  Open your Mobile App project.
2.  Locate the API configuration file (usually `config.dart`, `constants.ts`, or `.env`).
3.  Update the `BASE_URL`:
    ```dart
    // Example for Flutter/Dart
    static const String baseUrl = "https://a1b2-c3d4.ngrok-free.app/api/v1";
    ```
    *Note: Ensure you include `/api/v1` if your endpoints require it.*

## 💡 Architecture Note
**You ONLY need to expose the API port (8000).**

*   **Mobile App** ↔️ **Ngrok Tunnel** ↔️ **API Container** (Publicly Accessible)
*   **API Container** ↔️ **Database/Redis/Workers** (Internally Connected via Docker Network)

The mobile app never speaks directly to the Database or Workers. It sends requests to the API, and the API talks to those services privately. Do **not** try to expose ports 5432 (DB) or 6379 (Redis) via ngrok.

## 4. Testing Checklist
- [ ] **Login/Sign Up**: Verify auth works over the tunnel.
- [ ] **Upload Audio**: Test a short voice note. Ngrok is slower than localhost, so uploads might take longer.
- [ ] **Real-time Updates**: If using WebSockets, ngrok supports them automatically.
- [ ] **Background Processing**: Check if the Celery worker picks up tasks after upload.

## 5. Important Notes
-   **Session Expiry**: Free ngrok URLs change every time you restart ngrok. You must update the mobile app config each time you restart the tunnel.
-   **Rate Limits**: Free accounts have request limits. Don't spam the API too hard during tests.
-   **Security**: Anyone with the URL can access your local API while ngrok is running. Stop ngrok (`Ctrl+C`) when finished.
