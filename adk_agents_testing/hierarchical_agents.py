import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.genai import types
from termcolor import colored

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from adk_agents_testing.mcp_tools.mcp_tool_search import return_sse_mcp_tools_search
from adk_agents_testing.mcp_tools.mcp_tool_stock import return_sse_mcp_tools_stocks

load_dotenv(find_dotenv())

MODEL = "gemini-2.5-flash-lite"
APP_NAME = "company_analysis_app"
USER_ID = "searcher_usr"
SESSION_ID = "searcher_session"


async def async_main():
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()

    search_toolset = None
    stocks_toolset = None

    try:
        print(colored(text="Creating session...", color="blue"))

        session = await session_service.create_session(
            state={},
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )

        print(colored(text="Session created!", color="blue"))

        search_tools, search_toolset = await return_sse_mcp_tools_search()
        stocks_tools, stocks_toolset = await return_sse_mcp_tools_stocks()

        stock_analysis_agent = Agent(
            model=MODEL,
            name="stock_analysis_agent",
            instruction=(
                "Analyze stock data and provide insights. "
                "If the user gives a company name, first find the stock symbol. "
                "Then get the latest stock price using the available stock tools."
            ),
            description=(
                "Handles stock analysis and provides insights, "
                "in particular, can get the latest stock price."
            ),
            tools=stocks_tools,
        )

        search_agent = Agent(
            model=MODEL,
            name="search_agent",
            instruction=(
                "Expert web researcher. "
                "Can search Google and read pages online using available search tools."
            ),
            description="Handles search queries and can read pages online.",
            tools=search_tools,
        )

        root_agent = Agent(
            name="company_analysis_assistant",
            model=MODEL,
            description=(
                "Main assistant: handles requests about stocks and company information."
            ),
            instruction=(
                "You are the main assistant coordinating a team.\n"
                "1. If the user asks about a company, provide a useful report.\n"
                "2. If the user needs current stock price, delegate to stock_analysis_agent.\n"
                "3. If the user needs current web information, delegate to search_agent.\n"
                "4. If the user asks a vague stock question, ask which company or ticker they mean.\n"
                "5. Continue the conversation naturally using the previous context."
            ),
            sub_agents=[
                search_agent,
                stock_analysis_agent,
            ],
            output_key="last_assistant_response",
        )

        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )

        print(colored(text="Chat started. Type 'exit' or 'quit' to stop.", color="blue"))

        while True:
            query = input("\nYou: ").strip()

            if query.lower() in {"exit", "quit", "q"}:
                print(colored(text="Exiting chat...", color="yellow"))
                break

            if not query:
                continue

            content = types.Content(
                role="user",
                parts=[types.Part(text=query)],
            )

            print(colored(text="Running agent...", color="blue"))

            final_response_text = None

            async for event in runner.run_async(
                session_id=session.id,
                user_id=session.user_id,
                new_message=content,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
                    elif event.actions and event.actions.escalate:
                        final_response_text = (
                            f"Agent escalated: "
                            f"{event.error_message or 'No specific message.'}"
                        )

            print(
                colored(
                    text=f"\nAssistant:\n{final_response_text}",
                    color="green",
                )
            )

    finally:
        print("Closing MCP server connections...")

        if stocks_toolset is not None:
            await stocks_toolset.close()

        if search_toolset is not None:
            await search_toolset.close()

        print("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(async_main())