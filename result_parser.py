import json


REQUIRED_CRITERIA = {
    "1",
    "2",
    "3",
    "4",
    "5",
}


def parse_evaluation_response(
    response_text: str
) -> dict:

    # -----------------------------------------
    # Parse JSON
    # -----------------------------------------

    try:

        data = json.loads(
            response_text
        )

    except json.JSONDecodeError as error:

        return {
            "valid": False,
            "error": (
                f"Invalid JSON returned by model: "
                f"{error}"
            )
        }

    # -----------------------------------------
    # Check top-level structure
    # -----------------------------------------

    if not isinstance(data, dict):

        return {
            "valid": False,
            "error": "Response must be a JSON object."
        }

    if "criterion_scores" not in data:

        return {
            "valid": False,
            "error": "Missing criterion_scores."
        }

    if "reasoning" not in data:

        return {
            "valid": False,
            "error": "Missing reasoning."
        }

    criterion_scores = data[
        "criterion_scores"
    ]

    reasoning = data[
        "reasoning"
    ]

    # -----------------------------------------
    # Check criterion_scores
    # -----------------------------------------

    if not isinstance(
        criterion_scores,
        dict
    ):

        return {
            "valid": False,
            "error": (
                "criterion_scores must be "
                "a JSON object."
            )
        }

    actual_criteria = set(
        str(key)
        for key in criterion_scores.keys()
    )

    missing = (
        REQUIRED_CRITERIA
        - actual_criteria
    )

    extra = (
        actual_criteria
        - REQUIRED_CRITERIA
    )

    if missing:

        return {
            "valid": False,
            "error": "Missing criterion scores.",
            "missing_criteria": sorted(
                missing
            )
        }

    if extra:

        return {
            "valid": False,
            "error": "Unexpected criterion scores.",
            "extra_criteria": sorted(
                extra
            )
        }

    # -----------------------------------------
    # Validate score values
    # -----------------------------------------

    invalid_scores = {}

    normalized_scores = {}

    for criterion in REQUIRED_CRITERIA:

        value = criterion_scores.get(
            criterion
        )

        # JSON numbers may come through as
        # int or float. We only accept integers.
        if (
            type(value) is not int
            or value not in {1, 2, 3, 4, 5}
        ):

            invalid_scores[
                criterion
            ] = value

        else:

            normalized_scores[
                criterion
            ] = value

    if invalid_scores:

        return {
            "valid": False,
            "error": "Invalid criterion scores.",
            "invalid_scores": invalid_scores
        }

    # -----------------------------------------
    # Validate reasoning
    # -----------------------------------------

    if not isinstance(
        reasoning,
        dict
    ):

        return {
            "valid": False,
            "error": (
                "reasoning must be "
                "a JSON object."
            )
        }

    missing_reasoning = []

    for criterion in REQUIRED_CRITERIA:

        if criterion not in reasoning:

            missing_reasoning.append(
                criterion
            )

            continue

        if not isinstance(
            reasoning[criterion],
            str
        ):

            missing_reasoning.append(
                criterion
            )

    if missing_reasoning:

        return {
            "valid": False,
            "error": (
                "Missing or invalid reasoning."
            ),
            "missing_reasoning": sorted(
                missing_reasoning
            )
        }

    # -----------------------------------------
    # Return clean result
    # -----------------------------------------

    return {
        "valid": True,
        "criterion_scores": normalized_scores,
        "reasoning": {
            criterion: reasoning[
                criterion
            ].strip()
            for criterion in sorted(
                REQUIRED_CRITERIA
            )
        }
    }