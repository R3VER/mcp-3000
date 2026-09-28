from config import DATABASE_PATH

from storage import (
    clear_boundary_reviews,
    get_boundary_queue_status,
    initialize_database,
    reset_boundary_queue,
)


# =================================================
# INITIALIZE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# REMOVE TEST REVIEWS
# =================================================

clear_boundary_reviews(
    DATABASE_PATH
)


# =================================================
# RESET ALL BOUNDARY BATCHES
# =================================================

reset_boundary_queue(
    DATABASE_PATH
)


# =================================================
# SHOW FINAL STATUS
# =================================================

print(
    "========== READY FOR REAL RUN =========="
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)