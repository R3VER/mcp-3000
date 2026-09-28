import asyncio

from fastmcp import Client


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        # =================================================
        # STEP 1: GET A REAL BATCH
        # =================================================

        print("========== STEP 1: GET BATCH ==========")

        batch_result = await client.call_tool(
            "get_boundary_batch",
            {
                "start_opinion_id": 109,
                "batch_size": 6
            }
        )

        batch = batch_result.data

        print(
            f"Available: {batch['available']}"
        )

        opinion_ids = [
            opinion["opinion_id"]
            for opinion in batch["opinions"]
        ]

        print(
            f"Opinion IDs: {opinion_ids}"
        )

        print()

        # =================================================
        # STEP 2: CREATE A VALID REVIEW
        # =================================================

        print("========== STEP 2: SUBMIT REVIEW ==========")

        decisions = [
            {
                "opinion_id": 109,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            },
            {
                "opinion_id": 110,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            },
            {
                "opinion_id": 114,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": (
                    "This appears to be "
                    "an independent submission."
                )
            }
        ]

        submit_result = await client.call_tool(
            "submit_boundary_review",
            {
                "start_opinion_id": 109,
                "opinion_ids": opinion_ids,
                "decisions": decisions
            }
        )

        print(
            submit_result
        )

        print()

        # =================================================
        # STEP 3: RESULT
        # =================================================

        data = submit_result.data

        print("========== STEP 3: RESULT ==========")

        print(
            f"Valid: {data.get('valid')}"
        )

        print(
            f"Saved: {data.get('saved')}"
        )

        print(
            f"Review ID: {data.get('review_id')}"
        )

        print(
            f"Status: {data.get('status')}"
        )

        print(
            f"Message: {data.get('message')}"
        )


if __name__ == "__main__":
    asyncio.run(main())