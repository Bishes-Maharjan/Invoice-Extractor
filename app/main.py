import base64
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.services.gemini import DEFAULT_MODEL, extract_image_content

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Invoice Extractor")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".heic", ".heif"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def get_mime_type(filename: str, content_type: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'.")
    if content_type and content_type != "application/octet-stream":
        return content_type

    return "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"



@app.get("/", include_in_schema=False)
async def serve_home():
    return FileResponse(BASE_DIR / "templates/index.html")

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    image_bytes = await file.read()

    if not image_bytes:
        return JSONResponse({"success": False, "error": "Uploaded file is empty."}, status_code=400)
    if len(image_bytes) > MAX_FILE_SIZE:
        return JSONResponse({"success": False, "error": "File exceeds 20 MB limit."}, status_code=400)

    try:
        mime_type = get_mime_type(file.filename, file.content_type)
        data = await extract_image_content(image_bytes=image_bytes, mime_type=mime_type)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    return JSONResponse({
        "success": True,
        "data": data,
        "image_base64": f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}",
    })
