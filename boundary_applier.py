import json
from pathlib import Path

from config import DATABASE_PATH

from storage import (
    get_all_boundary_reviews,
    get_all_opinions,
)


# =================================================
# ALLOWED ACTIONS
# =================================================

ALLOWED_ACTIONS = {
    "KEEP",
    "MERGE_WITH_PREVIOUS",
    "MERGE_WITH_NEXT",
    "DROP_ARTIFACT",
    "KEEP_EMPTY",
    "SPLIT_REVIEW",
}


# =================================================
# UNION-FIND
# =================================================

class UnionFind:
    """
    Small union-find structure used to resolve
    chains of merged opinions.

    Example:

        10 MERGE_WITH_NEXT 11
        11 MERGE_WITH_NEXT 12

    becomes:

        [10, 11, 12]
    """

    def __init__(
        self,
        values: list[int]
    ) -> None:

        self.parent = {
            value: value
            for value in values
        }

    def find(
        self,
        value: int
    ) -> int:

        if self.parent[value] != value:

            self.parent[value] = self.find(
                self.parent[value]
            )

        return self.parent[value]

    def union(
        self,
        left: int,
        right: int
    ) -> None:

        left_root = self.find(
            left
        )

        right_root = self.find(
            right
        )

        if left_root != right_root:

            # Keep the smaller opinion ID
            # as the root for deterministic
            # output.

            if left_root < right_root:

                self.parent[
                    right_root
                ] = left_root

            else:

                self.parent[
                    left_root
                ] = right_root


# =================================================
# LOAD OPINION MAP
# =================================================

def build_opinion_map(
    opinions: list[dict]
) -> dict[int, dict]:
    """
    Convert the list of opinions into:

        {
            opinion_id: opinion
        }
    """

    opinion_map = {}

    for opinion in opinions:

        opinion_id = int(
            opinion["opinion_id"]
        )

        if opinion_id in opinion_map:

            raise ValueError(
                f"Duplicate opinion_id found: "
                f"{opinion_id}"
            )

        opinion_map[
            opinion_id
        ] = opinion

    return opinion_map


# =================================================
# BUILD DECISION MAP
# =================================================

