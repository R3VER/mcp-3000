import json
import sqlite3
from pathlib import Path

from model import (
    Opinion,
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED,
    NO_CONTENT,
)


# =================================================
# BOUNDARY BATCH STATUS
# =================================================

BOUNDARY_PENDING = "PENDING"
BOUNDARY_PROCESSING = "PROCESSING"
BOUNDARY_REVIEWED = "REVIEWED"
BOUNDARY_FAILED = "FAILED"


# =================================================
# DATABASE CONNECTION
# =================================================

def get_connection(
    database_path: Path
) -> sqlite3.Connection:

    database_path = Path(
        database_path
    )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        database_path,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


# =================================================
# INITIALIZE DATABASE
# =================================================

def initialize_database(
    database_path: Path
) -> None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    # =================================================
    # OPINIONS TABLE
    # =================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opinions (
            opinion_id INTEGER PRIMARY KEY,
            submitter TEXT,
            text TEXT NOT NULL,
            source_paragraphs TEXT,
            status TEXT NOT NULL,
            error TEXT
        )
        """
    )

    # =================================================
    # EVALUATIONS TABLE
    # =================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            opinion_id INTEGER PRIMARY KEY,
            criterion_1 INTEGER NOT NULL,
            criterion_2 INTEGER NOT NULL,
            criterion_3 INTEGER NOT NULL,
            criterion_4 INTEGER NOT NULL,
            criterion_5 INTEGER NOT NULL,
            total_score REAL NOT NULL,
            reasoning TEXT,
            FOREIGN KEY (opinion_id)
                REFERENCES opinions(opinion_id)
        )
        """
    )

    # =================================================
    # BOUNDARY REVIEWS TABLE
    # =================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS boundary_reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_opinion_id INTEGER NOT NULL,
            opinion_ids TEXT NOT NULL,
            decisions TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =================================================
    # BOUNDARY BATCHES TABLE
    # =================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS boundary_batches (
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_opinion_id INTEGER NOT NULL UNIQUE,
            end_opinion_id INTEGER NOT NULL,
            batch_size INTEGER NOT NULL,
            status TEXT NOT NULL,
            review_id INTEGER,
            error TEXT,
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =================================================
    # CHECK EXISTING OPINIONS COLUMNS
    # =================================================

    cursor.execute(
        "PRAGMA table_info(opinions)"
    )

    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    # =================================================
    # ADD source_paragraphs IF MISSING
    # =================================================

    if (
        "source_paragraphs"
        not in existing_columns
    ):

        cursor.execute(
            """
            ALTER TABLE opinions
            ADD COLUMN source_paragraphs TEXT
            """
        )

    connection.commit()

    connection.close()


# =================================================
# CLEAR OPINIONS
# =================================================

def clear_opinions(
    database_path: Path
) -> None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM evaluations"
    )

    cursor.execute(
        "DELETE FROM opinions"
    )

    connection.commit()

    connection.close()


# =================================================
# SAVE OPINION
# =================================================

