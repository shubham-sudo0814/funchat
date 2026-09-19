"""
Image upload and security validators.
"""

from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image
import os


def validate_image_file(image_file):
    """
    Validates that the uploaded file:
    1. Does not exceed MAX_UPLOAD_SIZE_BYTES.
    2. Has an allowed extension.
    3. Can be opened and identified by Pillow as a valid, non-corrupted image.
    """
    if not image_file:
        return

    # 1. Size Check
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE_BYTES', 5 * 1024 * 1024)
    if image_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum allowed size of {max_mb:.0f} MB.")

    # 2. Extension Check
    ext = os.path.splitext(image_file.name)[1].lower().lstrip('.')
    allowed_exts = getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', ['jpg', 'jpeg', 'png', 'webp', 'gif'])
    if ext not in allowed_exts:
        raise ValidationError(f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(allowed_exts)}.")

    # 3. Pillow Content Verification
    try:
        # Seek to beginning in case file pointer was moved
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
        img.verify()
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
    except Exception as e:
        raise ValidationError("The uploaded file is not a valid or readable image.") from e
