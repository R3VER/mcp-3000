import asyncio

from fastmcp import Client

from config import DATABASE_PATH

from storage import (
    get_boundary_queue_status,
    reset_processing_boundary_batches,
)


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        # =================================================
        # 1. INITIAL STATUS
        # =================================================

        print(
            "========== INITIAL STATUS =========="
        )

        print(
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )

        # =================================================
        # 2. CLAIM NEXT BATCH THROUGH MCP
        # =================================================

        print()
        print(
            "========== CLAIM BATCH =========="
        )

        result = await client.call_tool(
            "get_next_boundary_batch",
            {
                "context_size": 1
            }
        )

        data = result.data

        print(
            "Batch ID:",
            data.get("batch_id")
        )

        print(
            "Start:",
            data.get("start_opinion_id")
        )

        print(
            "End:",
            data.get("end_opinion_id")
        )

        print(
            "Status:",
            data.get("status")
        )

        # =================================================
        # 3. CHECK STATUS AFTER CLAIM
        # =================================================

        print()
        print(
            "========== AFTER CLAIM =========="
        )

        print(
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )

        # =================================================
        # 4. CREATE TEST DECISIONS
        # =================================================

        target_opinions = data[
            "target_opinions"
        ]

        opinion_ids = [
            opinion["opinion_id"]
            for opinion in target_opinions
        ]

        decisions = []

        for opinion_id in opinion_ids:

            decisions.append(
                {
                    "opinion_id": opinion_id,
                    "action": "KEEP",
                    "target_opinion_id": None,
                    "reason": (
                        "TEST ONLY: "
                        "artificial KEEP decision "
                        "used to verify the MCP "
                        "queue workflow."
                    )
                }
            )

        # =================================================
        # 5. SUBMIT THROUGH MCP
        # =================================================

        print()
        print(
            "========== SUBMIT REVIEW =========="
        )

        result = await client.call_tool(
            "submit_boundary_review",
            {
                "batch_id": data["batch_id"],

                "start_opinion_id": (
                    data["start_opinion_id"]
                ),

                "opinion_ids": opinion_ids,

                "decisions": decisions,
            }
        )

        submit_data = result.data

        print(
            submit_data
        )

        # =================================================
        # 6. FINAL STATUS
        # =================================================

        print()
        print(
            "========== FINAL STATUS =========="
        )

        print(
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )

        # =================================================
        # 7. RESET PROCESSING JOBS
        # =================================================

        print()
        print(
            "========== CLEANUP =========="
        )

        reset_processing_boundary_batches(
            DATABASE_PATH
        )

        print(
            get_boundary_queue_status(
                DATABASE_PATH
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
    