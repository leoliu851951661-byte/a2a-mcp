import asyncio
import os
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk import Runner
from google.genai import types
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters
from requests import session
import asyncio
import contextlib
import socket

import uvicorn

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.search_server import create_starlette_app, mcp
load_dotenv(find_dotenv())

project_path = os.getenv("PROJECT_PATH")
mcp_server_dir = os.path.join(project_path, "mcp_server")

_uvicorn_server = None
_uvicorn_task = None


async def wait_for_port(host: str, port: int, timeout: float = 10.0):
    start = asyncio.get_running_loop().time()

    while True:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            if asyncio.get_running_loop().time() - start > timeout:
                raise TimeoutError(f"Server did not start on {host}:{port}")
            await asyncio.sleep(0.2)


async def start_mcp_sse_server():
    global _uvicorn_server, _uvicorn_task

    if _uvicorn_server is not None:
        return

    starlette_app = mcp.sse_app()

    config = uvicorn.Config(
        starlette_app,
        host="127.0.0.1",
        port=8080,
        log_level="info",
    )

    _uvicorn_server = uvicorn.Server(config)
    _uvicorn_task = asyncio.create_task(_uvicorn_server.serve())

    await wait_for_port("127.0.0.1", 8080)


async def stop_mcp_sse_server():
    global _uvicorn_server, _uvicorn_task

    if _uvicorn_server is not None:
        _uvicorn_server.should_exit = True

    if _uvicorn_task is not None:
        with contextlib.suppress(asyncio.CancelledError):
            await _uvicorn_task

    _uvicorn_server = None
    _uvicorn_task = None

async def get_agent_async():
    """Creates an ADK Agent equipped with tools from the MCP Server."""
    toolset = await get_tools_async()

    root_agent = LlmAgent(
        model='gemini-2.5-flash',
        name='search_agent',
        description="Agent to answer questions using Google Search.",
        instruction=(
            "You are an expert researcher. When someone asks you something "
            "you always double check online. You always stick to the facts."
        ),
        tools=[toolset],
    )

    return root_agent, toolset

async def get_tools_async():
    """Gets tools from the Search MCP Server."""
    print("Starting embedded MCP SSE server...")
    await start_mcp_sse_server()

    print("Connecting ADK to MCP SSE server...")

    toolset = McpToolset(
        connection_params=SseConnectionParams(
            url="http://127.0.0.1:8080/sse",
        ),
    )

    print("MCP Toolset created successfully.")
    return toolset

async def async_main():
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()
    toolset = None

    try:
        print("Creating session...")
        session = await session_service.create_session(
            state={},
            app_name="mcp_search_app",
            user_id="searcher_usr",
            session_id="searcher_session",
        )

        print(f"Session created with ID: {session.id}")

        query = "What are the typical sports of the Aosta Valley? Answer precisely and in lots of detail."
        print(f"User Query: '{query}'")

        content = types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )

        root_agent, toolset = await get_agent_async()

        runner = Runner(
            app_name="mcp_search_app",
            agent=root_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )

        print("Running agent...")

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
                        f"Agent escalated: {event.error_message or 'No specific message.'}"
                    )

        print(f"############# Final Response #############\n\n{final_response_text}")

    finally:
        if toolset is not None:
            print("Closing MCP toolset...")
            await toolset.close()

        print("Stopping embedded MCP SSE server...")
        await stop_mcp_sse_server()

        print("Cleanup complete.")


if __name__ == '__main__':
    asyncio.run(async_main())