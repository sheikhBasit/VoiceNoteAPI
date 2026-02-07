import json
import os

import firebase_admin
from firebase_admin import credentials, messaging

from app.utils.json_logger import JLogger


class NotificationService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        try:
            # Check for service account path or base64 env var
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

            cred = None
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
            elif service_account_json:
                cred = credentials.Certificate(json.loads(service_account_json))

            if cred:
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                JLogger.info("Firebase Admin SDK initialized successfully")
            else:
                JLogger.warning(
                    "Firebase credentials not found. Push notifications will be mocked."
                )
        except Exception as e:
            JLogger.error("Failed to initialize Firebase Admin SDK", error=str(e))

    @staticmethod
    def send_multicast(tokens: list, title: str, body: str, data: dict = None):
        if not NotificationService._initialized:
            NotificationService.initialize()

        if not NotificationService._initialized:
            JLogger.info(
                "Mocking Push Notification (Service not init)",
                count=len(tokens),
                title=title,
            )
            return {"success_count": len(tokens), "failure_count": 0}

        try:
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        icon="stock_ticker_update", color="#f45342"
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(badge=42, sound="default"),
                    ),
                ),
            )
            response = messaging.send_multicast(message)
            JLogger.info(
                "Push notification multicast sent",
                success_count=response.success_count,
                failure_count=response.failure_count,
            )
            return response
        except Exception as e:
            JLogger.error("Failed to send multicast push notification", error=str(e))
            raise e

    @staticmethod
    def send_to_token(token: str, title: str, body: str, data: dict = None):
        if not NotificationService._initialized:
            NotificationService.initialize()

        if not NotificationService._initialized:
            JLogger.info(
                "Mocking Push Notification (Service not init)",
                token=token[-10:],
                title=title,
            )
            return "mock-message-id"

        try:
            message = messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
            )
            response = messaging.send(message)
            JLogger.info("Push notification sent", message_id=response)
            return response
        except Exception as e:
            JLogger.error(
                "Failed to send push notification", token=token[-10:], error=str(e)
            )
            raise e
