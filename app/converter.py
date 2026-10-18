from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

# pdfminer logs a warning for every malformed font descriptor; the text is still extracted.
logging.getLogger("pdfminer").setLevel(logging.ERROR)


def convert_bytes(data: bytes, extension: str) -> str:
    """Convert an in-memory upload using MarkItDown's stream API."""
    try:
        from markitdown import MarkItDown, StreamInfo
    except ImportError as exc:  # pragma: no cover - dependency installation issue
        raise RuntimeError(
            "MarkItDown is not installed. Run pip install -r requirements.txt."
        ) from exc

    converter = MarkItDown(enable_plugins=False)
    stream_info = StreamInfo(extension=extension)
    result: Any = converter.convert_stream(BytesIO(data), stream_info=stream_info)

    markdown = getattr(result, "markdown", None)
    if markdown is None:
        markdown = getattr(result, "text_content", None)
    if not isinstance(markdown, str):
        raise RuntimeError("The converter did not return Markdown text.")
    return markdown


def describe_conversion_error(exc: Exception) -> str:
    """Turn a converter exception into a short message for the user."""
    message = str(exc).strip()
    lowered = message.lower()
    if "missingdependency" in lowered or "install" in lowered and "markitdown" in lowered:
        return (
            "This format needs extra conversion components. "
            "Run pip install -r requirements.txt to install them."
        )
    if "not a valid office open xml" in lowered:
        return "The file is not a valid Office Open XML document, or it is damaged."
    if not message:
        return "Conversion failed. The file may be damaged or in an unsupported format."
    return f"Conversion failed: {message[:500]}"