def save_opinion(
    database_path: Path,
    opinion: Opinion
) -> None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    source_paragraphs_json = json.dumps(
        opinion.source_paragraphs or [],
        ensure_ascii=False
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO opinions (
            opinion_id,
            submitter,
            text,
            source_paragraphs,
            status,
            error
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            opinion.opinion_id,
            opinion.submitter,
            opinion.text,
            source_paragraphs_json,
            opinion.status,
            opinion.error,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# CONVERT DATABASE ROW TO OPINION
# =================================================

def row_to_opinion(
    row: sqlite3.Row
) -> Opinion:

    try:

        source_paragraphs = json.loads(
            row["source_paragraphs"]
        )

    except (
        TypeError,
        json.JSONDecodeError
    ):

        source_paragraphs = []

    return Opinion(
        opinion_id=row["opinion_id"],
        text=row["text"],
        submitter=row["submitter"],
        source_paragraphs=source_paragraphs,
        status=row["status"],
        error=row["error"],
    )


# =================================================
# GET NEXT PENDING OPINION
# =================================================

def get_next_pending_opinion(
    database_path: Path
) -> Opinion | None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT
            opinion_id,
            submitter,
            text,
            source_paragraphs,
            status,
            error
        FROM opinions
        WHERE status = ?
        ORDER BY opinion_id
        LIMIT 1
        """,
        (PENDING,)
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return row_to_opinion(row)


# =================================================
# CLAIM NEXT PENDING OPINION
# =================================================

def claim_next_pending_opinion(
    database_path: Path
) -> Opinion | None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        row = cursor.execute(
            """
            SELECT
                opinion_id,
                submitter,
                text,
                source_paragraphs,
                status,
                error
            FROM opinions
            WHERE status = ?
            ORDER BY opinion_id
            LIMIT 1
            """,
            (PENDING,)
        ).fetchone()

        if row is None:

            connection.commit()

            return None

        opinion_id = row["opinion_id"]

        cursor.execute(
            """
            UPDATE opinions
            SET
                status = ?,
                error = NULL
            WHERE opinion_id = ?
              AND status = ?
            """,
            (
                PROCESSING,
                opinion_id,
                PENDING
            )
        )

        connection.commit()

        try:

            source_paragraphs = json.loads(
                row["source_paragraphs"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_paragraphs = []

        return Opinion(
            opinion_id=row["opinion_id"],
            text=row["text"],
            submitter=row["submitter"],
            source_paragraphs=source_paragraphs,
            status=PROCESSING,
            error=None,
        )

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# =================================================
# UPDATE OPINION STATUS
# =================================================

def update_opinion_status(
    database_path: Path,
    opinion_id: int,
    status: str,
    error: str | None = None
) -> None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE opinions
        SET
            status = ?,
            error = ?
        WHERE opinion_id = ?
        """,
        (
            status,
            error,
            opinion_id
        )
    )

    connection.commit()

    connection.close()


# =================================================
# SAVE EVALUATION
# =================================================

def save_evaluation(
    database_path: Path,
    opinion_id: int,
    criterion_scores: dict[str, int],
    total_score: float,
    reasoning: dict[str, str]
) -> None:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO evaluations (
            opinion_id,
            criterion_1,
            criterion_2,
            criterion_3,
            criterion_4,
            criterion_5,
            total_score,
            reasoning
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opinion_id,
            criterion_scores["1"],
            criterion_scores["2"],
            criterion_scores["3"],
            criterion_scores["4"],
            criterion_scores["5"],
            total_score,
            json.dumps(
                reasoning,
                ensure_ascii=False
            ),
        )
    )

    connection.commit()

    connection.close()


# =================================================
# SAVE BOUNDARY REVIEW
# =================================================

def save_boundary_review(
    database_path: Path,
    start_opinion_id: int,
    opinion_ids: list[int],
    decisions: list[dict]
) -> int:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO boundary_reviews (
            start_opinion_id,
            opinion_ids,
            decisions,
            status,
            error
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            start_opinion_id,

            json.dumps(
                opinion_ids,
                ensure_ascii=False
            ),

            json.dumps(
                decisions,
                ensure_ascii=False
            ),

            "VALIDATED",

            None,
        )
    )

    review_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return int(review_id)


# =================================================
# GET OPINION BATCH
# =================================================

