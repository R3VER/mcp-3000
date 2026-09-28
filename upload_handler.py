from pathlib import Path
import shutil

from config import BASE_DIR
from job_manager import create_job


UPLOAD_DIR = BASE_DIR / "data" / "uploads"


ALLOWED_EXTENSIONS = {
    ".docx",
    ".pdf",
    ".txt",
}


def save_uploaded_file(file_path):
    """
    Save an uploaded file into a job-specific folder.

    Args:
        file_path: path to the uploaded file

    Returns:
        dict containing job information and stored file path
    """

    source_path = Path(file_path)

    if not source_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {source_path}"
        )

    extension = source_path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Create a temporary job ID first.
    # We need the ID so the uploaded file gets its own folder.
    temp_job_id = None

    # Create the base upload directory.
    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create a temporary directory based on filename.
    # The actual job record is created immediately afterward.
    import uuid

    temp_job_id = uuid.uuid4().hex

    job_dir = UPLOAD_DIR / temp_job_id
    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path = job_dir / source_path.name

    shutil.copy2(
        source_path,
        destination_path,
    )

    # Now create the actual job.
    job_id = create_job(
        original_filename=source_path.name,
        stored_path=destination_path,
    )

    # Rename the temporary folder to the actual job ID.
    actual_job_dir = UPLOAD_DIR / job_id

    if actual_job_dir != job_dir:
        job_dir.rename(actual_job_dir)

        destination_path = actual_job_dir / source_path.name

        # Update the database because the stored path changed.
        from job_manager import _connect

        with _connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET stored_path = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    str(destination_path),
                    _get_current_time(),
                    job_id,
                ),
            )

            conn.commit()

    return {
        "job_id": job_id,
        "original_filename": source_path.name,
        "stored_path": str(destination_path),
    }


def _get_current_time():
    """
    Return current UTC time as an ISO string.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    print("Upload handler is ready.")
    print("Allowed extensions:")

    for extension in sorted(ALLOWED_EXTENSIONS):
        print(f"  {extension}")