def build_decision_map(
    reviews: list[dict]
) -> tuple[
    dict[int, dict],
    dict
]:
    """
    Flatten all boundary-review decisions.

    Every original opinion must have exactly one
    decision.

    Returns:

        decision_map
        diagnostics
    """

    decision_map = {}

    duplicate_ids = []

    unknown_ids = []

    invalid_actions = []

    for review in reviews:

        if review.get("status") != "VALIDATED":

            continue

        decisions = review.get(
            "decisions",
            []
        )

        for decision in decisions:

            try:

                opinion_id = int(
                    decision[
                        "opinion_id"
                    ]
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                invalid_actions.append(
                    {
                        "decision": decision,
                        "error": (
                            "Invalid opinion_id."
                        )
                    }
                )

                continue

            if opinion_id in decision_map:

                duplicate_ids.append(
                    opinion_id
                )

                continue

            action = decision.get(
                "action"
            )

            if action not in (
                ALLOWED_ACTIONS
            ):

                invalid_actions.append(
                    {
                        "opinion_id": opinion_id,
                        "action": action,
                    }
                )

                continue

            decision_map[
                opinion_id
            ] = {
                "opinion_id": opinion_id,

                "action": action,

                "target_opinion_id": (
                    decision.get(
                        "target_opinion_id"
                    )
                ),

                "reason": str(
                    decision.get(
                        "reason",
                        ""
                    )
                ).strip(),

                "review_id": (
                    review[
                        "review_id"
                    ]
                ),
            }

    diagnostics = {
        "duplicate_decision_ids": sorted(
            set(duplicate_ids)
        ),

        "unknown_decision_ids": sorted(
            set(unknown_ids)
        ),

        "invalid_actions": invalid_actions,
    }

    return (
        decision_map,
        diagnostics
    )


# =================================================
# VERIFY REVIEW COVERAGE
# =================================================

def verify_review_coverage(
    opinion_ids: list[int],
    decision_map: dict[int, dict]
) -> dict:
    """
    Make sure every original opinion has exactly
    one boundary decision.

    This prevents partial application.
    """

    source_ids = set(
        opinion_ids
    )

    decided_ids = set(
        decision_map.keys()
    )

    missing_ids = (
        source_ids
        - decided_ids
    )

    extra_ids = (
        decided_ids
        - source_ids
    )

    return {
        "valid": (
            not missing_ids
            and not extra_ids
        ),

        "missing_opinion_ids": sorted(
            missing_ids
        ),

        "extra_opinion_ids": sorted(
            extra_ids
        ),
    }


# =================================================
# GET MERGE EDGES
# =================================================

def build_merge_edges(
    decision_map: dict[int, dict],
    opinion_ids: set[int]
) -> tuple[
    list[tuple[int, int]],
    list[dict]
]:
    """
    Build merge relationships.

    Returns:

        edges
        conflicts
    """

    edges = []

    conflicts = []

    for opinion_id, decision in (
        decision_map.items()
    ):

        action = decision[
            "action"
        ]

        target = decision.get(
            "target_opinion_id"
        )

        if action not in {
            "MERGE_WITH_PREVIOUS",
            "MERGE_WITH_NEXT",
        }:

            continue

        if target is None:

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "error": (
                        "Merge decision has "
                        "no target."
                    )
                }
            )

            continue

        try:

            target = int(
                target
            )

        except (
            TypeError,
            ValueError
        ):

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "error": (
                        "Merge target is "
                        "not an integer."
                    )
                }
            )

            continue

        # -------------------------------------------------
        # TARGET MUST EXIST
        # -------------------------------------------------

        if target not in opinion_ids:

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "target_opinion_id": target,
                    "error": (
                        "Merge target does not "
                        "exist in original opinions."
                    )
                }
            )

            continue

        # -------------------------------------------------
        # TARGET MUST BE ADJACENT
        # -------------------------------------------------

        if abs(
            opinion_id - target
        ) != 1:

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "target_opinion_id": target,
                    "error": (
                        "Merge target is not "
                        "immediately adjacent."
                    )
                }
            )

            continue

        edges.append(
            (
                opinion_id,
                target
            )
        )

    return (
        edges,
        conflicts
    )


# =================================================
# CHECK MERGE CONFLICTS
# =================================================

def find_merge_conflicts(
    decision_map: dict[int, dict],
    edges: list[tuple[int, int]]
) -> list[dict]:
    """
    Detect decisions that cannot safely be merged.

    Examples:

        DROP_ARTIFACT + merge into that opinion
        SPLIT_REVIEW + merge into that opinion
    """

    conflicts = []

    merged_ids = set()

    for left, right in edges:

        merged_ids.add(left)
        merged_ids.add(right)

    for opinion_id in sorted(
        merged_ids
    ):

        decision = decision_map.get(
            opinion_id
        )

        if decision is None:

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "error": (
                        "Opinion participates in "
                        "a merge but has no decision."
                    )
                }
            )

            continue

        action = decision[
            "action"
        ]

        if action == "DROP_ARTIFACT":

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "error": (
                        "DROP_ARTIFACT opinion "
                        "cannot participate "
                        "in a merge."
                    )
                }
            )

        elif action == "SPLIT_REVIEW":

            conflicts.append(
                {
                    "opinion_id": opinion_id,
                    "error": (
                        "SPLIT_REVIEW opinion "
                        "cannot participate "
                        "in a merge."
                    )
                }
            )

    return conflicts


# =================================================
# FIND GROUPS
# =================================================

def build_merge_groups(
    opinion_ids: list[int],
    edges: list[tuple[int, int]]
) -> list[list[int]]:
    """
    Resolve all merge relationships.

    Example:

        5 ↔ 6
        6 ↔ 7

    becomes:

        [5, 6, 7]
    """

    union_find = UnionFind(
        opinion_ids
    )

    for left, right in edges:

        union_find.union(
            left,
            right
        )

    groups = {}

    for opinion_id in opinion_ids:

        root = union_find.find(
            opinion_id
        )

        groups.setdefault(
            root,
            []
        ).append(
            opinion_id
        )

    result = []

    for group in groups.values():

        group.sort()

        result.append(
            group
        )

    result.sort(
        key=lambda group: group[0]
    )

    return result