def get_opinion_batch(
    database_path: Path,
    start_opinion_id: int,
    batch_size: int
) -> list[dict]:

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            opinion_id,
            submitter,
            text,
            source_paragraphs,
            status,
            error
        FROM opinions
        WHERE opinion_id >= ?
        ORDER BY opinion_id
        LIMIT ?
        """,
        (
            start_opinion_id,
            batch_size
        )
    ).fetchall()

    connection.close()

    opinions = []

    for row in rows:

        try:

            source_paragraphs = json.loads(
                row["source_paragraphs"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_paragraphs = []

        opinions.append(
            {
                "opinion_id": row["opinion_id"],
                "submitter": row["submitter"],
                "text": row["text"],
                "source_paragraphs": source_paragraphs,
                "status": row["status"],
                "error": row["error"],
            }
        )

    return opinions


# =================================================
# GET BOUNDARY CONTEXT BATCH
# =================================================

def get_boundary_context_batch(
    database_path: Path,
    start_opinion_id: int,
    batch_size: int,
    context_size: int = 1
) -> dict:
    """
    Return target opinions and surrounding context.
    """

    if batch_size < 1:

        return {
            "previous_context": [],
            "target_opinions": [],
            "next_context": []
        }

    if context_size < 0:
        context_size = 0

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    target_start = (
        start_opinion_id
    )

    target_end = (
        start_opinion_id
        + batch_size
        - 1
    )

    # =================================================
    # PREVIOUS CONTEXT
    # =================================================

    previous_rows = []

    if context_size > 0:

        previous_rows = cursor.execute(
            """
            SELECT
                opinion_id,
                submitter,
                text,
                source_paragraphs,
                status,
                error
            FROM opinions
            WHERE opinion_id < ?
            ORDER BY opinion_id DESC
            LIMIT ?
            """,
            (
                target_start,
                context_size
            )
        ).fetchall()

        previous_rows.reverse()

    # =================================================
    # TARGET OPINIONS
    # =================================================

    target_rows = cursor.execute(
        """
        SELECT
            opinion_id,
            submitter,
            text,
            source_paragraphs,
            status,
            error
        FROM opinions
        WHERE opinion_id BETWEEN ? AND ?
        ORDER BY opinion_id
        """,
        (
            target_start,
            target_end
        )
    ).fetchall()

    # =================================================
    # NEXT CONTEXT
    # =================================================

    next_rows = []

    if context_size > 0:

        next_rows = cursor.execute(
            """
            SELECT
                opinion_id,
                submitter,
                text,
                source_paragraphs,
                status,
                error
            FROM opinions
            WHERE opinion_id > ?
            ORDER BY opinion_id
            LIMIT ?
            """,
            (
                target_end,
                context_size
            )
        ).fetchall()

    connection.close()

    # =================================================
    # ROW -> DICT
    # =================================================

    def row_to_dict(
        row: sqlite3.Row
    ) -> dict:

        try:

            source_paragraphs = json.loads(
                row["source_paragraphs"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_paragraphs = []

        return {
            "opinion_id": row["opinion_id"],
            "submitter": row["submitter"],
            "text": row["text"],
            "source_paragraphs": source_paragraphs,
            "status": row["status"],
            "error": row["error"],
        }

    previous_context = [
        row_to_dict(row)
        for row in previous_rows
    ]

    target_opinions = [
        row_to_dict(row)
        for row in target_rows
    ]

    next_context = [
        row_to_dict(row)
        for row in next_rows
    ]

    return {
        "previous_context": previous_context,
        "target_opinions": target_opinions,
        "next_context": next_context,
    }


# =================================================
# CLEAR BOUNDARY QUEUE
# =================================================

def clear_boundary_queue(
    database_path: Path
) -> None:
    """
    Delete all boundary batch records.

    Used when the opinions dataset is freshly
    re-ingested.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM boundary_batches"
    )

    connection.commit()

    connection.close()


# =================================================
# BUILD BOUNDARY QUEUE
# =================================================

def build_boundary_queue(
    database_path: Path,
    batch_size: int = 10
) -> int:
    """
    Build sequential boundary-review batches from
    the current opinions table.

    Example with batch_size=10:

        1-10
        11-20
        21-30
        ...
    """

    if type(batch_size) is not int:

        raise TypeError(
            "batch_size must be an integer."
        )

    if batch_size < 1:

        raise ValueError(
            "batch_size must be >= 1."
        )

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    # -------------------------------------------------
    # GET TOTAL OPINIONS
    # -------------------------------------------------

    total_opinions = cursor.execute(
        """
        SELECT COUNT(*)
        FROM opinions
        """
    ).fetchone()[0]

    # -------------------------------------------------
    # NO OPINIONS
    # -------------------------------------------------

    if total_opinions == 0:

        connection.close()

        return 0

    # -------------------------------------------------
    # GET MAX OPINION ID
    # -------------------------------------------------

    max_opinion_id = cursor.execute(
        """
        SELECT MAX(opinion_id)
        FROM opinions
        """
    ).fetchone()[0]

    # -------------------------------------------------
    # CREATE BATCHES
    # -------------------------------------------------

    batch_count = 0

    start_opinion_id = 1

    while (
        start_opinion_id
        <= max_opinion_id
    ):

        end_opinion_id = min(
            start_opinion_id
            + batch_size
            - 1,
            max_opinion_id
        )

        actual_batch_size = (
            end_opinion_id
            - start_opinion_id
            + 1
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO
            boundary_batches (
                start_opinion_id,
                end_opinion_id,
                batch_size,
                status,
                review_id,
                error
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                start_opinion_id,
                end_opinion_id,
                actual_batch_size,
                BOUNDARY_PENDING,
                None,
                None,
            )
        )

        if cursor.rowcount > 0:
            batch_count += 1

        start_opinion_id = (
            end_opinion_id + 1
        )

    connection.commit()

    connection.close()

    return batch_count


# =================================================
# CLAIM NEXT BOUNDARY BATCH
# =================================================

