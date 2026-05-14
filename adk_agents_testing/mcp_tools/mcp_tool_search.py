from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams


SEARCH_MCP_URL = "http://127.0.0.1:8080/sse"


async def return_sse_mcp_tools_search():
    print("Attempting to connect to MCP server for search and page read...")

    toolset = McpToolset(
        connection_params=SseConnectionParams(
            url=SEARCH_MCP_URL,
        ),
    )

    print("MCP Toolset created successfully.")
    return [toolset], toolset


async def return_mcp_tools_search():
    """
    Compatibility function for older code.

    This project now uses the SSE search MCP server instead of launching
    the search MCP server through stdio.
    """
    return await return_sse_mcp_tools_search()