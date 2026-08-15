import io
import re

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover - optional dep
    PdfReader = None


def extract_pdf_text(file_like) -> str:
    try:
        raw = file_like.read()
        if hasattr(file_like, "seek"):
            file_like.seek(0)
        if not raw or not raw.lstrip().startswith(b"%PDF-"):
            return ""
        reader = PdfReader(io.BytesIO(raw), strict=False)
        parts: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