def claim_next_boundary_batch(
    database_path: Path
) -> dict | None:
    """
    Atomically claim the next PENDING
    boundary-review batch.

    PENDING -> PROCESSING
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        row = cursor.execute(
            """
            SELECT
                batch_id,
                start_opinion_id,
                end_opinion_id,
                batch_size,
                status,
                review_id,
                error
            FROM boundary_batches
            WHERE status = ?
            ORDER BY batch_id
            LIMIT 1
            """,
            (
                BOUNDARY_PENDING,
            )
        ).fetchone()

        if row is None:

            connection.commit()

            return None

        batch_id = row[
            "batch_id"
        ]

        cursor.execute(
            """
            UPDATE boundary_batches
            SET
                status = ?,
                error = NULL,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE batch_id = ?
              AND status = ?
            """,
            (
                BOUNDARY_PROCESSING,
                batch_id,
                BOUNDARY_PENDING,
            )
        )

        connection.commit()

        return {
            "batch_id": row[
                "batch_id"
            ],

            "start_opinion_id": row[
                "start_opinion_id"
            ],

            "end_opinion_id": row[
                "end_opinion_id"
            ],

            "batch_size": row[
                "batch_size"
            ],

            "status": (
                BOUNDARY_PROCESSING
            ),

            "review_id": row[
                "review_id"
            ],

            "error": None,
        }

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()

# =================================================
# GET BOUNDARY BATCH BY ID
# =================================================

def get_boundary_batch_by_id(
    database_path: Path,
    batch_id: int
) -> dict | None:
    """
    Get one boundary batch from the queue.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT
            batch_id,
            start_opinion_id,
            end_opinion_id,
            batch_size,
            status,
            review_id,
            error
        FROM boundary_batches
        WHERE batch_id = ?
        """,
        (
            batch_id,
        )
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "batch_id": row["batch_id"],
        "start_opinion_id": row["start_opinion_id"],
        "end_opinion_id": row["end_opinion_id"],
        "batch_size": row["batch_size"],
        "status": row["status"],
        "review_id": row["review_id"],
        "error": row["error"],
    }


# =================================================
# COMPLETE BOUNDARY BATCH
# =================================================

def complete_boundary_batch(
    database_path: Path,
    batch_id: int,
    review_id: int
) -> None:
    """
    Mark a boundary batch as REVIEWED.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_batches
        SET
            status = ?,
            review_id = ?,
            error = NULL,
            updated_at =
                CURRENT_TIMESTAMP
        WHERE batch_id = ?
        """,
        (
            BOUNDARY_REVIEWED,
            review_id,
            batch_id,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# FAIL BOUNDARY BATCH
# =================================================

def fail_boundary_batch(
    database_path: Path,
    batch_id: int,
    error: str
) -> None:
    """
    Mark a boundary batch as FAILED.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_batches
        SET
            status = ?,
            error = ?,
            updated_at =
                CURRENT_TIMESTAMP
        WHERE batch_id = ?
        """,
        (
            BOUNDARY_FAILED,
            error,
            batch_id,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# RESET PROCESSING BOUNDARY BATCHES
# =================================================

def reset_processing_boundary_batches(
    database_path: Path
) -> None:
    """
    Reset interrupted boundary jobs.

    PROCESSING -> PENDING
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_batches
        SET
            status = ?,
            error = NULL,
            updated_at =
                CURRENT_TIMESTAMP
        WHERE status = ?
        """,
        (
            BOUNDARY_PENDING,
            BOUNDARY_PROCESSING,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# GET BOUNDARY QUEUE STATUS
# =================================================

def get_boundary_queue_status(
    database_path: Path
) -> dict:
    """
    Return boundary queue progress.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    total = cursor.execute(
        """
        SELECT COUNT(*)
        FROM boundary_batches
        """
    ).fetchone()[0]

    pending = cursor.execute(
        """
        SELECT COUNT(*)
        FROM boundary_batches
        WHERE status = ?
        """,
        (
            BOUNDARY_PENDING,
        )
    ).fetchone()[0]

    processing = cursor.execute(
        """
        SELECT COUNT(*)
        FROM boundary_batches
        WHERE status = ?
        """,
        (
            BOUNDARY_PROCESSING,
        )
    ).fetchone()[0]

    reviewed = cursor.execute(
        """
        SELECT COUNT(*)
        FROM boundary_batches
        WHERE status = ?
        """,
        (
            BOUNDARY_REVIEWED,
        )
    ).fetchone()[0]

    failed = cursor.execute(
        """
        SELECT COUNT(*)
        FROM boundary_batches
        WHERE status = ?
        """,
        (
            BOUNDARY_FAILED,
        )
    ).fetchone()[0]

    connection.close()

    return {
        "total_batches": total,
        "pending": pending,
        "processing": processing,
        "reviewed": reviewed,
        "failed": failed,
    }

