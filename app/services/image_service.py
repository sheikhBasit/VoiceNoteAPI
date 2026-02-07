from PIL import Image

from app.utils.json_logger import JLogger


class ImageService:
    @staticmethod
    def process_image(
        file_path: str, output_path: str, max_size=(1024, 1024), quality=85
    ):
        """
        Compress and resize image for general usage.
        """
        try:
            with Image.open(file_path) as img:
                # Convert RGBA to RGB if saving as JPEG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(output_path, "JPEG", quality=quality, optimize=True)
                return True
        except Exception as e:
            JLogger.error("Image compression failed", path=file_path, error=str(e))
            return False

    @staticmethod
    def generate_thumbnail(file_path: str, thumb_path: str, size=(200, 200)):
        """
        Generate a small thumbnail for lists/RecyclerVies.
        """
        try:
            with Image.open(file_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumb_path, "JPEG", quality=70, optimize=True)
                return True
        except Exception as e:
            JLogger.error("Thumbnail generation failed", path=file_path, error=str(e))
            return False
