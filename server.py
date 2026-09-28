import json
from pathlib import Path

from fastmcp import FastMCP

from config import DATABASE_PATH

from boundary_reviewer import (
    build_boundary_review_prompt
)

from boundary_parser import (
    validate_boundary_decisions
)

from evaluation_prompt import (
    build_evaluation_prompt
)

from result_parser import (
    parse_evaluation_response
)

from storage import (
    claim_next_boundary_batch,
    claim_next_pending_opinion,
    complete_boundary_batch,
    fail_boundary_batch,
    get_boundary_batch_by_id,
    get_boundary_context_batch,
    get_boundary_queue_status,
    initialize_database,
    reset_processing_boundary_batches,
    retry_failed_boundary_batch,
    save_boundary_review,
    save_evaluation,
    update_opinion_status,
)


# =================================================
# SERVER
# =================================================

mcp = FastMCP(
    "Pollution Evaluation Server"
)


# =================================================
# PATHS
# =================================================

BASE_DIR = Path(
    __file__
).resolve().parent

RULES_PATH = BASE_DIR / "rules.json"


# =================================================
# LOAD RULES
# =================================================

with open(
    RULES_PATH,
    "r",
    encoding="utf-8"
) as file:

    rules = json.load(file)


# =================================================
# INITIALIZE DATABASE
# =================================================

initialize_database(
    DATABASE_PATH
)


# =================================================
# INTERNAL SCORE VALIDATION
# =================================================

def validate_score_value(
    score: int
) -> bool:

    valid_scores = {
        int(value)
        for value in rules[
            "scoring_scale"
        ].keys()
    }

    return (
        type(score) is int
        and score in valid_scores
    )


def validate_all_scores(
    scores: dict[str, int]
) -> dict:

    expected_criteria = {
        criterion["number"]
        for criterion in rules[
            "evaluation_parameters"
        ]
    }

    try:

        normalized_scores = {
            int(number): score
            for number, score in scores.items()
        }

    except (
        TypeError,
        ValueError
    ):

        return {
            "valid": False,
            "error": (
                "Criterion numbers "
                "must be integers."
            ),
            "missing_criteria": [],
            "extra_criteria": [],
            "invalid_scores": {}
        }

    provided_criteria = set(
        normalized_scores.keys()
    )

    missing = (
        expected_criteria
        - provided_criteria
    )

    extra = (
        provided_criteria
        - expected_criteria
    )

    invalid_scores = {
        number: score
        for number, score
        in normalized_scores.items()
        if not validate_score_value(
            score
        )
    }

    return {
        "valid": (
            not missing
            and not extra
            and not invalid_scores
        ),
        "missing_criteria": sorted(
            missing
        ),
        "extra_criteria": sorted(
            extra
        ),
        "invalid_scores": invalid_scores
    }


# =================================================
# INTERNAL WEIGHTED SCORE CALCULATION
# =================================================

def calculate_weighted_score_value(
    scores: dict[int, int]
) -> dict:

    total_score = 0

    breakdown = {}

    max_score = max(
        int(value)
        for value in rules[
            "scoring_scale"
        ].keys()
    )

    for criterion in rules[
        "evaluation_parameters"
    ]:

        number = criterion[
            "number"
        ]

        weight = criterion[
            "weight"
        ]

        score = scores[
            number
        ]

        weighted_score = (
            score
            / max_score
            * weight
        )

        total_score += (
            weighted_score
        )

        breakdown[number] = {
            "score": score,
            "weight": weight,
            "weighted_score": round(
                weighted_score,
                2
            )
        }

    return {
        "total_score": round(
            total_score,
            2
        ),

        "maximum_score": sum(
            criterion["weight"]
            for criterion in rules[
                "evaluation_parameters"
            ]
        ),

        "breakdown": breakdown
    }


# =================================================
# MCP TOOL: GET RULES
# =================================================

@mcp.tool
def get_rules() -> dict:
    """
    Return the complete evaluation framework.
    """

    return rules


# =================================================
# MCP TOOL: GET BOUNDARY BATCH
# =================================================