# =================================================
# RESET ENTIRE BOUNDARY QUEUE
# =================================================

def reset_boundary_queue(
    database_path: Path
) -> None:
    """
    Reset all boundary batches to PENDING.

    This is useful before starting a fresh
    boundary-review run.

    It does not delete the opinions.
    It does not delete boundary review history.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_batches
        SET
            status = ?,
            review_id = NULL,
            error = NULL,
            updated_at =
                CURRENT_TIMESTAMP
        """,
        (
            BOUNDARY_PENDING,
        )
    )

    connection.commit()

    connection.close()

# =================================================
# CLEAR BOUNDARY REVIEWS
# =================================================

def clear_boundary_reviews(
    database_path: Path
) -> None:
    """
    Delete boundary-review history.

    Use this only when resetting a test dataset
    before a fresh real boundary-review run.

    This does NOT delete opinions.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM boundary_reviews"
    )

    connection.commit()

    connection.close()

    # =================================================
# MATERIALIZATION TABLES
# =================================================

def initialize_materialization_tables(
    database_path: Path
) -> None:
    """
    Create tables required for the safe
    boundary-review materialization stage.

    These tables are separate from the original
    opinions and boundary-review tables.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    # -------------------------------------------------
    # FINAL OPINIONS
    # -------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS final_opinions (
            final_opinion_id INTEGER PRIMARY KEY,
            submitter TEXT,
            text TEXT NOT NULL,
            source_opinion_ids TEXT NOT NULL,
            source_paragraphs TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # -------------------------------------------------
    # BOUNDARY APPLICATION RUNS
    # -------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS boundary_application_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            total_source_opinions INTEGER NOT NULL,
            total_boundary_reviews INTEGER NOT NULL,
            total_final_opinions INTEGER,
            error TEXT,
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """
    )

    connection.commit()

    connection.close()


# =================================================
# GET ALL OPINIONS
# =================================================

def get_all_opinions(
    database_path: Path
) -> list[dict]:
    """
    Return all original opinions in ID order.

    The original opinions are never modified by
    this read operation.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            opinion_id,
            submitter,
            text,
            source_paragraphs,
            status,
            error
        FROM opinions
        ORDER BY opinion_id
        """
    ).fetchall()

    connection.close()

    opinions = []

    for row in rows:

        try:

            source_paragraphs = json.loads(
                row["source_paragraphs"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_paragraphs = []

        opinions.append(
            {
                "opinion_id": row["opinion_id"],
                "submitter": row["submitter"],
                "text": row["text"],
                "source_paragraphs": source_paragraphs,
                "status": row["status"],
                "error": row["error"],
            }
        )

    return opinions


# =================================================
# GET ALL BOUNDARY REVIEWS
# =================================================

def get_all_boundary_reviews(
    database_path: Path
) -> list[dict]:
    """
    Return all saved boundary reviews.

    The review decisions are decoded from JSON.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            review_id,
            start_opinion_id,
            opinion_ids,
            decisions,
            status,
            error,
            created_at
        FROM boundary_reviews
        ORDER BY start_opinion_id
        """
    ).fetchall()

    connection.close()

    reviews = []

    for row in rows:

        try:

            opinion_ids = json.loads(
                row["opinion_ids"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            opinion_ids = []

        try:

            decisions = json.loads(
                row["decisions"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            decisions = []

        reviews.append(
            {
                "review_id": row["review_id"],
                "start_opinion_id": (
                    row["start_opinion_id"]
                ),
                "opinion_ids": opinion_ids,
                "decisions": decisions,
                "status": row["status"],
                "error": row["error"],
                "created_at": row["created_at"],
            }
        )

    return reviews


# =================================================
# CLEAR FINAL OPINIONS
# =================================================

def clear_final_opinions(
    database_path: Path
) -> None:
    """
    Delete previously materialized final opinions.

    This does NOT modify:
        opinions
        boundary_reviews
        boundary_batches
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM final_opinions"
    )

    connection.commit()

    connection.close()


