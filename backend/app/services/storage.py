import os
import uuid
from fastapi import UploadFile, HTTPException
from app.config import settings

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 # 10MB

async def save_upload_file(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 10MB limit."
        )

    unique_filename = f"{uuid.uuid4().hex}{ext}"

    if settings.STORAGE_TYPE == "cloudinary" and settings.CLOUDINARY_URL:
        # Cloudinary integration hook
        try:
            import cloudinary
            import cloudinary.uploader
            res = cloudinary.uploader.upload(content, public_id=unique_filename)
            return res.get("secure_url")
        except Exception:
            pass # fallback to local storage

    # Local storage default
    dest_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    return f"/uploads/{unique_filename}"