@mcp.tool
def get_boundary_batch(
    start_opinion_id: int,
    batch_size: int = 10,
    context_size: int = 1
) -> dict:
    """
    Manually retrieve a boundary-review batch.

    This does NOT claim the batch from the queue.

    It is useful for inspection and testing.
    """

    # -------------------------------------------------
    # VALIDATE START ID
    # -------------------------------------------------

    if type(start_opinion_id) is not int:

        return {
            "valid": False,
            "error": (
                "start_opinion_id "
                "must be an integer."
            )
        }

    # -------------------------------------------------
    # VALIDATE BATCH SIZE
    # -------------------------------------------------

    if type(batch_size) is not int:

        return {
            "valid": False,
            "error": (
                "batch_size "
                "must be an integer."
            )
        }

    # -------------------------------------------------
    # VALIDATE CONTEXT SIZE
    # -------------------------------------------------

    if type(context_size) is not int:

        return {
            "valid": False,
            "error": (
                "context_size "
                "must be an integer."
            )
        }

    # -------------------------------------------------
    # VALUE CHECKS
    # -------------------------------------------------

    if start_opinion_id < 1:

        return {
            "valid": False,
            "error": (
                "start_opinion_id "
                "must be >= 1."
            )
        }

    if not 1 <= batch_size <= 25:

        return {
            "valid": False,
            "error": (
                "batch_size "
                "must be between 1 and 25."
            )
        }

    if not 0 <= context_size <= 3:

        return {
            "valid": False,
            "error": (
                "context_size "
                "must be between 0 and 3."
            )
        }

    # -------------------------------------------------
    # GET DATA
    # -------------------------------------------------

    boundary_data = (
        get_boundary_context_batch(
            database_path=DATABASE_PATH,
            start_opinion_id=start_opinion_id,
            batch_size=batch_size,
            context_size=context_size,
        )
    )

    previous_context = (
        boundary_data[
            "previous_context"
        ]
    )

    target_opinions = (
        boundary_data[
            "target_opinions"
        ]
    )

    next_context = (
        boundary_data[
            "next_context"
        ]
    )

    # -------------------------------------------------
    # NO TARGETS
    # -------------------------------------------------

    if not target_opinions:

        return {
            "valid": True,
            "available": False,

            "start_opinion_id": (
                start_opinion_id
            ),

            "batch_size": 0,

            "context_size": (
                context_size
            ),

            "previous_context": (
                previous_context
            ),

            "opinions": [],

            "target_opinions": [],

            "next_context": (
                next_context
            ),

            "boundary_review_prompt": ""
        }

    # -------------------------------------------------
    # BUILD REVIEW PROMPT
    # -------------------------------------------------

    boundary_review_prompt = (
        build_boundary_review_prompt(
            boundary_data
        )
    )

    # -------------------------------------------------
    # RETURN DATA
    # -------------------------------------------------

    return {
        "valid": True,
        "available": True,

        "start_opinion_id": (
            start_opinion_id
        ),

        "batch_size": len(
            target_opinions
        ),

        "context_size": (
            context_size
        ),

        "previous_context": (
            previous_context
        ),

        # Backward-compatible field
        "opinions": (
            target_opinions
        ),

        "target_opinions": (
            target_opinions
        ),

        "next_context": (
            next_context
        ),

        "boundary_review_prompt": (
            boundary_review_prompt
        )
    }


# =================================================
# MCP TOOL: GET NEXT BOUNDARY BATCH
# =================================================

@mcp.tool
def get_next_boundary_batch(
    context_size: int = 1
) -> dict:
    """
    Claim the next PENDING boundary batch.

    PENDING -> PROCESSING

    Returns the batch plus surrounding context.
    """

    # -------------------------------------------------
    # VALIDATE CONTEXT SIZE
    # -------------------------------------------------

    if type(context_size) is not int:

        return {
            "valid": False,
            "error": (
                "context_size "
                "must be an integer."
            )
        }

    if not 0 <= context_size <= 3:

        return {
            "valid": False,
            "error": (
                "context_size "
                "must be between 0 and 3."
            )
        }

    # -------------------------------------------------
    # CLAIM NEXT BATCH
    # -------------------------------------------------

    batch = (
        claim_next_boundary_batch(
            DATABASE_PATH
        )
    )

    # -------------------------------------------------
    # NO BATCHES
    # -------------------------------------------------

    if batch is None:

        queue_status = (
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )

        return {
            "valid": True,
            "available": False,
            "message": (
                "No PENDING boundary "
                "batches remain."
            ),
            "queue": queue_status
        }

    # -------------------------------------------------
    # GET CONTEXT + TARGETS
    # -------------------------------------------------

    boundary_data = (
        get_boundary_context_batch(
            database_path=DATABASE_PATH,

            start_opinion_id=(
                batch[
                    "start_opinion_id"
                ]
            ),

            batch_size=(
                batch[
                    "batch_size"
                ]
            ),

            context_size=context_size,
        )
    )

    # -------------------------------------------------
    # BUILD PROMPT
    # -------------------------------------------------

    boundary_review_prompt = (
        build_boundary_review_prompt(
            boundary_data
        )
    )

    # -------------------------------------------------
    # RETURN
    # -------------------------------------------------

    return {
        "valid": True,

        "available": True,

        "batch_id": (
            batch[
                "batch_id"
            ]
        ),

        "start_opinion_id": (
            batch[
                "start_opinion_id"
            ]
        ),

        "end_opinion_id": (
            batch[
                "end_opinion_id"
            ]
        ),

        "batch_size": (
            batch[
                "batch_size"
            ]
        ),

        "status": (
            batch[
                "status"
            ]
        ),

        "context_size": (
            context_size
        ),

        "previous_context": (
            boundary_data[
                "previous_context"
            ]
        ),

        "target_opinions": (
            boundary_data[
                "target_opinions"
            ]
        ),

        "next_context": (
            boundary_data[
                "next_context"
            ]
        ),

        "boundary_review_prompt": (
            boundary_review_prompt
        )
    }


