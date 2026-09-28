# =================================================
# BOUNDARY PARSER
# =================================================

ALLOWED_ACTIONS = {
    "KEEP",
    "MERGE_WITH_PREVIOUS",
    "MERGE_WITH_NEXT",
    "DROP_ARTIFACT",
    "KEEP_EMPTY",
    "SPLIT_REVIEW",
}


def validate_boundary_decisions(
    decisions: list[dict],
    opinion_ids: list[int],
    previous_context_ids: list[int] | None = None,
    next_context_ids: list[int] | None = None,
) -> dict:
    """
    Validate LLM boundary-review decisions.

    opinion_ids:
        IDs of the TARGET opinions.

    previous_context_ids:
        IDs available immediately before the target batch.

    next_context_ids:
        IDs available immediately after the target batch.

    Context IDs may be used only as merge targets for
    the corresponding edge target.
    """

    # =================================================
    # BASIC VALIDATION
    # =================================================

    if not isinstance(
        decisions,
        list
    ):
        return {
            "valid": False,
            "error": (
                "decisions must be a list."
            )
        }

    if not isinstance(
        opinion_ids,
        list
    ):
        return {
            "valid": False,
            "error": (
                "opinion_ids must be a list."
            )
        }

    # =================================================
    # NORMALIZE TARGET IDS
    # =================================================

    try:

        expected_ids = [
            int(opinion_id)
            for opinion_id in opinion_ids
        ]

    except (
        TypeError,
        ValueError
    ):

        return {
            "valid": False,
            "error": (
                "opinion_ids must contain integers."
            )
        }

    # =================================================
    # DUPLICATE TARGET IDS
    # =================================================

    if len(expected_ids) != len(
        set(expected_ids)
    ):

        return {
            "valid": False,
            "error": (
                "opinion_ids contains duplicates."
            )
        }

    # =================================================
    # CONTEXT IDS
    # =================================================

    if previous_context_ids is None:
        previous_context_ids = []

    if next_context_ids is None:
        next_context_ids = []

    if not isinstance(
        previous_context_ids,
        list
    ):

        return {
            "valid": False,
            "error": (
                "previous_context_ids "
                "must be a list."
            )
        }

    if not isinstance(
        next_context_ids,
        list
    ):

        return {
            "valid": False,
            "error": (
                "next_context_ids "
                "must be a list."
            )
        }

    try:

        normalized_previous_ids = [
            int(opinion_id)
            for opinion_id
            in previous_context_ids
        ]

        normalized_next_ids = [
            int(opinion_id)
            for opinion_id
            in next_context_ids
        ]

    except (
        TypeError,
        ValueError
    ):

        return {
            "valid": False,
            "error": (
                "Context IDs must contain integers."
            )
        }

    # =================================================
    # EMPTY BATCH
    # =================================================

    if not expected_ids:

        if decisions:

            return {
                "valid": False,
                "error": (
                    "No opinion IDs were supplied, "
                    "but decisions were returned."
                )
            }

        return {
            "valid": True,
            "decisions": []
        }

    # =================================================
    # DECISION COUNT
    # =================================================

    if len(decisions) != len(
        expected_ids
    ):

        return {
            "valid": False,
            "error": (
                "Number of decisions does not "
                "match number of supplied opinions."
            ),

            "expected_count": (
                len(expected_ids)
            ),

            "actual_count": (
                len(decisions)
            ),
        }

    expected_set = set(
        expected_ids
    )

    # =================================================
    # TRACK SEEN IDS
    # =================================================

    seen_ids = set()

    normalized_decisions = []

    # =================================================
    # VALIDATE EACH DECISION
    # =================================================

    for decision in decisions:

        # -------------------------------------------------
        # OBJECT CHECK
        # -------------------------------------------------

        if not isinstance(
            decision,
            dict
        ):

            return {
                "valid": False,
                "error": (
                    "Each decision must "
                    "be an object."
                )
            }

        # -------------------------------------------------
        # OPINION ID
        # -------------------------------------------------

        if "opinion_id" not in decision:

            return {
                "valid": False,
                "error": (
                    "Decision is missing "
                    "opinion_id."
                )
            }

        try:

            opinion_id = int(
                decision[
                    "opinion_id"
                ]
            )

        except (
            TypeError,
            ValueError
        ):

            return {
                "valid": False,
                "error": (
                    "opinion_id "
                    "must be an integer."
                )
            }

        # -------------------------------------------------
        # MUST BE A TARGET
        # -------------------------------------------------

        if opinion_id not in expected_set:

            return {
                "valid": False,
                "error": (
                    f"Unexpected opinion_id: "
                    f"{opinion_id}"
                )
            }

        # -------------------------------------------------
        # DUPLICATE DECISION
        # -------------------------------------------------

        if opinion_id in seen_ids:

            return {
                "valid": False,
                "error": (
                    f"Duplicate decision for "
                    f"opinion_id {opinion_id}."
                )
            }

        seen_ids.add(
            opinion_id
        )

        # -------------------------------------------------
        # ACTION
        # -------------------------------------------------

        action = decision.get(
            "action"
        )

        if action not in ALLOWED_ACTIONS:

            return {
                "valid": False,
                "error": (
                    f"Invalid action for "
                    f"opinion_id {opinion_id}: "
                    f"{action}"
                ),

                "allowed_actions": sorted(
                    ALLOWED_ACTIONS
                ),
            }

        # -------------------------------------------------
        # TARGET OPINION ID
        # -------------------------------------------------

        target = decision.get(
            "target_opinion_id"
        )

        # =================================================
        # MERGE WITH PREVIOUS
        # =================================================

        if action == "MERGE_WITH_PREVIOUS":

            if target is None:

                return {
                    "valid": False,
                    "error": (
                        f"opinion_id {opinion_id} "
                        "requires target_opinion_id "
                        "for MERGE_WITH_PREVIOUS."
                    )
                }

            try:

                target = int(
                    target
                )

            except (
                TypeError,
                ValueError
            ):

                return {
                    "valid": False,
                    "error": (
                        "target_opinion_id "
                        "must be an integer."
                    )
                }

            current_index = (
                expected_ids.index(
                    opinion_id
                )
            )

            # -------------------------------------------------
            # FIRST TARGET
            # -------------------------------------------------

            if current_index == 0:

                # The previous target can be
                # inside the target batch OR
                # in the previous context.

                if current_index == 0:

                    if normalized_previous_ids:

                        expected_previous = (
                            normalized_previous_ids[
                                -1
                            ]
                        )

                        if target != (
                            expected_previous
                        ):

                            return {
                                "valid": False,
                                "error": (
                                    f"opinion_id "
                                    f"{opinion_id} must merge "
                                    f"with previous context "
                                    f"opinion "
                                    f"{expected_previous}, "
                                    f"not {target}."
                                )
                            }

                    else:

                        return {
                            "valid": False,
                            "error": (
                                f"opinion_id "
                                f"{opinion_id} cannot "
                                "MERGE_WITH_PREVIOUS "
                                "because no previous "
                                "context was supplied."
                            )
                        }

            # -------------------------------------------------
            # INNER TARGET
            # -------------------------------------------------

            else:

                expected_previous = (
                    expected_ids[
                        current_index - 1
                    ]
                )

                if target != (
                    expected_previous
                ):

                    return {
                        "valid": False,
                        "error": (
                            f"opinion_id "
                            f"{opinion_id} must merge "
                            f"with previous opinion "
                            f"{expected_previous}, "
                            f"not {target}."
                        )
                    }

        # =================================================
        # MERGE WITH NEXT
        # =================================================

        elif action == "MERGE_WITH_NEXT":

            if target is None:

                return {
                    "valid": False,
                    "error": (
                        f"opinion_id {opinion_id} "
                        "requires target_opinion_id "
                        "for MERGE_WITH_NEXT."
                    )
                }

            try:

                target = int(
                    target
                )

            except (
                TypeError,
                ValueError
            ):

                return {
                    "valid": False,
                    "error": (
                        "target_opinion_id "
                        "must be an integer."
                    )
                }

            current_index = (
                expected_ids.index(
                    opinion_id
                )
            )

            # -------------------------------------------------
            # LAST TARGET
            # -------------------------------------------------

            if current_index == (
                len(expected_ids) - 1
            ):

                if normalized_next_ids:

                    expected_next = (
                        normalized_next_ids[
                            0
                        ]
                    )

                    if target != (
                        expected_next
                    ):

                        return {
                            "valid": False,
                            "error": (
                                f"opinion_id "
                                f"{opinion_id} must merge "
                                f"with next context "
                                f"opinion "
                                f"{expected_next}, "
                                f"not {target}."
                            )
                        }

                else:

                    return {
                        "valid": False,
                        "error": (
                            f"opinion_id "
                            f"{opinion_id} cannot "
                            "MERGE_WITH_NEXT because "
                            "no next context was supplied."
                        )
                    }

            # -------------------------------------------------
            # INNER TARGET
            # -------------------------------------------------

            else:

                expected_next = (
                    expected_ids[
                        current_index + 1
                    ]
                )

                if target != (
                    expected_next
                ):

                    return {
                        "valid": False,
                        "error": (
                            f"opinion_id "
                            f"{opinion_id} must merge "
                            f"with next opinion "
                            f"{expected_next}, "
                            f"not {target}."
                        )
                    }

        # =================================================
        # NON-MERGE ACTION
        # =================================================

        else:

            if target is not None:

                return {
                    "valid": False,
                    "error": (
                        f"opinion_id "
                        f"{opinion_id} must have "
                        "target_opinion_id = null "
                        f"for action {action}."
                    )
                }

        # =================================================
        # NORMALIZED DECISION
        # =================================================

        normalized_decisions.append(
            {
                "opinion_id": opinion_id,

                "action": action,

                "target_opinion_id": target,

                "reason": str(
                    decision.get(
                        "reason",
                        ""
                    )
                ).strip(),
            }
        )

    # =================================================
    # MISSING DECISIONS
    # =================================================

    missing_ids = (
        expected_set
        - seen_ids
    )

    if missing_ids:

        return {
            "valid": False,
            "error": (
                "Some supplied opinions "
                "have no decision."
            ),
            "missing_opinion_ids": sorted(
                missing_ids
            ),
        }

    # =================================================
    # SUCCESS
    # =================================================

    return {
        "valid": True,
        "decisions": normalized_decisions
    }