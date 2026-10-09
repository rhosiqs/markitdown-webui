from __future__ import annotations

import asyncio
import mimetypes
import time
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import BASE_DIR, SETTINGS
from .converter import convert_bytes
from .preview import render_markdown
from .security import output_filename, safe_filename, validate_extension

# Windows reads MIME types from the registry, which often maps .js to text/plain.
# With the nosniff header the browser then refuses to run the script.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

app = FastAPI(
    title=SETTINGS.app_name,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class MarkdownPayload(BaseModel):
    markdown: str = Field(default="", max_length=SETTINGS.max_markdown_chars)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": SETTINGS.app_name,
            "max_upload_mb": SETTINGS.max_upload_bytes // (1024 * 1024),
        },
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/convert")
async def convert(file: UploadFile = File(...)) -> dict[str, object]:
    try:
        filename = safe_filename(file.filename)
        extension = validate_extension(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started = time.perf_counter()
    data = await _read_limited(file, SETTINGS.max_upload_bytes)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")

    try:
        markdown = await asyncio.to_thread(convert_bytes, data, extension)
    except Exception as exc:
        detail = _humanize_conversion_error(exc)
        raise HTTPException(status_code=422, detail=detail) from exc

    return {
        "filename": filename,
        "output_filename": output_filename(filename),
        "markdown": markdown,
        "source_bytes": len(data),
        "markdown_chars": len(markdown),
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    }


@app.post("/api/render")
async def render(payload: MarkdownPayload) -> dict[str, str]:
    return {"html": render_markdown(payload.markdown)}


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"The file exceeds the {limit // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _humanize_conversion_error(exc: Exception) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if "missingdependency" in lowered or "install" in lowered and "markitdown" in lowered:
        return "This format needs extra conversion components. Run pip install -r requirements.txt to install them."
    if "not a valid office open xml" in lowered:
        return "The file is not a valid Office Open XML document, or it is damaged."
    if not message:
        return "Conversion failed. The file may be damaged or in an unsupported format."
    return f"Conversion failed: {message[:500]}"
