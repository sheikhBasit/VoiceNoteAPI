import os
from pathlib import Path
from typing import List, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.config import email_config
from app.utils.json_logger import JLogger

class EmailService:
    """
    Service for sending transactional emails using SMTP.
    """
    
    _conf = ConnectionConfig(
        MAIL_USERNAME=email_config.MAIL_USERNAME,
        MAIL_PASSWORD=email_config.MAIL_PASSWORD,
        MAIL_FROM=email_config.MAIL_FROM,
        MAIL_PORT=email_config.MAIL_PORT,
        MAIL_SERVER=email_config.MAIL_SERVER,
        MAIL_FROM_NAME=email_config.MAIL_FROM_NAME,
        MAIL_STARTTLS=email_config.MAIL_STARTTLS,
        MAIL_SSL_TLS=email_config.MAIL_SSL_TLS,
        USE_CREDENTIALS=email_config.USE_CREDENTIALS,
        VALIDATE_CERTS=email_config.VALIDATE_CERTS,
        TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "email",
    )
    
    _fastmail = FastMail(_conf)

    @classmethod
    async def send_email(
        cls, 
        subject: str, 
        recipients: List[EmailStr], 
        body: str, 
        subtype: MessageType = MessageType.html,
        template_name: Optional[str] = None,
        template_body: Optional[dict] = None
    ):
        """
        Generic method to send an email.
        """
        try:
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=body,
                subtype=subtype,
                template_body=template_body
            )
            
            if template_name:
                await cls._fastmail.send_message(message, template_name=template_name)
            else:
                await cls._fastmail.send_message(message)
                
            JLogger.info("Email sent successfully", subject=subject, recipients=recipients)
            return True
        except Exception as e:
            JLogger.error("Failed to send email", subject=subject, recipients=recipients, error=str(e))
            # Fallback to console log in development if SMTP fails
            if os.getenv("ENVIRONMENT") != "production":
                print(f"\n[EMAIL FALLBACK] Sent to: {recipients}")
                print(f"Subject: {subject}")
                print(f"Body: {body}\n")
            return False

    @classmethod
    async def send_password_reset_email(cls, email: str, token: str, user_name: str):
        """
        Sends a password reset email to the user.
        """
        # In a real app, this would be a link to the frontend
        # For now, we use a placeholder URL
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={token}"
        
        subject = "Reset Your VoiceNote AI Password"
        template_body = {
            "user_name": user_name,
            "reset_link": reset_link,
            "expire_minutes": 30
        }
        
        # Plain text fallback
        body = f"Hello {user_name},\n\nYou requested to reset your password. Click the link below to set a new password:\n{reset_link}\n\nThis link expires in 30 minutes."
        
        return await cls.send_email(
            subject=subject,
            recipients=[email],
            body=body,
            template_name="password_reset.html",
            template_body=template_body
        )

    @classmethod
    async def send_device_verification_email(cls, email: str, link: str):
        """
        Sends a device verification email.
        """
        subject = "Verify New Device Login - VoiceNote AI"
        template_body = {
            "verification_link": link,
            "expire_minutes": 15
        }
        
        body = f"Authorize your new device by clicking here: {link}\nThis link expires in 15 minutes."
        
        return await cls.send_email(
            subject=subject,
            recipients=[email],
            body=body,
            template_name="device_verification.html",
            template_body=template_body
        )
