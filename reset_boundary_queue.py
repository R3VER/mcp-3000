from config import DATABASE_PATH

from storage import (
    initialize_database,
    reset_boundary_queue,
    get_boundary_queue_status,
)


initialize_database(
    DATABASE_PATH
)

reset_boundary_queue(
    DATABASE_PATH
)

print(
    "========== BOUNDARY QUEUE RESET =========="
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)