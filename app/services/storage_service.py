from datetime import timedelta

from minio import Minio

from app.core.config import ai_config
from app.utils.json_logger import JLogger

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac", ".opus"}
MAX_DOWNLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500MB safety limit


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
        # Validate file extension
        import os
        _, ext = os.path.splitext(object_name)
        if ext.lower() not in ALLOWED_AUDIO_EXTENSIONS:
            raise ValueError(
                f"Invalid file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
            )

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
            # Check file size before downloading to prevent memory exhaustion
            stat = self.client.stat_object(self.bucket_name, object_name)
            if stat.size > MAX_DOWNLOAD_SIZE_BYTES:
                raise ValueError(
                    f"File too large ({stat.size / 1024 / 1024:.0f}MB). "
                    f"Maximum download size is {MAX_DOWNLOAD_SIZE_BYTES / 1024 / 1024:.0f}MB."
                )

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

    def delete_file(self, object_name: str, owner_user_id: str = None):
        """
        Removes a file from MinIO transit storage.
        If owner_user_id is provided, validates the object path belongs to that user.
        """
        # Ownership check: object_name format is "user_id/note_id.wav"
        if owner_user_id and not object_name.startswith(f"{owner_user_id}/"):
            JLogger.warning(
                "Storage delete blocked: ownership mismatch",
                object_name=object_name,
                claimed_owner=owner_user_id,
            )
            raise PermissionError("You do not own this file")

        try:
            self.client.remove_object(self.bucket_name, object_name)
            JLogger.info("File deleted from storage", object_name=object_name)
        except Exception as e:
            JLogger.error(
                "Failed to delete file from storage",
                error=str(e),
                object_name=object_name,
            )

    def delete_note_files(self, user_id: str, note_id: str):
        """
        Cleans up all storage files associated with a note.
        Called during hard delete to prevent orphaned files.
        """
        prefix = f"{user_id}/{note_id}"
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix)
            for obj in objects:
                self.client.remove_object(self.bucket_name, obj.object_name)
                JLogger.info("Orphaned file cleaned", object_name=obj.object_name)
        except Exception as e:
            JLogger.error(
                "Failed to clean up note files",
                error=str(e),
                prefix=prefix,
            )