# =================================================
# SAVE FINAL OPINION
# =================================================

def save_final_opinion(
    database_path: Path,
    final_opinion_id: int,
    submitter: str | None,
    text: str,
    source_opinion_ids: list[int],
    source_paragraphs: list[int],
    status: str,
) -> None:
    """
    Save one materialized final opinion.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO final_opinions (
            final_opinion_id,
            submitter,
            text,
            source_opinion_ids,
            source_paragraphs,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            final_opinion_id,
            submitter,
            text,

            json.dumps(
                source_opinion_ids,
                ensure_ascii=False
            ),

            json.dumps(
                source_paragraphs,
                ensure_ascii=False
            ),

            status,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# CREATE APPLICATION RUN
# =================================================

def create_boundary_application_run(
    database_path: Path,
    total_source_opinions: int,
    total_boundary_reviews: int,
) -> int:
    """
    Create a new boundary-materialization run.

    The run starts in PREVIEW status.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO boundary_application_runs (
            status,
            total_source_opinions,
            total_boundary_reviews,
            total_final_opinions,
            error
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "PREVIEW",
            total_source_opinions,
            total_boundary_reviews,
            None,
            None,
        )
    )

    run_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return int(run_id)


# =================================================
# COMPLETE APPLICATION RUN
# =================================================

def complete_boundary_application_run(
    database_path: Path,
    run_id: int,
    total_final_opinions: int,
) -> None:
    """
    Mark a boundary-materialization run as completed.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_application_runs
        SET
            status = ?,
            total_final_opinions = ?,
            completed_at =
                CURRENT_TIMESTAMP
        WHERE run_id = ?
        """,
        (
            "APPLIED",
            total_final_opinions,
            run_id,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# FAIL APPLICATION RUN
# =================================================

def fail_boundary_application_run(
    database_path: Path,
    run_id: int,
    error: str,
) -> None:
    """
    Mark a boundary-materialization run as failed.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE boundary_application_runs
        SET
            status = ?,
            error = ?
        WHERE run_id = ?
        """,
        (
            "FAILED",
            error,
            run_id,
        )
    )

    connection.commit()

    connection.close()


# =================================================
# GET FINAL OPINIONS
# =================================================

def get_final_opinions(
    database_path: Path
) -> list[dict]:
    """
    Return materialized final opinions.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            final_opinion_id,
            submitter,
            text,
            source_opinion_ids,
            source_paragraphs,
            status,
            created_at
        FROM final_opinions
        ORDER BY final_opinion_id
        """
    ).fetchall()

    connection.close()

    results = []

    for row in rows:

        try:

            source_opinion_ids = json.loads(
                row["source_opinion_ids"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_opinion_ids = []

        try:

            source_paragraphs = json.loads(
                row["source_paragraphs"]
            )

        except (
            TypeError,
            json.JSONDecodeError
        ):

            source_paragraphs = []

        results.append(
            {
                "final_opinion_id": (
                    row[
                        "final_opinion_id"
                    ]
                ),

                "submitter": (
                    row["submitter"]
                ),

                "text": (
                    row["text"]
                ),

                "source_opinion_ids": (
                    source_opinion_ids
                ),

                "source_paragraphs": (
                    source_paragraphs
                ),

                "status": (
                    row["status"]
                ),

                "created_at": (
                    row["created_at"]
                ),
            }
        )

    return results

# =================================================
# RETRY FAILED BOUNDARY BATCH
# =================================================

def retry_failed_boundary_batch(
    database_path: Path,
    batch_id: int
) -> bool:
    """
    Move one FAILED boundary batch back to PENDING.

    This does not modify the opinions table.
    """

    connection = get_connection(
        database_path
    )

    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT
            status
        FROM boundary_batches
        WHERE batch_id = ?
        """,
        (
            batch_id,
        )
    ).fetchone()

    if row is None:

        connection.close()

        return False

    if row["status"] != BOUNDARY_FAILED:

        connection.close()

        return False

    cursor.execute(
        """
        UPDATE boundary_batches
        SET
            status = ?,
            error = NULL,
            review_id = NULL,
            updated_at =
                CURRENT_TIMESTAMP
        WHERE batch_id = ?
          AND status = ?
        """,
        (
            BOUNDARY_PENDING,
            batch_id,
            BOUNDARY_FAILED,
        )
    )

    connection.commit()

    changed = (
        cursor.rowcount == 1
    )

    connection.close()

    return changed