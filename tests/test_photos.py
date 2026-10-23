import io

from PIL import Image

from config import PHOTO_MAX_PX
from logic.photos import shrink_photo


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "teal").save(buf, format="PNG")
    return buf.getvalue()


def test_large_photo_is_capped_and_jpeg():
    data, mime = shrink_photo(_png(2400, 1600))
    img = Image.open(io.BytesIO(data))
    assert mime == "image/jpeg"
    assert img.format == "JPEG"
    assert max(img.size) == PHOTO_MAX_PX


def test_small_photo_is_not_upscaled():
    data, _ = shrink_photo(_png(300, 200))
    assert Image.open(io.BytesIO(data)).size == (300, 200)
