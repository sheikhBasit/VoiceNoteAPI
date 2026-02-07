from datetime import timedelta

from minio import Minio

from app.core.config import ai_config
from app.utils.json_logger import JLogger


class StorageService:
    def __init__(self):
        self.client = Minio(
            ai_config.MINIO_ENDPOINT,
            access_key=ai_config.MINIO_ACCESS_KEY,
            secret_key=ai_config.MINIO_SECRET_KEY,
            secure=ai_config.MINIO_SECURE,
        )
        self.bucket_name = ai_config.MINIO_BUCKET_NAME

    def generate_presigned_put_url(self, object_name: str, expires_delta: int = 3600):
        """Generates a pre-signed URL for the client to upload (PUT) directly to MinIO."""
        try:
            url = self.client.presigned_put_object(
                self.bucket_name, object_name, expires=timedelta(seconds=expires_delta)
            )
            return url
        except Exception as e:
            JLogger.error(
                "Failed to generate pre-signed URL",
                error=str(e),
                object_name=object_name,
            )
            raise e

    def download_file(self, object_name: str, local_path: str):
        """Downloads a file from MinIO to a local path for processing."""
        try:
            self.client.fget_object(self.bucket_name, object_name, local_path)
            JLogger.info(
                "File downloaded from storage",
                object_name=object_name,
                local_path=local_path,
            )
            return local_path
        except Exception as e:
            JLogger.error(
                "Failed to download file from storage",
                error=str(e),
                object_name=object_name,
            )
            raise e

    def delete_file(self, object_name: str):
        """Removes a file from MinIO transit storage."""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            JLogger.info("File deleted from storage", object_name=object_name)
        except Exception as e:
            JLogger.error(
                "Failed to delete file from storage",
                error=str(e),
                object_name=object_name,
            )
            # We don't necessarily want to crash the worker if cleanup fails,
            # but we should log it for auditing.
