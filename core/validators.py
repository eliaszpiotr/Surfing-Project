import io

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
IMAGE_UPLOAD_ERROR = "Uploaded file is not a valid image. Please upload a JPG, PNG or WebP file."


def validate_uploaded_image(image_file, max_size=None):
    """Validate uploaded image content, size, dimensions, and decoded format."""
    if not isinstance(image_file, UploadedFile):
        return

    if max_size and image_file.size > max_size:
        raise ValidationError(f"Image must be under {max_size // (1024 * 1024)}MB.")

    try:
        data = image_file.read()
        image = Image.open(io.BytesIO(data))
        image.verify()

        image = Image.open(io.BytesIO(data))
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(IMAGE_UPLOAD_ERROR)

        width, height = image.size
        max_pixels = getattr(settings, "IMAGE_UPLOAD_MAX_PIXELS", 20_000_000)
        if width <= 0 or height <= 0 or width * height > max_pixels:
            raise ValidationError("Image dimensions are too large.")
    except ValidationError:
        raise
    except (OSError, UnidentifiedImageError):
        raise ValidationError(IMAGE_UPLOAD_ERROR)
    finally:
        if hasattr(image_file, "seek"):
            image_file.seek(0)
