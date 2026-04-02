from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}


async def extract_text_from_file(file: UploadFile) -> str:
    ext = PurePosixPath(file.filename or "").suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    content = await file.read()
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=415,
            detail="File is not valid UTF-8 text. Please upload a plain text file.",
        )
