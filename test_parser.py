from result_parser import parse_evaluation_response


def test_valid_response():
    response = """
    {
        "criterion_scores": {
            "1": 4,
            "2": 3,
            "3": 5,
            "4": 4,
            "5": 3
        },
        "reasoning": {
            "1": "The proposal could reduce pollution from the targeted source.",
            "2": "The mechanism is described, but practical evidence is limited.",
            "3": "The approach could potentially be expanded to other locations.",
            "4": "The proposal describes a relatively low-cost approach.",
            "5": "The proposed approach is different from conventional solutions."
        }
    }
    """

    result = parse_evaluation_response(
        response
    )

    print("========== VALID RESPONSE ==========")
    print(result)


def test_invalid_score():
    response = """
    {
        "criterion_scores": {
            "1": 6,
            "2": 3,
            "3": 5,
            "4": 4,
            "5": 3
        },
        "reasoning": {
            "1": "Reason 1",
            "2": "Reason 2",
            "3": "Reason 3",
            "4": "Reason 4",
            "5": "Reason 5"
        }
    }
    """

    result = parse_evaluation_response(
        response
    )

    print()
    print("========== INVALID SCORE ==========")
    print(result)


def test_missing_criterion():
    response = """
    {
        "criterion_scores": {
            "1": 4,
            "2": 3,
            "3": 5,
            "4": 4
        },
        "reasoning": {
            "1": "Reason 1",
            "2": "Reason 2",
            "3": "Reason 3",
            "4": "Reason 4",
            "5": "Reason 5"
        }
    }
    """

    result = parse_evaluation_response(
        response
    )

    print()
    print("========== MISSING CRITERION ==========")
    print(result)


def test_invalid_json():
    response = """
    This is not valid JSON.
    """

    result = parse_evaluation_response(
        response
    )

    print()
    print("========== INVALID JSON ==========")
    print(result)


def main():

    test_valid_response()

    test_invalid_score()

    test_missing_criterion()

    test_invalid_json()


if __name__ == "__main__":
    main()