# =================================================
# MCP TOOL: GET BOUNDARY QUEUE STATUS
# =================================================

@mcp.tool
def get_boundary_queue_status_tool() -> dict:
    """
    Return current boundary-review queue progress.
    """

    return get_boundary_queue_status(
        DATABASE_PATH
    )


# =================================================
# MCP TOOL: FAIL BOUNDARY BATCH
# =================================================

@mcp.tool
def fail_boundary_batch_tool(
    batch_id: int,
    error: str
) -> dict:
    """
    Mark a PROCESSING boundary batch as FAILED.

    This does not modify the opinions table.
    """

    # -------------------------------------------------
    # VALIDATE BATCH ID
    # -------------------------------------------------

    if type(batch_id) is not int:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be an integer."
            )
        }

    if batch_id < 1:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be >= 1."
            )
        }

    # -------------------------------------------------
    # VALIDATE ERROR
    # -------------------------------------------------

    if not isinstance(
        error,
        str
    ):

        return {
            "valid": False,
            "error": (
                "error "
                "must be a string."
            )
        }

    error = error.strip()

    if not error:

        return {
            "valid": False,
            "error": (
                "error "
                "cannot be empty."
            )
        }

    # -------------------------------------------------
    # GET BATCH
    # -------------------------------------------------

    batch = get_boundary_batch_by_id(
        DATABASE_PATH,
        batch_id
    )

    if batch is None:

        return {
            "valid": False,
            "error": (
                f"Boundary batch "
                f"{batch_id} not found."
            )
        }

    # -------------------------------------------------
    # STATUS MUST BE PROCESSING
    # -------------------------------------------------

    if batch["status"] != "PROCESSING":

        return {
            "valid": False,
            "error": (
                f"Batch {batch_id} "
                f"is not PROCESSING. "
                f"Current status: "
                f"{batch['status']}."
            )
        }

    # -------------------------------------------------
    # MARK FAILED
    # -------------------------------------------------

    fail_boundary_batch(
        DATABASE_PATH,
        batch_id,
        error
    )

    # -------------------------------------------------
    # RETURN
    # -------------------------------------------------

    return {
        "valid": True,

        "batch_id": (
            batch_id
        ),

        "status": (
            "FAILED"
        ),

        "error": (
            error
        ),

        "queue": (
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )
    }

# =================================================
# MCP TOOL: RETRY FAILED BOUNDARY BATCH
# =================================================

@mcp.tool
def retry_failed_boundary_batch_tool(
    batch_id: int
) -> dict:
    """
    Move one FAILED boundary batch back to PENDING.

    This does not modify the opinions table.
    """

    # -------------------------------------------------
    # VALIDATE BATCH ID
    # -------------------------------------------------

    if type(batch_id) is not int:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be an integer."
            )
        }

    if batch_id < 1:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be >= 1."
            )
        }

    # -------------------------------------------------
    # GET BATCH
    # -------------------------------------------------

    batch = get_boundary_batch_by_id(
        DATABASE_PATH,
        batch_id
    )

    if batch is None:

        return {
            "valid": False,
            "error": (
                f"Boundary batch "
                f"{batch_id} not found."
            )
        }

    # -------------------------------------------------
    # MUST BE FAILED
    # -------------------------------------------------

    if batch["status"] != "FAILED":

        return {
            "valid": False,
            "error": (
                f"Batch {batch_id} "
                f"is not FAILED. "
                f"Current status: "
                f"{batch['status']}."
            )
        }

    # -------------------------------------------------
    # RETRY
    # -------------------------------------------------

    success = retry_failed_boundary_batch(
        DATABASE_PATH,
        batch_id
    )

    if not success:

        return {
            "valid": False,
            "error": (
                f"Failed to retry "
                f"boundary batch {batch_id}."
            )
        }

    # -------------------------------------------------
    # RETURN
    # -------------------------------------------------

    return {
        "valid": True,

        "batch_id": batch_id,

        "previous_status": "FAILED",

        "status": "PENDING",

        "message": (
            "Failed boundary batch "
            "was successfully returned "
            "to PENDING."
        ),

        "queue": (
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )
    }


