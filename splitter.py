import re


STOP_PHRASES = {
    "attachment",
    "thank you",
    "solution ka pollution",
    "pollution ka solution",
    "read pdf",
    "plantation",
    "fey",
    "yes",
    "!",
    ".",
    "vehicle solution",
    "vehicle and vayu solution",
}


def get_segments(paragraph: dict) -> list[dict]:
    """
    Group consecutive Word runs with the same formatting.

    Whitespace-only runs are treated as separators.
    """

    runs = paragraph["runs"]

    segments = []

    current_type = None
    current_text = []

    pending_space = False

    for run in runs:

        raw_text = run["text"]

        if not raw_text:
            continue

        # Ignore runs containing only whitespace,
        # but remember that a space existed.
        if not raw_text.strip():
            pending_space = True
            continue

        text = raw_text.strip()

        run_type = (
            "bold"
            if run["bold"]
            else "normal"
        )

        # First segment
        if current_type is None:

            current_type = run_type
            current_text = [text]
            pending_space = False

            continue

        # Same formatting
        if run_type == current_type:

            if pending_space:
                current_text.append(" ")

            current_text.append(text)

        # Formatting changed
        else:

            combined_text = "".join(
                current_text
            ).strip()

            if combined_text:

                segments.append(
                    {
                        "type": current_type,
                        "text": combined_text
                    }
                )

            current_type = run_type
            current_text = [text]

        pending_space = False

    # Add final segment
    if current_text:

        combined_text = "".join(
            current_text
        ).strip()

        if combined_text:

            segments.append(
                {
                    "type": current_type,
                    "text": combined_text
                }
            )

    return segments


def is_damaged_name(
    paragraph: dict,
    segments: list[dict]
) -> bool:
    """
    Detect a name whose formatting is split into
    bold + tiny normal text.

    Example:

        Austin Josep
        h

    should still be treated as one submitter name.
    """

    if len(segments) != 2:
        return False

    bold_segments = [
        segment
        for segment in segments
        if segment["type"] == "bold"
    ]

    normal_segments = [
        segment
        for segment in segments
        if segment["type"] == "normal"
    ]

    if len(bold_segments) != 1:
        return False

    normal_text = "".join(
        segment["text"]
        for segment in normal_segments
    ).strip()

    paragraph_text = paragraph["text"].strip()

    word_count = len(
        paragraph_text.split()
    )

    return (
        word_count <= 6
        and len(normal_text) <= 2
    )


def is_date(text: str) -> bool:
    """
    Detect simple date-like paragraphs.

    Examples:
        29-08-2026
        29/08/2026
        29.08.2026
    """

    cleaned = (
        text
        .replace("-", "")
        .replace("/", "")
        .replace(".", "")
        .strip()
    )

    return cleaned.isdigit()


def is_url(text: str) -> bool:
    """
    Detect URLs.
    """

    text_lower = text.lower()

    return (
        "http://" in text_lower
        or "https://" in text_lower
        or "www." in text_lower
    )


def looks_like_plain_name(
    paragraphs: list[dict],
    position: int
) -> tuple[bool, int]:
    """
    Detect a submitter name that is NOT bold.

    This uses several signals:

    - short paragraph
    - alphabetic words
    - capitalization
    - all caps
    - long following paragraph

    Returns:

        (is_name, score)
    """

    paragraph = paragraphs[position]

    text = paragraph["text"].strip()

    if not text:
        return False, 0

    words = text.split()

    # Names in this document are generally short.
    if not 1 <= len(words) <= 5:
        return False, 0

    lower_text = text.lower()

    # Known non-name phrases.
    if lower_text in STOP_PHRASES:
        return False, 0

    # Dates are not names.
    if is_date(text):
        return False, 0

    # URLs are not names.
    if is_url(text):
        return False, 0

    # Obvious diagram / formatting fragments.
    if any(
        symbol in text
        for symbol in [
            "**",
            "→",
            "↓",
            "###"
        ]
    ):
        return False, 0

    score = 0

    # -------------------------------------------------
    # Signal 1: alphabetic words
    # -------------------------------------------------

    name_like_words = 0

    for word in words:

        cleaned = word.strip(
            ".,;:!?()[]{}\"'"
        )

        if not cleaned:
            continue

        if cleaned.isalpha():

            name_like_words += 1

        elif "." in word:

            # Allows initials such as:
            # Dr.
            # A.K.
            name_like_words += 1

    if name_like_words == len(words):

        score += 2

    # -------------------------------------------------
    # Signal 2: capitalization
    # -------------------------------------------------

    capitalized = 0

    for word in words:

        cleaned = word.strip(
            ".,;:!?()[]{}\"'"
        )

        if not cleaned:
            continue

        if cleaned[0].isupper():

            capitalized += 1

    if capitalized >= max(
        1,
        len(words) - 1
    ):

        score += 2

    # -------------------------------------------------
    # Signal 3: ALL CAPS
    # -------------------------------------------------

    if (
        text.upper() == text
        and any(
            character.isalpha()
            for character in text
        )
    ):

        score += 1

    # -------------------------------------------------
    # Signal 4: next paragraph is substantial
    # -------------------------------------------------

    if position + 1 >= len(paragraphs):

        return False, score

    next_text = paragraphs[
        position + 1
    ]["text"].strip()

    if not next_text:

        return False, score

    next_words = next_text.split()

    # A name is usually followed by the actual
    # opinion text.
    if len(next_words) >= 8:

        score += 3

    # If the next paragraph is another obvious
    # heading/fragment, reduce confidence.
    if len(next_words) <= 5:

        next_lower = next_text.lower()

        if next_lower in STOP_PHRASES:

            score -= 2

    return score >= 5, score


