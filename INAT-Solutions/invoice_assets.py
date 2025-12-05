import io
from typing import Optional
from reportlab.lib.utils import ImageReader
from settings_store import get_blob

def get_invoice_logo_imagereader() -> Optional[ImageReader]:
    data, mime = get_blob("invoice_logo")
    if not data:
        return None
    return ImageReader(io.BytesIO(data))