# =================================================
# COMBINE SOURCE PARAGRAPHS
# =================================================

def combine_source_paragraphs(
    group: list[int],
    opinion_map: dict[int, dict]
) -> list[int]:
    """
    Combine source paragraph IDs while preserving
    original order and removing duplicates.
    """

    result = []

    seen = set()

    for opinion_id in group:

        paragraphs = opinion_map[
            opinion_id
        ].get(
            "source_paragraphs",
            []
        )

        for paragraph in paragraphs:

            try:

                paragraph = int(
                    paragraph
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if paragraph not in seen:

                seen.add(
                    paragraph
                )

                result.append(
                    paragraph
                )

    return result


# =================================================
# COMBINE TEXT
# =================================================

def combine_text(
    group: list[int],
    opinion_map: dict[int, dict]
) -> str:
    """
    Combine the text of merged source opinions.
    """

    pieces = []

    for opinion_id in group:

        text = str(
            opinion_map[
                opinion_id
            ].get(
                "text",
                ""
            )
        ).strip()

        if text:

            pieces.append(
                text
            )

    return "\n\n".join(
        pieces
    ).strip()


# =================================================
# RESOLVE SUBMITTER
# =================================================

def resolve_submitter(
    group: list[int],
    opinion_map: dict[int, dict]
) -> tuple[
    str | None,
    list[dict]
]:
    """
    Resolve the submitter for a merged group.

    Normally merged candidates should have the same
    submitter.

    Different non-empty submitter names are treated
    as a safety conflict.
    """

    submitters = []

    for opinion_id in group:

        submitter = opinion_map[
            opinion_id
        ].get(
            "submitter"
        )

        if submitter is None:

            continue

        submitter = str(
            submitter
        ).strip()

        if not submitter:

            continue

        if submitter not in submitters:

            submitters.append(
                submitter
            )

    conflicts = []

    if len(submitters) > 1:

        conflicts.append(
            {
                "source_opinion_ids": group,
                "submitters": submitters,
                "error": (
                    "Merged opinions have "
                    "different submitter names."
                )
            }
        )

    if submitters:

        return (
            submitters[0],
            conflicts
        )

    return (
        None,
        conflicts
    )


# =================================================
# BUILD FINAL OPINION
# =================================================

def build_final_opinion(
    final_opinion_id: int,
    group: list[int],
    opinion_map: dict[int, dict],
    decision_map: dict[int, dict]
) -> tuple[
    dict,
    list[dict]
]:
    """
    Construct one final opinion from one merge group.
    """

    submitter, submitter_conflicts = (
        resolve_submitter(
            group,
            opinion_map
        )
    )

    text = combine_text(
        group,
        opinion_map
    )

    source_paragraphs = (
        combine_source_paragraphs(
            group,
            opinion_map
        )
    )

    actions = {
        decision_map[
            opinion_id
        ]["action"]
        for opinion_id in group
    }

    status = "READY"

    if "KEEP_EMPTY" in actions:

        status = "KEEP_EMPTY"

    final_opinion = {
        "final_opinion_id": (
            final_opinion_id
        ),

        "submitter": submitter,

        "text": text,

        "source_opinion_ids": (
            group
        ),

        "source_paragraphs": (
            source_paragraphs
        ),

        "status": status,
    }

    return (
        final_opinion,
        submitter_conflicts
    )


# =================================================
# BUILD MATERIALIZATION PLAN
# =================================================

def build_materialization_plan(
    database_path: Path
) -> dict:
    """
    Build the complete corrected-opinion plan
    without writing anything to the database.

    This is the dry-run stage.

    The function refuses to build a final plan when
    boundary reviews are incomplete or conflicting.
    """

    # =================================================
    # LOAD SOURCE OPINIONS
    # =================================================

    opinions = get_all_opinions(
        database_path
    )

    if not opinions:

        return {
            "valid": False,
            "ready": False,
            "error": (
                "No opinions found."
            )
        }

    opinion_map = build_opinion_map(
        opinions
    )

    opinion_ids = sorted(
        opinion_map.keys()
    )

    # =================================================
    # LOAD REVIEWS
    # =================================================

    reviews = get_all_boundary_reviews(
        database_path
    )

    if not reviews:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "No boundary reviews "
                "have been saved."
            ),

            "source_opinions": len(
                opinions
            ),

            "boundary_reviews": 0,
        }

    # =================================================
    # BUILD DECISION MAP
    # =================================================

    decision_map, diagnostics = (
        build_decision_map(
            reviews
        )
    )

    if diagnostics[
        "duplicate_decision_ids"
    ]:

        return {
            "valid": False,
            "ready": False,
            "error": (
                "Some opinions have "
                "multiple boundary decisions."
            ),

            "duplicate_decision_ids": (
                diagnostics[
                    "duplicate_decision_ids"
                ]
            ),
        }

    if diagnostics[
        "invalid_actions"
    ]:

        return {
            "valid": False,
            "ready": False,
            "error": (
                "Invalid boundary actions "
                "were found."
            ),

            "invalid_actions": (
                diagnostics[
                    "invalid_actions"
                ]
            ),
        }

    # =================================================
    # VERIFY COVERAGE
    # =================================================

    coverage = verify_review_coverage(
        opinion_ids,
        decision_map
    )

    if not coverage["valid"]:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "Boundary review coverage "
                "is incomplete."
            ),

            "source_opinions": len(
                opinions
            ),

            "boundary_reviews": len(
                reviews
            ),

            "missing_opinion_ids": (
                coverage[
                    "missing_opinion_ids"
                ]
            ),

            "extra_opinion_ids": (
                coverage[
                    "extra_opinion_ids"
                ]
            ),
        }

    # =================================================
    # FIND SPLIT REVIEWS
    # =================================================

    split_review_ids = [
        opinion_id
        for opinion_id, decision
        in decision_map.items()
        if decision[
            "action"
        ] == "SPLIT_REVIEW"
    ]

    if split_review_ids:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "Some opinions require "
                "SPLIT_REVIEW before "
                "materialization."
            ),

            "split_review_ids": (
                sorted(
                    split_review_ids
                )
            ),
        }

    # =================================================
    # BUILD MERGE EDGES
    # =================================================

    edges, edge_conflicts = (
        build_merge_edges(
            decision_map,
            set(opinion_ids)
        )
    )

    if edge_conflicts:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "Invalid merge relationships "
                "were detected."
            ),

            "merge_conflicts": (
                edge_conflicts
            ),
        }

    # =================================================
    # CHECK MERGE CONFLICTS
    # =================================================

    merge_conflicts = (
        find_merge_conflicts(
            decision_map,
            edges
        )
    )

    if merge_conflicts:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "Conflicting DROP_ARTIFACT "
                "or SPLIT_REVIEW decisions "
                "participate in merges."
            ),

            "merge_conflicts": (
                merge_conflicts
            ),
        }

    # =================================================
    # BUILD MERGE GROUPS
    # =================================================

    groups = build_merge_groups(
        opinion_ids,
        edges
    )

    # =================================================
    # DROP ARTIFACTS
    # =================================================

    dropped_ids = {
        opinion_id
        for opinion_id, decision
        in decision_map.items()
        if decision[
            "action"
        ] == "DROP_ARTIFACT"
    }

    # =================================================
    # REMOVE DROP ARTIFACTS FROM GROUPS
    # =================================================

    materialization_groups = []

    for group in groups:

        cleaned_group = [
            opinion_id
            for opinion_id in group
            if opinion_id
            not in dropped_ids
        ]

        if cleaned_group:

            materialization_groups.append(
                cleaned_group
            )

    # =================================================
    # BUILD FINAL OPINIONS
    # =================================================

    final_opinions = []

    submitter_conflicts = []

    final_opinion_id = 1

    for group in (
        materialization_groups
    ):

        final_opinion, conflicts = (
            build_final_opinion(
                final_opinion_id=(
                    final_opinion_id
                ),

                group=group,

                opinion_map=(
                    opinion_map
                ),

                decision_map=(
                    decision_map
                ),
            )
        )

        final_opinions.append(
            final_opinion
        )

        if conflicts:

            submitter_conflicts.extend(
                conflicts
            )

        final_opinion_id += 1

    # =================================================
    # SUBMITTER CONFLICTS
    # =================================================

    if submitter_conflicts:

        return {
            "valid": False,
            "ready": False,

            "error": (
                "A merge group contains "
                "different submitter names."
            ),

            "submitter_conflicts": (
                submitter_conflicts
            ),
        }

    # =================================================
    # COUNTS
    # =================================================

    merged_groups = [
        group
        for group
        in materialization_groups
        if len(group) > 1
    ]

    keep_count = sum(
        1
        for decision
        in decision_map.values()
        if decision[
            "action"
        ] == "KEEP"
    )

    keep_empty_count = sum(
        1
        for decision
        in decision_map.values()
        if decision[
            "action"
        ] == "KEEP_EMPTY"
    )

    # =================================================
    # FINAL PLAN
    # =================================================

    return {
        "valid": True,
        "ready": True,

        "source_opinions": len(
            opinions
        ),

        "boundary_reviews": len(
            reviews
        ),

        "final_opinions": len(
            final_opinions
        ),

        "keep_decisions": keep_count,

        "keep_empty_decisions": (
            keep_empty_count
        ),

        "dropped_artifacts": len(
            dropped_ids
        ),

        "merged_groups": len(
            merged_groups
        ),

        "merged_source_opinions": sum(
            len(group)
            for group
            in merged_groups
        ),

        "merge_groups": (
            merged_groups
        ),

        "final_records": (
            final_opinions
        ),
    }