# =================================================
# MCP TOOL: RESET PROCESSING BOUNDARY BATCHES
# =================================================

@mcp.tool
def reset_processing_boundary_batches_tool() -> dict:
    """
    Reset interrupted PROCESSING boundary batches
    back to PENDING.

    Useful after a server/client interruption.
    """

    reset_processing_boundary_batches(
        DATABASE_PATH
    )

    return {
        "valid": True,

        "message": (
            "All PROCESSING boundary batches "
            "were reset to PENDING."
        ),

        "queue": (
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )
    }


# =================================================
# MCP TOOL: VALIDATE BOUNDARY REVIEW
# =================================================

@mcp.tool
def validate_boundary_review(
    opinion_ids: list[int],
    decisions: list[dict],
    previous_context_ids: list[int] | None = None,
    next_context_ids: list[int] | None = None,
) -> dict:
    """
    Validate boundary-review decisions.

    This does NOT save anything.
    """

    return validate_boundary_decisions(
        decisions=decisions,

        opinion_ids=(
            opinion_ids
        ),

        previous_context_ids=(
            previous_context_ids or []
        ),

        next_context_ids=(
            next_context_ids or []
        ),
    )


# =================================================
# MCP TOOL: SUBMIT BOUNDARY REVIEW
# =================================================

