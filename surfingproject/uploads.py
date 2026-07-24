import io
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from PIL import Image

from core.validators import validate_uploaded_image


def _secure_image_name(prefix):
    return f"{prefix}/{uuid.uuid4().hex}.jpg"


def profile_picture_upload_path(instance, filename):
    return _secure_image_name("profile_pictures")


def spot_image_upload_path(instance, filename):
    return _secure_image_name("spots_images")


def spot_gallery_upload_path(instance, filename):
    return _secure_image_name("spot_gallery")


def normalize_uploaded_image(image_file, upload_dir, max_size=None):
    """Return a JPEG upload with a server-generated name and metadata stripped."""
    validate_uploaded_image(image_file, max_size=max_size)
    if not isinstance(image_file, UploadedFile):
        return image_file

    data = image_file.read()
    source = Image.open(io.BytesIO(data))
    source.load()

    if source.mode not in ("RGB", "L"):
        source = source.convert("RGB")
    elif source.mode == "L":
        source = source.convert("RGB")

    output = io.BytesIO()
    source.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)
    image_file.seek(0)

    return SimpleUploadedFile(
        _secure_image_name(upload_dir),
        output.getvalue(),
        content_type="image/jpeg",
    )