# =================================================
# FORMAT PREVIEW
# =================================================

def format_preview(
    plan: dict
) -> str:
    """
    Convert a materialization plan into a readable
    console preview.
    """

    if not plan.get(
        "valid",
        False
    ):

        lines = [
            "========== MATERIALIZATION BLOCKED ==========",
            "",
            f"Reason: {plan.get('error')}",
            "",
        ]

        for key in [
            "missing_opinion_ids",
            "extra_opinion_ids",
            "duplicate_decision_ids",
            "split_review_ids",
            "merge_conflicts",
            "submitter_conflicts",
        ]:

            if key in plan:

                lines.append(
                    f"{key}: "
                    f"{json.dumps(plan[key], ensure_ascii=False)}"
                )

        lines.append(
            "============================================="
        )

        return "\n".join(
            lines
        )

    # =================================================
    # SUCCESS PREVIEW
    # =================================================

    lines = [
        "========== MATERIALIZATION PREVIEW ==========",
        "",
        f"Source opinions: "
        f"{plan['source_opinions']}",

        f"Boundary reviews: "
        f"{plan['boundary_reviews']}",

        f"Final opinions: "
        f"{plan['final_opinions']}",

        f"KEEP decisions: "
        f"{plan['keep_decisions']}",

        f"KEEP_EMPTY decisions: "
        f"{plan['keep_empty_decisions']}",

        f"Dropped artifacts: "
        f"{plan['dropped_artifacts']}",

        f"Merged groups: "
        f"{plan['merged_groups']}",

        "",
        "Merge groups:",
    ]

    for group in plan[
        "merge_groups"
    ]:

        lines.append(
            "  "
            + " + ".join(
                str(value)
                for value in group
            )
        )

    lines.extend(
        [
            "",
            "First final records:",
        ]
    )

    for final_opinion in plan[
        "final_records"
    ][:10]:

        preview_text = (
            final_opinion[
                "text"
            ]
            .replace(
                "\n",
                " "
            )
            .strip()
        )

        if len(preview_text) > 160:

            preview_text = (
                preview_text[
                    :160
                ]
                + "..."
            )

        lines.append(
            (
                f"  FINAL {final_opinion['final_opinion_id']} | "
                f"SOURCE {final_opinion['source_opinion_ids']} | "
                f"SUBMITTER {final_opinion['submitter']} | "
                f"{preview_text}"
            )
        )

    lines.extend(
        [
            "",
            "============================================="
        ]
    )

    return "\n".join(
        lines
    )


# =================================================
# MAIN
# =================================================

if __name__ == "__main__":

    plan = build_materialization_plan(
        DATABASE_PATH
    )

    print(
        format_preview(
            plan
        )
    )