@mcp.tool
def submit_boundary_review(
    batch_id: int,
    start_opinion_id: int,
    opinion_ids: list[int],
    decisions: list[dict]
) -> dict:
    """
    Validate and save a boundary review for
    a claimed processing batch.

    PROCESSING -> REVIEWED

    The original opinions table is NOT modified.
    """

    # =================================================
    # VALIDATE BATCH ID
    # =================================================

    if type(batch_id) is not int:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be an integer."
            )
        }

    if batch_id < 1:

        return {
            "valid": False,
            "error": (
                "batch_id "
                "must be >= 1."
            )
        }

    # =================================================
    # VALIDATE START OPINION ID
    # =================================================

    if type(start_opinion_id) is not int:

        return {
            "valid": False,
            "error": (
                "start_opinion_id "
                "must be an integer."
            )
        }

    if start_opinion_id < 1:

        return {
            "valid": False,
            "error": (
                "start_opinion_id "
                "must be >= 1."
            )
        }

    # =================================================
    # GET BATCH
    # =================================================

    batch = (
        get_boundary_batch_by_id(
            DATABASE_PATH,
            batch_id
        )
    )

    if batch is None:

        return {
            "valid": False,
            "error": (
                f"Boundary batch "
                f"{batch_id} not found."
            )
        }

    # =================================================
    # BATCH MUST BE PROCESSING
    # =================================================

    if batch["status"] != "PROCESSING":

        return {
            "valid": False,
            "error": (
                f"Batch {batch_id} "
                f"is not PROCESSING. "
                f"Current status: "
                f"{batch['status']}."
            )
        }

    # =================================================
    # START ID MUST MATCH BATCH
    # =================================================

    if start_opinion_id != (
        batch[
            "start_opinion_id"
        ]
    ):

        return {
            "valid": False,
            "error": (
                "start_opinion_id does not "
                "match the claimed boundary "
                "batch."
            )
        }

    # =================================================
    # VALIDATE OPINION IDS
    # =================================================

    if not isinstance(
        opinion_ids,
        list
    ):

        return {
            "valid": False,
            "error": (
                "opinion_ids "
                "must be a list."
            )
        }

    if not opinion_ids:

        return {
            "valid": False,
            "error": (
                "opinion_ids "
                "cannot be empty."
            )
        }

    try:

        normalized_opinion_ids = [
            int(opinion_id)
            for opinion_id
            in opinion_ids
        ]

    except (
        TypeError,
        ValueError
    ):

        return {
            "valid": False,
            "error": (
                "opinion_ids "
                "must contain integers."
            )
        }

    # =================================================
    # NO DUPLICATES
    # =================================================

    if len(
        normalized_opinion_ids
    ) != len(
        set(
            normalized_opinion_ids
        )
    ):

        return {
            "valid": False,
            "error": (
                "opinion_ids "
                "contains duplicates."
            )
        }

    # =================================================
    # EXPECTED BATCH RANGE
    # =================================================

    expected_opinion_ids = list(
        range(
            batch[
                "start_opinion_id"
            ],
            batch[
                "end_opinion_id"
            ] + 1
        )
    )

    if normalized_opinion_ids != (
        expected_opinion_ids
    ):

        return {
            "valid": False,

            "error": (
                "opinion_ids do not match "
                "the claimed boundary batch."
            ),

            "expected_opinion_ids": (
                expected_opinion_ids
            ),

            "received_opinion_ids": (
                normalized_opinion_ids
            )
        }

    # =================================================
    # GET REAL CONTEXT
    # =================================================

    boundary_data = (
        get_boundary_context_batch(
            database_path=DATABASE_PATH,

            start_opinion_id=(
                batch[
                    "start_opinion_id"
                ]
            ),

            batch_size=(
                batch[
                    "batch_size"
                ]
            ),

            context_size=1,
        )
    )

    previous_context_ids = [
        opinion[
            "opinion_id"
        ]
        for opinion
        in boundary_data[
            "previous_context"
        ]
    ]

    next_context_ids = [
        opinion[
            "opinion_id"
        ]
        for opinion
        in boundary_data[
            "next_context"
        ]
    ]

    # =================================================
    # VALIDATE DECISIONS
    # =================================================

    validation = (
        validate_boundary_decisions(
            decisions=decisions,

            opinion_ids=(
                normalized_opinion_ids
            ),

            previous_context_ids=(
                previous_context_ids
            ),

            next_context_ids=(
                next_context_ids
            ),
        )
    )

    if not validation["valid"]:

        return validation

    # =================================================
    # SAVE BOUNDARY REVIEW
    # =================================================

    review_id = save_boundary_review(
        database_path=DATABASE_PATH,

        start_opinion_id=(
            start_opinion_id
        ),

        opinion_ids=(
            normalized_opinion_ids
        ),

        decisions=(
            validation[
                "decisions"
            ]
        ),
    )

    # =================================================
    # MARK BATCH REVIEWED
    # =================================================

    complete_boundary_batch(
        database_path=DATABASE_PATH,

        batch_id=batch_id,

        review_id=review_id
    )

    # =================================================
    # GET QUEUE STATUS
    # =================================================

    queue_status = (
        get_boundary_queue_status(
            DATABASE_PATH
        )
    )

    # =================================================
    # RETURN
    # =================================================

    return {
        "valid": True,

        "saved": True,

        "review_id": (
            review_id
        ),

        "batch_id": (
            batch_id
        ),

        "start_opinion_id": (
            start_opinion_id
        ),

        "end_opinion_id": (
            batch[
                "end_opinion_id"
            ]
        ),

        "opinion_ids": (
            normalized_opinion_ids
        ),

        "decision_count": len(
            validation[
                "decisions"
            ]
        ),

        "previous_context_ids": (
            previous_context_ids
        ),

        "next_context_ids": (
            next_context_ids
        ),

        "status": (
            "REVIEWED"
        ),

        "queue": (
            queue_status
        ),

        "message": (
            "Boundary review validated, "
            "saved, and the batch was marked "
            "REVIEWED. The opinions table "
            "was not modified."
        )
    }


# =================================================
# MCP TOOL: GET NEXT OPINION
# =================================================

@mcp.tool
def get_next_opinion() -> dict:
    """
    Claim the next PENDING opinion.

    PENDING -> PROCESSING
    """

    opinion = (
        claim_next_pending_opinion(
            DATABASE_PATH
        )
    )

    if opinion is None:

        return {
            "available": False,

            "message": (
                "No PENDING opinions remain."
            )
        }

    prompt = build_evaluation_prompt(
        opinion
    )

    return {
        "available": True,

        "opinion_id": (
            opinion.opinion_id
        ),

        "submitter": (
            opinion.submitter
        ),

        "text": (
            opinion.text
        ),

        "source_paragraphs": (
            opinion.source_paragraphs
        ),

        "status": (
            opinion.status
        ),

        "evaluation_prompt": (
            prompt
        )
    }


