# =================================================
# BOUNDARY REVIEWER
# =================================================

def build_boundary_review_prompt(
    boundary_data: dict
) -> str:
    """
    Build the prompt used by the LLM to review
    document boundaries.

    boundary_data contains:

        previous_context
        target_opinions
        next_context

    Only target_opinions are allowed to receive
    decisions.
    """

    previous_context = (
        boundary_data.get(
            "previous_context",
            []
        )
    )

    target_opinions = (
        boundary_data.get(
            "target_opinions",
            []
        )
    )

    next_context = (
        boundary_data.get(
            "next_context",
            []
        )
    )

    # =================================================
    # FORMAT ONE OPINION
    # =================================================

    def format_opinion(
        opinion: dict,
        label: str
    ) -> str:

        return f"""
----------------------------------------
{label}
OPINION ID: {opinion["opinion_id"]}
SUBMITTER: {opinion["submitter"]}
SOURCE PARAGRAPHS: {opinion.get("source_paragraphs", [])}

STATUS: {opinion.get("status")}

TEXT:
{opinion["text"]}
----------------------------------------
"""

    # =================================================
    # FORMAT PREVIOUS CONTEXT
    # =================================================

    previous_sections = []

    for opinion in previous_context:

        previous_sections.append(
            format_opinion(
                opinion,
                "PREVIOUS CONTEXT"
            )
        )

    previous_block = "\n".join(
        previous_sections
    )

    if not previous_block:

        previous_block = (
            "NO PREVIOUS CONTEXT AVAILABLE"
        )

    # =================================================
    # FORMAT TARGET OPINIONS
    # =================================================

    target_sections = []

    for opinion in target_opinions:

        target_sections.append(
            format_opinion(
                opinion,
                "TARGET OPINION"
            )
        )

    target_block = "\n".join(
        target_sections
    )

    if not target_block:

        target_block = (
            "NO TARGET OPINIONS AVAILABLE"
        )

    # =================================================
    # FORMAT NEXT CONTEXT
    # =================================================

    next_sections = []

    for opinion in next_context:

        next_sections.append(
            format_opinion(
                opinion,
                "NEXT CONTEXT"
            )
        )

    next_block = "\n".join(
        next_sections
    )

    if not next_block:

        next_block = (
            "NO NEXT CONTEXT AVAILABLE"
        )

    # =================================================
    # FINAL PROMPT
    # =================================================

    return f"""
You are reviewing the boundaries produced by a
document-splitting system.

Your job is NOT to evaluate or score the pollution
solution.

Your ONLY job is to determine whether the splitter
correctly separated the document into individual
submissions.

A single person may submit multiple separate opinions.

For example:

Austin Joseph
Opinion about transport

Austin Joseph
Opinion about biomass burning

Austin Joseph
Opinion about road dust

These may be THREE separate opinions even though
the submitter name is identical.

Do NOT merge opinions merely because the submitter
name is the same.

================================================
IMPORTANT BATCH STRUCTURE
================================================

The supplied material is divided into three groups:

1. PREVIOUS CONTEXT
2. TARGET OPINIONS
3. NEXT CONTEXT

PREVIOUS CONTEXT and NEXT CONTEXT exist only to help
you understand whether a TARGET OPINION continues
into another candidate.

You may READ and USE the context opinions.

However:

YOU MUST NEVER RETURN A DECISION FOR A CONTEXT OPINION.

Only TARGET OPINIONS may appear in the decisions array.

================================================
POSSIBLE ACTIONS
================================================

KEEP

The target candidate is a valid independent opinion.

MERGE_WITH_PREVIOUS

The target candidate is actually a continuation of
the immediately preceding opinion.

MERGE_WITH_NEXT

The target candidate is actually a continuation of
the immediately following opinion.

DROP_ARTIFACT

The target candidate is clearly a formatting artifact,
heading, label, date, attachment marker, diagram
fragment, or other non-submission text.

KEEP_EMPTY

The target candidate appears to be a genuine
submission heading, but no substantive opinion text
is available.

SPLIT_REVIEW

The target candidate itself appears to contain multiple
different submissions and requires another splitting pass.

================================================
IMPORTANT RULES
================================================

1. Do not merge solely because names are identical.

2. Do not invent missing text.

3. Do not invent submitter names.

4. Do not assume a short paragraph is an artifact
   just because it is short.

5. A very short legitimate submission must be preserved.

6. Continuation text can span multiple paragraphs.

7. A heading followed by another heading may indicate
   a blank submission, a formatting artifact, or a
   boundary problem.

8. Use surrounding context when deciding whether a
   target candidate is incomplete.

9. Preserve repeated submissions from the same person
   when their content is clearly separate.

10. Pay particular attention to:

    - incomplete sentences
    - abrupt topic changes
    - repeated submitter names
    - headings appearing inside content
    - dates
    - "Attachment"
    - section labels
    - diagram fragments
    - text that clearly continues the previous opinion

11. When MERGE_WITH_PREVIOUS is used, the immediate
    previous candidate must be the actual continuation.

12. When MERGE_WITH_NEXT is used, the immediate next
    candidate must be the actual continuation.

13. Do not make decisions about PREVIOUS CONTEXT or
    NEXT CONTEXT.

14. Every TARGET OPINION must receive exactly one
    decision.

15. The number of decisions must exactly equal the
    number of TARGET OPINIONS.

16. Base the decision only on the supplied document
    context.

================================================
PREVIOUS CONTEXT
================================================

{previous_block}

================================================
TARGET OPINIONS
================================================

{target_block}

================================================
NEXT CONTEXT
================================================

{next_block}

================================================
OUTPUT
================================================

Return ONLY valid JSON.

Use this exact structure:

{{
    "decisions": [
        {{
            "opinion_id": 0,
            "action": "KEEP",
            "target_opinion_id": null,
            "reason": ""
        }}
    ]
}}

Rules for output:

- Include every TARGET OPINION exactly once.
- Do not include PREVIOUS CONTEXT opinion IDs.
- Do not include NEXT CONTEXT opinion IDs.
- opinion_id must be the ID of a TARGET OPINION.
- For MERGE_WITH_PREVIOUS or MERGE_WITH_NEXT,
  target_opinion_id must identify the adjacent candidate.
- For KEEP, DROP_ARTIFACT, KEEP_EMPTY and
  SPLIT_REVIEW, target_opinion_id must be null.
- Keep the reason concise but explain the boundary
  decision.
"""