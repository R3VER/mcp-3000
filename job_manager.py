import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import DATABASE_PATH


# Job states
UPLOADED = "UPLOADED"
PROCESSING = "PROCESSING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"


def _now():
    """
    Return current UTC time as an ISO string.
    """
    return datetime.now(timezone.utc).isoformat()


def _connect():
    """
    Create a connection to the existing SQLite database.
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_jobs_table():
    """
    Create the jobs table if it does not already exist.
    """
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                status TEXT NOT NULL,
                result_path TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.commit()


def create_job(original_filename, stored_path):
    """
    Create a new upload-processing job.

    Returns:
        job_id (str)
    """
    initialize_jobs_table()

    job_id = uuid4().hex
    now = _now()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                job_id,
                original_filename,
                stored_path,
                status,
                result_path,
                error,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                original_filename,
                str(stored_path),
                UPLOADED,
                None,
                None,
                now,
                now,
            ),
        )

        conn.commit()

    return job_id


def get_job(job_id):
    """
    Get one job by ID.

    Returns:
        dict | None
    """
    initialize_jobs_table()

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                job_id,
                original_filename,
                stored_path,
                status,
                result_path,
                error,
                created_at,
                updated_at
            FROM jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def update_job_status(job_id, status, error=None):
    """
    Update the processing status of a job.
    """
    initialize_jobs_table()

    now = _now()

    with _connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                error = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                status,
                error,
                now,
                job_id,
            ),
        )

        conn.commit()


def mark_job_processing(job_id):
    """
    Mark a job as currently processing.
    """
    update_job_status(
        job_id=job_id,
        status=PROCESSING,
        error=None,
    )


def mark_job_completed(job_id, result_path):
    """
    Mark a job as completed and store its result file path.
    """
    initialize_jobs_table()

    now = _now()

    with _connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                result_path = ?,
                error = NULL,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                COMPLETED,
                str(result_path),
                now,
                job_id,
            ),
        )

        conn.commit()


def mark_job_failed(job_id, error):
    """
    Mark a job as failed and store the error message.
    """
    update_job_status(
        job_id=job_id,
        status=FAILED,
        error=str(error),
    )


def list_jobs(limit=50):
    """
    Return the most recent jobs.

    Returns:
        list[dict]
    """
    initialize_jobs_table()

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                job_id,
                original_filename,
                stored_path,
                status,
                result_path,
                error,
                created_at,
                updated_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_jobs_table()

    test_job_id = create_job(
        original_filename="test.docx",
        stored_path="data/uploads/test.docx",
    )

    print("Created job:")
    print(test_job_id)

    print("\nJob details:")
    print(get_job(test_job_id))

    mark_job_processing(test_job_id)

    print("\nAfter PROCESSING:")
    print(get_job(test_job_id))

    mark_job_completed(
        test_job_id,
        "data/output/test_result.pdf",
    )

    print("\nAfter COMPLETED:")
    print(get_job(test_job_id))