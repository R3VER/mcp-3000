import asyncio

from fastmcp import Client


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        # =================================================
        # Get a real boundary batch
        # =================================================

        print("========== GET BOUNDARY BATCH ==========")

        result = await client.call_tool(
            "get_boundary_batch",
            {
                "start_opinion_id": 109,
                "batch_size": 6
            }
        )

        data = result.data

        print(
            f"Batch available: "
            f"{data['available']}"
        )

        opinion_ids = [
            opinion["opinion_id"]
            for opinion in data["opinions"]
        ]

        print(
            f"Opinion IDs: {opinion_ids}"
        )

        print()

        # =================================================
        # TEST 1 — VALID
        # =================================================

        print("========== TEST 1: VALID ==========")

        valid_decisions = [
            {
                "opinion_id": 109,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Independent transport submission."
            },
            {
                "opinion_id": 110,
                "action": "MERGE_WITH_NEXT",
                "target_opinion_id": 111,
                "reason": "Testing merge validation."
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Independent submission."
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Independent submission."
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Independent submission."
            },
            {
                "opinion_id": 114,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Independent road-dust submission."
            }
        ]

        valid_result = await client.call_tool(
            "validate_boundary_review",
            {
                "opinion_ids": opinion_ids,
                "decisions": valid_decisions
            }
        )

        print(valid_result)
        print()

        # =================================================
        # TEST 2 — INVALID TARGET
        # =================================================

        print(
            "========== TEST 2: INVALID MERGE TARGET =========="
        )

        invalid_target_decisions = [
            {
                "opinion_id": 109,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 110,
                "action": "MERGE_WITH_NEXT",
                "target_opinion_id": 114,
                "reason": "Wrong target."
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 114,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            }
        ]

        invalid_target_result = await client.call_tool(
            "validate_boundary_review",
            {
                "opinion_ids": opinion_ids,
                "decisions": invalid_target_decisions
            }
        )

        print(invalid_target_result)
        print()

        # =================================================
        # TEST 3 — MISSING DECISION
        # =================================================

        print(
            "========== TEST 3: MISSING DECISION =========="
        )

        missing_decision_list = [
            {
                "opinion_id": 109,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 110,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": ""
            }
        ]

        missing_result = await client.call_tool(
            "validate_boundary_review",
            {
                "opinion_ids": opinion_ids,
                "decisions": missing_decision_list
            }
        )

        print(missing_result)
        print()


if __name__ == "__main__":
    asyncio.run(main())