from __future__ import annotations

from typing import List
import fitz  # PyMuPDF


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[bytes]:
    """Render each PDF page to PNG bytes."""
    images: List[bytes] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
    return images