# =================================================
# MCP TOOL: VALIDATE SCORES
# =================================================

@mcp.tool
def validate_scores(
    scores: dict[str, int]
) -> dict:
    """
    Validate all five criterion scores.
    """

    return validate_all_scores(
        scores
    )


# =================================================
# MCP TOOL: CALCULATE WEIGHTED SCORE
# =================================================

@mcp.tool
def calculate_weighted_score(
    scores: dict[str, int]
) -> dict:
    """
    Validate and calculate the weighted score.
    """

    validation = (
        validate_all_scores(
            scores
        )
    )

    if not validation["valid"]:

        return {
            "valid": False,

            "error": (
                "Cannot calculate: "
                "invalid scores."
            ),

            "validation": (
                validation
            )
        }

    normalized_scores = {
        int(number): score
        for number, score
        in scores.items()
    }

    result = (
        calculate_weighted_score_value(
            normalized_scores
        )
    )

    return {
        "valid": True,

        "total_score": (
            result[
                "total_score"
            ]
        ),

        "maximum_score": (
            result[
                "maximum_score"
            ]
        ),

        "breakdown": (
            result[
                "breakdown"
            ]
        )
    }


# =================================================
# MCP TOOL: SUBMIT EVALUATION
# =================================================

@mcp.tool
def submit_evaluation(
    opinion_id: int,
    evaluation: dict
) -> dict:
    """
    Validate, calculate, save and complete
    one opinion evaluation.
    """

    # =================================================
    # VALIDATE OPINION ID
    # =================================================

    if type(opinion_id) is not int:

        return {
            "valid": False,
            "error": (
                "opinion_id "
                "must be an integer."
            )
        }

    if opinion_id < 1:

        return {
            "valid": False,
            "error": (
                "opinion_id "
                "must be >= 1."
            )
        }

    # =================================================
    # VALIDATE EVALUATION OBJECT
    # =================================================

    if not isinstance(
        evaluation,
        dict
    ):

        update_opinion_status(
            DATABASE_PATH,
            opinion_id,
            "FAILED",
            "Evaluation must be a dictionary."
        )

        return {
            "valid": False,
            "opinion_id": opinion_id,
            "error": (
                "evaluation "
                "must be a dictionary."
            )
        }

    # =================================================
    # CONVERT TO JSON
    # =================================================

    response_text = json.dumps(
        evaluation,
        ensure_ascii=False
    )

    # =================================================
    # PARSE
    # =================================================

    parsed = (
        parse_evaluation_response(
            response_text
        )
    )

    if not parsed["valid"]:

        update_opinion_status(
            DATABASE_PATH,
            opinion_id,
            "FAILED",
            parsed.get(
                "error",
                "Invalid evaluation."
            )
        )

        return {
            "valid": False,
            "opinion_id": opinion_id,
            "error": parsed.get(
                "error",
                "Invalid evaluation."
            )
        }

    criterion_scores = (
        parsed[
            "criterion_scores"
        ]
    )

    reasoning = (
        parsed[
            "reasoning"
        ]
    )

    # =================================================
    # CALCULATE SCORE
    # =================================================

    score_result = (
        calculate_weighted_score(
            criterion_scores
        )
    )

    if not score_result["valid"]:

        update_opinion_status(
            DATABASE_PATH,
            opinion_id,
            "FAILED",
            "Score validation failed."
        )

        return {
            "valid": False,

            "opinion_id": (
                opinion_id
            ),

            "error": (
                "Score validation failed."
            ),

            "validation": (
                score_result
            )
        }

    total_score = (
        score_result[
            "total_score"
        ]
    )

    # =================================================
    # SAVE EVALUATION
    # =================================================

    save_evaluation(
        DATABASE_PATH,
        opinion_id,
        criterion_scores,
        total_score,
        reasoning
    )

    # =================================================
    # MARK COMPLETED
    # =================================================

    update_opinion_status(
        DATABASE_PATH,
        opinion_id,
        "COMPLETED",
        None
    )

    # =================================================
    # RETURN
    # =================================================

    return {
        "valid": True,

        "opinion_id": (
            opinion_id
        ),

        "status": (
            "COMPLETED"
        ),

        "total_score": (
            total_score
        ),

        "maximum_score": (
            score_result[
                "maximum_score"
            ]
        ),

        "breakdown": (
            score_result[
                "breakdown"
            ]
        )
    }


# =================================================
# START SERVER
# =================================================

if __name__ == "__main__":

    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000
    )