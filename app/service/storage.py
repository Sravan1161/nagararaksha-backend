import os
import uuid

from fastapi import UploadFile
from PIL import Image

from app.config import settings

os.makedirs(settings.upload_dir, exist_ok=True)


def save_photo(file: UploadFile) -> str:
    """Saves an uploaded photo to local disk, resized/compressed, and returns a relative URL.

    Swap this function's body for an S3 / Cloudinary / Firebase Storage upload
    when moving beyond local development -- the rest of the app only depends
    on getting a URL string back.
    """
    ext = ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.upload_dir, filename)

    image = Image.open(file.file).convert("RGB")
    if image.width > settings.max_photo_width:
        ratio = settings.max_photo_width / image.width
        image = image.resize((settings.max_photo_width, int(image.height * ratio)))
    image.save(path, "JPEG", quality=75)

    return f"/uploads/{filename}"


def photo_path_from_url(url: str) -> str:
    filename = url.rsplit("/", 1)[-1]
    return os.path.join(settings.upload_dir, filename)
