import asyncio

from fastmcp import Client


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        # ================================================
        # 1. CHECK INITIAL QUEUE
        # ================================================

        print(
            "========== INITIAL QUEUE =========="
        )

        result = await client.call_tool(
            "get_boundary_queue_status_tool",
            {}
        )

        print(result.data)

        print()

        # ================================================
        # 2. GET NEXT BATCH
        # ================================================

        print(
            "========== GET NEXT BATCH =========="
        )

        result = await client.call_tool(
            "get_next_boundary_batch",
            {
                "context_size": 1
            }
        )

        data = result.data

        print(
            f"Available: "
            f"{data.get('available')}"
        )

        if not data.get("available"):

            print(
                "No boundary batch available."
            )

            return

        print(
            f"Batch ID: "
            f"{data['batch_id']}"
        )

        print(
            f"Start ID: "
            f"{data['start_opinion_id']}"
        )

        print(
            f"End ID: "
            f"{data['end_opinion_id']}"
        )

        print(
            f"Batch size: "
            f"{data['batch_size']}"
        )

        print(
            f"Status: "
            f"{data['status']}"
        )

        print()

        # ================================================
        # 3. SHOW CONTEXT
        # ================================================

        print(
            "========== PREVIOUS CONTEXT =========="
        )

        for opinion in data[
            "previous_context"
        ]:

            print(
                f"{opinion['opinion_id']} | "
                f"{opinion['submitter']}"
            )

        print()

        print(
            "========== TARGET OPINIONS =========="
        )

        for opinion in data[
            "target_opinions"
        ]:

            print(
                f"{opinion['opinion_id']} | "
                f"{opinion['submitter']}"
            )

        print()

        print(
            "========== NEXT CONTEXT =========="
        )

        for opinion in data[
            "next_context"
        ]:

            print(
                f"{opinion['opinion_id']} | "
                f"{opinion['submitter']}"
            )

        print()

        # ================================================
        # 4. CHECK QUEUE AFTER CLAIM
        # ================================================

        print(
            "========== QUEUE AFTER CLAIM =========="
        )

        result = await client.call_tool(
            "get_boundary_queue_status_tool",
            {}
        )

        print(result.data)

        print()

        # ================================================
        # 5. IMPORTANT
        # ================================================

        print(
            "========== TEST COMPLETE =========="
        )

        print(
            "The batch was intentionally claimed "
            "and is now PROCESSING."
        )

        print(
            "We will reset it after verifying "
            "the queue behavior."
        )


if __name__ == "__main__":
    asyncio.run(main())