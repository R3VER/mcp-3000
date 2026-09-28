import sqlite3

from config import DATABASE_PATH


def main():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    print(
        "========== BOUNDARY REVIEWS =========="
    )

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
        ORDER BY review_id
        """
    ).fetchall()

    if not rows:

        print("No boundary reviews found.")

        connection.close()

        return

    for row in rows:

        print()
        print(
            f"Review ID: {row['review_id']}"
        )

        print(
            f"Start Opinion ID: "
            f"{row['start_opinion_id']}"
        )

        print(
            f"Opinion IDs: "
            f"{row['opinion_ids']}"
        )

        print(
            f"Status: {row['status']}"
        )

        print(
            f"Error: {row['error']}"
        )

        print(
            f"Created At: "
            f"{row['created_at']}"
        )

        print(
            f"Decisions: "
            f"{row['decisions']}"
        )

    print()
    print(
        "======================================="
    )

    # -------------------------------------------------
    # VERIFY OPINIONS WERE NOT MODIFIED
    # -------------------------------------------------

    print()
    print(
        "========== OPINION STATUS CHECK =========="
    )

    rows = cursor.execute(
        """
        SELECT
            opinion_id,
            submitter,
            status
        FROM opinions
        WHERE opinion_id BETWEEN 109 AND 114
        ORDER BY opinion_id
        """
    ).fetchall()

    for row in rows:

        print(
            f"Opinion {row['opinion_id']} | "
            f"Submitter: {row['submitter']} | "
            f"Status: {row['status']}"
        )

    connection.close()


if __name__ == "__main__":
    main()