def split_opinions(
    paragraphs: list[dict]
) -> list[dict]:
    """
    Split the extracted document into individual opinions.

    A new opinion can begin when:

    1. A bold submitter name is encountered.
    2. A high-confidence plain-text submitter name
       is encountered.
    3. A damaged bold name is encountered.

    Important:
    The plain-name check happens BEFORE adding the
    paragraph to the current opinion. Otherwise the
    submitter name could accidentally become part of
    the previous opinion.

    Each opinion also stores the original DOCX paragraph
    indexes in `source_paragraphs`.
    """

    opinions = []

    current_opinion = None

    for position, paragraph in enumerate(
        paragraphs
    ):

        segments = get_segments(
            paragraph
        )

        if not segments:
            continue

        paragraph_text = paragraph[
            "text"
        ].strip()

        # =================================================
        # CASE 1
        # Damaged bold name
        # =================================================

        if is_damaged_name(
            paragraph,
            segments
        ):

            submitter = paragraph_text

            # Ignore exact duplicate heading
            # when the previous opinion has no content.
            if (
                current_opinion is not None
                and not current_opinion["paragraphs"]
                and current_opinion[
                    "submitter"
                ].strip().lower()
                == submitter.lower()
            ):
                continue

            if current_opinion is not None:

                opinions.append(
                    current_opinion
                )

            current_opinion = {
                "submitter": submitter,
                "paragraphs": [],
                "source_paragraphs": [
                    paragraph["index"]
                ]
            }

            continue

        # =================================================
        # CASE 2
        # Plain-text submitter name
        # =================================================

        has_bold_segment = any(
            segment["type"] == "bold"
            for segment in segments
        )

        # Only test plain-name logic when the paragraph
        # contains no bold formatting.
        if not has_bold_segment:

            is_plain_name, _ = (
                looks_like_plain_name(
                    paragraphs,
                    position
                )
            )

            if is_plain_name:

                submitter = paragraph_text

                # Ignore exact duplicate heading
                # when previous opinion has no content.
                if (
                    current_opinion is not None
                    and not current_opinion[
                        "paragraphs"
                    ]
                    and current_opinion[
                        "submitter"
                    ].strip().lower()
                    == submitter.lower()
                ):
                    continue

                if current_opinion is not None:

                    opinions.append(
                        current_opinion
                    )

                current_opinion = {
                    "submitter": submitter,
                    "paragraphs": [],
                    "source_paragraphs": [
                        paragraph["index"]
                    ]
                }

                continue

        # =================================================
        # CASE 3
        # Process formatted segments
        # =================================================

        for segment in segments:

            segment_type = segment[
                "type"
            ]

            segment_text = segment[
                "text"
            ].strip()

            if not segment_text:
                continue

            # ---------------------------------------------
            # Bold segment = possible submitter heading
            # ---------------------------------------------

            if segment_type == "bold":

                submitter = segment_text

                # Exact duplicate heading with no content
                # between them.
                if (
                    current_opinion is not None
                    and not current_opinion[
                        "paragraphs"
                    ]
                    and current_opinion[
                        "submitter"
                    ].strip().lower()
                    == submitter.lower()
                ):
                    continue

                # Close previous opinion.
                if current_opinion is not None:

                    opinions.append(
                        current_opinion
                    )

                # Start new opinion.
                current_opinion = {
                    "submitter": submitter,
                    "paragraphs": [],
                    "source_paragraphs": [
                        paragraph["index"]
                    ]
                }

            # ---------------------------------------------
            # Normal segment = opinion content
            # ---------------------------------------------

            else:

                if current_opinion is None:
                    continue

                current_opinion[
                    "paragraphs"
                ].append(
                    segment_text
                )

                current_opinion[
                    "source_paragraphs"
                ].append(
                    paragraph["index"]
                )

    # =====================================================
    # Add final opinion
    # =====================================================

    if current_opinion is not None:

        opinions.append(
            current_opinion
        )

    return opinions