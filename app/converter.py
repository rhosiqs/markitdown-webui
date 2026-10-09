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
