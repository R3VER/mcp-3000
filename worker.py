from config import DATABASE_PATH
from storage import (
    get_next_pending_opinion,
    update_opinion_status,
)
from model import PROCESSING


def process_one_opinion() -> None:

    # Get the oldest pending opinion
    opinion = get_next_pending_opinion(
        DATABASE_PATH
    )

    if opinion is None:

        print("No pending opinions found.")

        return

    print()
    print("========== NEXT OPINION ==========")
    print(f"Opinion ID: {opinion.opinion_id}")
    print(f"Submitter: {opinion.submitter}")
    print(f"Status: {opinion.status}")
    print()
    print("Text:")
    print(opinion.text[:1000])

    # Mark the job as processing
    update_opinion_status(
        DATABASE_PATH,
        opinion.opinion_id,
        PROCESSING
    )

    print()
    print(
        f"Opinion {opinion.opinion_id} "
        f"marked as PROCESSING."
    )


if __name__ == "__main__":

    process_one_opinion()