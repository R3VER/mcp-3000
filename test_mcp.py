import asyncio

from fastmcp import Client


SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main():

    client = Client(SERVER_URL)

    async with client:

        print("========== MCP CONNECTION ==========")
        print("Connected to MCP server")
        print()

        print("========== AVAILABLE TOOLS ==========")

        tools = await client.list_tools()

        for tool in tools:
            print(f"- {tool.name}")

        print()

        print("========== BOUNDARY CONTEXT TEST ==========")

        result = await client.call_tool(
            "get_boundary_batch",
            {
                "start_opinion_id": 109,
                "batch_size": 6,
                "context_size": 1
            }
        )

        data = result.data

        print()

        print("========== PREVIOUS CONTEXT ==========")

        for opinion in data["previous_context"]:
            print(
                f"ID: {opinion['opinion_id']} | "
                f"Submitter: {opinion['submitter']}"
            )

        print()

        print("========== TARGET OPINIONS ==========")

        for opinion in data["target_opinions"]:
            print(
                f"ID: {opinion['opinion_id']} | "
                f"Submitter: {opinion['submitter']}"
            )

        print()

        print("========== NEXT CONTEXT ==========")

        for opinion in data["next_context"]:
            print(
                f"ID: {opinion['opinion_id']} | "
                f"Submitter: {opinion['submitter']}"
            )

        print()

        print("========== BATCH INFORMATION ==========")

        print(
            f"Start ID: "
            f"{data['start_opinion_id']}"
        )

        print(
            f"Target count: "
            f"{data['batch_size']}"
        )

        print(
            f"Context size: "
            f"{data['context_size']}"
        )

        print()

        print("========== PROMPT CHECK ==========")

        prompt = data[
            "boundary_review_prompt"
        ]

        print(
            "Prompt generated:",
            bool(prompt)
        )

        print(
            "Prompt length:",
            len(prompt)
        )


if __name__ == "__main__":
    asyncio.run(main())