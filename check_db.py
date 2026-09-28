import sqlite3


connection = sqlite3.connect(
    "database/opinions.db"
)

cursor = connection.cursor()


statuses = [
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "NO_CONTENT",
]


print("========== DATABASE STATUS ==========")


for status in statuses:

    count = cursor.execute(
        """
        SELECT COUNT(*)
        FROM opinions
        WHERE status = ?
        """,
        (status,)
    ).fetchone()[0]

    print(f"{status}: {count}")


total = cursor.execute(
    """
    SELECT COUNT(*)
    FROM opinions
    """
).fetchone()[0]


print("-------------------------------------")
print(f"TOTAL: {total}")


connection.close()