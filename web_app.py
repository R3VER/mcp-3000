from pathlib import Path
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile

from upload_handler import save_uploaded_file
from job_manager import get_job


app = FastAPI(
    title="Pollution Evaluation API",
    description="Upload a pollution-opinion document and create a processing job.",
    version="1.0.0",
)


ALLOWED_EXTENSIONS = {
    ".docx",
    ".pdf",
    ".txt",
}


@app.get("/health")
def health_check():
    """
    Simple health-check endpoint.
    """
    return {
        "status": "ok",
        "service": "Pollution Evaluation API",
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    """
    Receive a document uploaded by the user,
    temporarily save it,
    and create a processing job.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {extension}. "
                f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    temp_path = None

    try:
        # Create a temporary file.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temp_file:

            temp_path = Path(temp_file.name)

            # Copy uploaded file into the temporary file.
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                temp_file.write(chunk)

        # Pass the temporary file to our existing upload handler.
        result = save_uploaded_file(temp_path)

        return {
            "success": True,
            "message": "File uploaded successfully.",
            "job_id": result["job_id"],
            "filename": result["original_filename"],
            "stored_path": result["stored_path"],
            "status": "UPLOADED",
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        )

    finally:
        # Remove temporary file.
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Get the current status of a processing job.
    """

    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return {
        "success": True,
        "job": job,
    }