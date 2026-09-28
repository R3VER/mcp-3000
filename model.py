from dataclasses import dataclass


PENDING = "PENDING"
PROCESSING = "PROCESSING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
NO_CONTENT = "NO_CONTENT"


ALLOWED_STATUSES = {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED,
    NO_CONTENT,
}


@dataclass
class Opinion:
    opinion_id: int
    text: str
    submitter: str | None = None

    # Original paragraph numbers from the DOCX
    source_paragraphs: list[int] | None = None

    status: str = PENDING
    error: str | None = None