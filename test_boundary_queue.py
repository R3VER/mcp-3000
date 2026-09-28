from config import DATABASE_PATH

from storage import (
    build_boundary_queue,
    claim_next_boundary_batch,
    complete_boundary_batch,
    get_boundary_queue_status,
    initialize_database,
    reset_processing_boundary_batches,
)


# =================================================
# INITIALIZE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# BUILD QUEUE
# =================================================

created = build_boundary_queue(
    DATABASE_PATH,
    batch_size=10
)

print(
    "========== QUEUE CREATED =========="
)

print(
    f"New batches created: {created}"
)


# =================================================
# STATUS
# =================================================

status = get_boundary_queue_status(
    DATABASE_PATH
)

print()

print(
    "========== INITIAL STATUS =========="
)

print(status)


# =================================================
# CLAIM ONE BATCH
# =================================================

batch = claim_next_boundary_batch(
    DATABASE_PATH
)

print()

print(
    "========== CLAIMED BATCH =========="
)

print(batch)


# =================================================
# STATUS AFTER CLAIM
# =================================================

status = get_boundary_queue_status(
    DATABASE_PATH
)

print()

print(
    "========== STATUS AFTER CLAIM =========="
)

print(status)


# =================================================
# COMPLETE THE TEST BATCH
# =================================================

if batch is not None:

    complete_boundary_batch(
        DATABASE_PATH,
        batch_id=batch["batch_id"],
        review_id=9999
    )


# =================================================
# FINAL STATUS
# =================================================

status = get_boundary_queue_status(
    DATABASE_PATH
)

print()

print(
    "========== FINAL STATUS =========="
)

print(status)


# =================================================
# RESET PROCESSING TEST
# =================================================

reset_processing_boundary_batches(
    DATABASE_PATH
)

print()

print(
    "========== RESET COMPLETE =========="
)

print(
    get_boundary_queue_status(
        DATABASE_PATH
    )
)