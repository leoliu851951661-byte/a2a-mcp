import asyncio
import logging
import traceback
from uuid import uuid4
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.client import A2AClient
from common.types import Message, TextPart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://127.0.0.1:12000/host_agent"


async def send_message(client: A2AClient, session_id: str, user_text: str):
    task_id = f"task-{uuid4().hex}"

    user_message = Message(
        role="user",
        parts=[TextPart(text=user_text)],
    )

    send_params = {
        "id": task_id,
        "sessionId": session_id,
        "message": user_message.model_dump(),
    }

    logger.info(f"Sending task {task_id} to {SERVER_URL}...")

    response = await client.send_task(payload=send_params)

    if response.error:
        logger.error(
            f"Task {task_id} failed: "
            f"{response.error.message} "
            f"(Code: {response.error.code})"
        )
        return

    if not response.result:
        logger.error(f"Received unexpected response for task {task_id}: {response}")
        return

    task_result = response.result

    logger.info(
        f"Task {task_id} completed with state: "
        f"{task_result.status.state}"
    )

    if task_result.status.message and task_result.status.message.parts:
        for part in task_result.status.message.parts:
            if hasattr(part, "text") and part.text:
                print(f"\nAssistant: {part.text}")
    else:
        logger.warning("No message part in agent response status")


async def main():
    client = A2AClient(url=SERVER_URL)

    # Keep this session_id for the whole conversation.
    session_id = f"session-{uuid4().hex}"

    print("Chat started. Type 'exit' or 'quit' to stop.")
    print(f"Session ID: {session_id}")

    while True:
        user_text = input("\nYou: ").strip()

        if user_text.lower() in {"exit", "quit", "q"}:
            print("Exiting chat.")
            break

        if not user_text:
            continue

        try:
            await send_message(
                client=client,
                session_id=session_id,
                user_text=user_text,
            )

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"An error occurred while communicating with the agent: {e}")


if __name__ == "__main__":
    asyncio.run(main())