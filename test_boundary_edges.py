import asyncio

from fastmcp import Client


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        print(
            "========== TEST 1: "
            "MERGE WITH PREVIOUS CONTEXT =========="
        )

        decisions = [
            {
                "opinion_id": 109,
                "action": "MERGE_WITH_PREVIOUS",
                "target_opinion_id": 108,
                "reason": (
                    "Test only: checking whether "
                    "the first target can reference "
                    "the immediately preceding context."
                )
            },
            {
                "opinion_id": 110,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 114,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            }
        ]

        result = await client.call_tool(
            "submit_boundary_review",
            {
                "start_opinion_id": 109,
                "opinion_ids": [
                    109,
                    110,
                    111,
                    112,
                    113,
                    114
                ],
                "decisions": decisions
            }
        )

        print(result)

        print()
        print(
            "========== TEST 2: "
            "MERGE WITH NEXT CONTEXT =========="
        )

        decisions = [
            {
                "opinion_id": 109,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 110,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 114,
                "action": "MERGE_WITH_NEXT",
                "target_opinion_id": 115,
                "reason": (
                    "Test only: checking whether "
                    "the last target can reference "
                    "the immediately following context."
                )
            }
        ]

        result = await client.call_tool(
            "submit_boundary_review",
            {
                "start_opinion_id": 109,
                "opinion_ids": [
                    109,
                    110,
                    111,
                    112,
                    113,
                    114
                ],
                "decisions": decisions
            }
        )

        print(result)

        print()
        print(
            "========== TEST 3: INVALID CONTEXT =========="
        )

        decisions = [
            {
                "opinion_id": 109,
                "action": "MERGE_WITH_PREVIOUS",
                "target_opinion_id": 107,
                "reason": (
                    "This should fail because 107 "
                    "is not the immediate previous "
                    "context."
                )
            },
            {
                "opinion_id": 110,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 111,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 112,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 113,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            },
            {
                "opinion_id": 114,
                "action": "KEEP",
                "target_opinion_id": None,
                "reason": "Test decision."
            }
        ]

        result = await client.call_tool(
            "submit_boundary_review",
            {
                "start_opinion_id": 109,
                "opinion_ids": [
                    109,
                    110,
                    111,
                    112,
                    113,
                    114
                ],
                "decisions": decisions
            }
        )

        print(result)


if __name__ == "__main__":
    asyncio.run(main())