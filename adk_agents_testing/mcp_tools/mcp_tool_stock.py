from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams


STOCK_MCP_URL = "http://127.0.0.1:8181/sse"


async def return_sse_mcp_tools_stocks():
    print("Attempting to connect to MCP server for stock info...")

    toolset = McpToolset(
        connection_params=SseConnectionParams(
            url=STOCK_MCP_URL,
        ),
    )

    print("MCP Toolset created successfully.")
    return [toolset], toolset


async def return_mcp_tools_stocks():
    """
    Compatibility function for older code.

    This project now uses the SSE stock MCP server instead of launching
    the stock MCP server through stdio.
    """
    return await return_sse_mcp_tools_stocks()