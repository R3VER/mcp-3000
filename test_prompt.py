from config import DATABASE_PATH
from storage import get_next_pending_opinion
from evaluation_prompt import build_evaluation_prompt


def main():

    opinion = get_next_pending_opinion(
        DATABASE_PATH
    )

    if opinion is None:

        print("No PENDING opinion found.")

        return

    prompt = build_evaluation_prompt(
        opinion
    )

    print("========== OPINION ==========")
    print(f"Opinion ID: {opinion.opinion_id}")
    print(f"Submitter: {opinion.submitter}")
    print()

    print("========== GENERATED PROMPT ==========")
    print(prompt)


if __name__ == "__main__":

    main()