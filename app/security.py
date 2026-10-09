from __future__ import annotations

from pathlib import Path

ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".xls",
        ".html",
        ".htm",
        ".csv",
        ".json",
        ".xml",
        ".txt",
        ".md",
        ".epub",
        ".msg",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".wav",
        ".mp3",
        ".m4a",
    }
)


def safe_filename(filename: str | None) -> str:
    if not filename:
        raise ValueError("The file has no name.")
    normalized = filename.replace("\\", "/")
    basename = Path(normalized).name.strip()
    if not basename or basename in {".", ".."}:
        raise ValueError("The file name is invalid.")
    if len(basename) > 240:
        raise ValueError("The file name is too long.")
    return basename


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if not extension or extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file format. Supported formats: {allowed}")
    return extension


def output_filename(source_filename: str) -> str:
    stem = Path(source_filename).stem.strip() or "converted"
    cleaned = "".join(ch for ch in stem if ch not in '<>:"/\\|?*\0').strip(" .")
    return f"{cleaned or 'converted'}.md"
