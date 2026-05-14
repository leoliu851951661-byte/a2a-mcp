import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from a2a_servers.agent_servers.utils import (
    generate_agent_card,
    generate_agent_task_manager,
)
from a2a_servers.agents.adk_agent import ADKAgent
from a2a_servers.common.server.server import A2AServer
from a2a_servers.common.types import AgentSkill


async def run_agent():
    AGENT_NAME = "host_agent"
    AGENT_DESCRIPTION = (
        "An agent that orchestrates the decomposition of the user request "
        "into tasks that can be performed by child agents."
    )

    PORT = 12000
    HOST = "127.0.0.1"
    AGENT_URL = f"http://{HOST}:{PORT}"
    AGENT_VERSION = "1.0.0"

    MODEL = "gemini-2.5-flash"

    AGENT_SKILLS = [
        AgentSkill(
            id="COORDINATE_AGENT_TASKS",
            name="coordinate_tasks",
            description="Coordinate tasks between agents.",
        ),
    ]

    list_urls = [
        "http://127.0.0.1:11000/google_search_agent",
        "http://127.0.0.1:10001/stock_agent",
    ]

    AGENT_CARD = generate_agent_card(
        agent_name=AGENT_NAME,
        agent_description=AGENT_DESCRIPTION,
        agent_url=AGENT_URL,
        agent_version=AGENT_VERSION,
        can_stream=False,
        can_push_notifications=False,
        can_state_transition_history=True,
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=AGENT_SKILLS,
    )

    host_agent = ADKAgent(
        model=MODEL,
        name="host_agent",
        description=AGENT_DESCRIPTION,
        tools=[],
        instructions=(
            "You are a host/orchestrator agent. "
            "Route search-related tasks to the Google search agent. "
            "Route stock-price and stock-symbol tasks to the stock agent. "
            "Combine the child agents' answers into a clear final response."
        ),
        is_host_agent=True,
        remote_agent_addresses=list_urls,
    )

    task_manager = generate_agent_task_manager(
        agent=host_agent,
    )

    server = A2AServer(
        host=HOST,
        port=PORT,
        endpoint="/host_agent",
        agent_card=AGENT_CARD,
        task_manager=task_manager,
    )

    print(f"Starting {AGENT_NAME} A2A Server on {AGENT_URL}")
    print(f"Host endpoint: {AGENT_URL}/host_agent")

    await server.astart()


if __name__ == "__main__":
    asyncio.run(run_agent())