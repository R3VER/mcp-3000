from config import DATABASE_PATH

from boundary_applier import (
    build_materialization_plan,
    format_preview,
)

from storage import (
    get_boundary_queue_status,
    initialize_database,
)


# =================================================
# INITIALIZE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# SHOW QUEUE STATUS
# =================================================

print(
    "========== BOUNDARY QUEUE STATUS =========="
)

queue_status = get_boundary_queue_status(
    DATABASE_PATH
)

print(queue_status)

print()


# =================================================
# BUILD PREVIEW
# =================================================

print(
    "========== BUILDING MATERIALIZATION PREVIEW =========="
)

plan = build_materialization_plan(
    DATABASE_PATH
)

print()


# =================================================
# SHOW PREVIEW
# =================================================

print(
    format_preview(
        plan
    )
)