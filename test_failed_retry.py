from config import DATABASE_PATH

from storage import (
    claim_next_boundary_batch,
    fail_boundary_batch,
    get_boundary_batch_by_id,
    get_boundary_queue_status,
    initialize_database,
    reset_boundary_queue,
    retry_failed_boundary_batch,
)


# =================================================
# INITIALIZE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# CLEAN QUEUE
# =================================================

reset_boundary_queue(
    DATABASE_PATH
)


print(
    "========== INITIAL STATUS =========="
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)


# =================================================
# CLAIM BATCH
# =================================================

batch = claim_next_boundary_batch(
    DATABASE_PATH
)

print()
print(
    "========== CLAIM =========="
)

print(batch)


# =================================================
# FAIL BATCH
# =================================================

fail_boundary_batch(
    DATABASE_PATH,
    batch["batch_id"],
    "TEST ERROR: simulated LLM failure."
)

print()
print(
    "========== AFTER FAILURE =========="
)

print(
    get_boundary_batch_by_id(
        DATABASE_PATH,
        batch["batch_id"]
    )
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)


# =================================================
# RETRY FAILED BATCH
# =================================================

success = retry_failed_boundary_batch(
    DATABASE_PATH,
    batch["batch_id"]
)

print()
print(
    "========== RETRY =========="
)

print(
    "Retry successful:",
    success
)

print(
    get_boundary_batch_by_id(
        DATABASE_PATH,
        batch["batch_id"]
    )
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)
