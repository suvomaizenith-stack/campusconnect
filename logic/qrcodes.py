"""QR codes that open the report form with a campus place already chosen."""
import io
from functools import lru_cache
from urllib.parse import urlencode

import qrcode


def report_link(base: str, slug: str) -> str:
    return f"{base.rstrip('/')}/report?{urlencode({'landmark': slug})}"


@lru_cache(maxsize=256)
def png(url: str) -> bytes:
    buf = io.BytesIO()
    qrcode.make(url, box_size=10, border=3).save(buf, format="PNG")
    return buf.getvalue()
