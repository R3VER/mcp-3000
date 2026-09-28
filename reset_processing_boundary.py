from config import DATABASE_PATH

from storage import (
    initialize_database,
    reset_processing_boundary_batches,
    get_boundary_queue_status,
)


# =================================================
# INITIALIZE DATABASE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# RESET PROCESSING JOBS
# =================================================

reset_processing_boundary_batches(
    DATABASE_PATH
)


# =================================================
# SHOW STATUS
# =================================================

print(
    "========== PROCESSING BATCHES RESET =========="
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)