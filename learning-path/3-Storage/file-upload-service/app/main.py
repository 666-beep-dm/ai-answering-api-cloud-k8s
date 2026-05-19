import os
import uuid
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="File Upload Service",
    description="Async file upload service built with FastAPI",
    version="1.0.0",
)


@app.post("/upload", summary="Upload a file", tags=["files"])
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Accept a file via multipart/form-data, validate it, and save it."""

    # --- Validate: non-empty content ---
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Generate unique filename ---
    ext = os.path.splitext(file.filename or "")[-1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    # --- Persist file asynchronously ---
    async with aiofiles.open(dest_path, "wb") as out_file:
        await out_file.write(contents)

    return JSONResponse(
        status_code=201,
        content={"filename": unique_name, "original_filename": file.filename, "status": "uploaded"},
    )


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
