"""Shrink ticket photos before they are stored as bytea."""
import io

from PIL import Image, ImageOps

from config import PHOTO_MAX_PX


def shrink_photo(data: bytes) -> tuple[bytes, str]:
    """Return (JPEG bytes, mime) with the longest side at most PHOTO_MAX_PX. Raises PIL errors on bad input."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((PHOTO_MAX_PX, PHOTO_MAX_PX))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue(), "image/jpeg"
