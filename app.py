from config import INPUT_DIR, DATABASE_PATH

from extractor import extract_text
from splitter import split_opinions

from storage import (
    initialize_database,
    save_opinion,
    clear_opinions,
)

from model import (
    Opinion,
    PENDING,
    NO_CONTENT,
)


def main():

    # =====================================================
    # 1. Find DOCX input
    # =====================================================

    docx_files = list(
        INPUT_DIR.glob("*.docx")
    )

    if not docx_files:

        print(
            "No DOCX file found in data/input/"
        )

        return

    input_file = docx_files[0]

    print(
        f"Reading: {input_file.name}"
    )

    # =====================================================
    # 2. Extract paragraphs from DOCX
    # =====================================================

    paragraphs = extract_text(
        input_file
    )

    print(
        f"Total extracted paragraphs: "
        f"{len(paragraphs)}"
    )

    # =====================================================
    # 3. Split document into candidate opinions
    # =====================================================

    raw_opinions = split_opinions(
        paragraphs
    )

    print(
        f"Total opinions detected: "
        f"{len(raw_opinions)}"
    )

    # =====================================================
    # 4. Initialize database
    # =====================================================

    initialize_database(
        DATABASE_PATH
    )

    # =====================================================
    # 5. Clear old ingestion
    #
    # IMPORTANT:
    # This is only for creating a fresh dataset.
    # Do NOT run this during actual processing of jobs.
    # =====================================================

    clear_opinions(
        DATABASE_PATH
    )

    # =====================================================
    # 6. Save opinions
    # =====================================================

    pending_count = 0
    no_content_count = 0

    for opinion_id, raw in enumerate(
        raw_opinions,
        start=1
    ):

        # Join all text paragraphs belonging
        # to this candidate opinion.
        text = " ".join(
            raw["paragraphs"]
        ).strip()

        # Preserve submitter name.
        submitter = (
            raw["submitter"]
            if raw["submitter"]
            else None
        )

        # Preserve original DOCX paragraph indexes.
        source_paragraphs = (
            raw.get(
                "source_paragraphs",
                []
            )
        )

        # Determine initial status.
        if text:

            status = PENDING

            pending_count += 1

        else:

            status = NO_CONTENT

            no_content_count += 1

        # Build Opinion object.
        opinion = Opinion(
            opinion_id=opinion_id,
            text=text,
            submitter=submitter,
            source_paragraphs=source_paragraphs,
            status=status,
            error=None,
        )

        # Save to SQLite.
        save_opinion(
            DATABASE_PATH,
            opinion
        )

    # =====================================================
    # 7. Print ingestion summary
    # =====================================================

    print()

    print(
        "========== INGESTION SUMMARY =========="
    )

    print(
        f"Total opinions: "
        f"{len(raw_opinions)}"
    )

    print(
        f"PENDING: "
        f"{pending_count}"
    )

    print(
        f"NO_CONTENT: "
        f"{no_content_count}"
    )

    print(
        f"Database: "
        f"{DATABASE_PATH}"
    )


if __name__ == "__main__":
    main()