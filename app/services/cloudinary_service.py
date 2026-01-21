import cloudinary
import cloudinary.uploader
import os
from fastapi import HTTPException
from PIL import Image # Use 'pip install Pillow'
import uuid

class CloudinaryService:
    def __init__(self):
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
        # Ensure local upload directory exists for temporary processing
        self.upload_dir = "uploads"
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def upload_audio(self, processed_file_path: str, public_id: str):
        """Uploads already-processed/enhanced audio from the local uploads folder."""
        try:
            # Verify file exists in uploads before proceeding
            if not os.path.exists(processed_file_path):
                raise FileNotFoundError(f"Processed audio not found at {processed_file_path}")

            result = cloudinary.uploader.upload(
                processed_file_path,
                resource_type="video", # Cloudinary uses "video" for audio
                public_id=f"voicenotes/audio/{public_id}",
                folder="voicenote_ai/recordings"
            )
            
            # Optionally remove the local file after successful upload
            # os.remove(processed_file_path) 
            return result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary Audio Error: {str(e)}")

    def upload_compressed_image(self, original_file_path: str, task_id: str):
        """Compresses a local image and then uploads it."""
        try:
            compressed_path = os.path.join(self.upload_dir, f"comp_{task_id}.jpg")
            
            # Image Processing: Resize and Compress
            with Image.open(original_file_path) as img:
                # Convert to RGB if necessary (handles PNG/RGBA)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Maintain aspect ratio but ensure it's not excessively large for a task note
                img.thumbnail((1280, 1280)) 
                
                # Save with optimization and 70% quality for high compression
                img.save(compressed_path, "JPEG", optimize=True, quality=70)

            # Upload the processed version
            result = cloudinary.uploader.upload(
                compressed_path,
                resource_type="image",
                public_id=f"tasks/images/{task_id}",
                folder="voicenote_ai/tasks"
            )

            # Cleanup local files
            if os.path.exists(compressed_path): os.remove(compressed_path)
            return result.get("secure_url")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image Processing/Upload Error: {str(e)}")
