"""
ConversationalAgent: stateless multi-turn tool-use loop using the Anthropic SDK.
Conversation history is passed in from the frontend on each request.
"""
from typing import Any

import anthropic
import structlog

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DEFINITIONS, handle_tool_call
from app.config import settings

logger = structlog.get_logger(__name__)

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_TOOL_ROUNDS = 10


async def chat(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """
    Run the agent tool-use loop.

    Args:
        messages: Full conversation history in Anthropic message format.

    Returns:
        (final_text_response, updated_messages_list)
    """
    current_messages = list(messages)
    final_text = ""

    for _ in range(MAX_TOOL_ROUNDS):
        response = await _client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=current_messages,
        )

        # Append assistant response to history.
        # Convert SDK objects (TextBlock, ToolUseBlock, …) to plain dicts so the
        # message list stays JSON-serialisable end-to-end.
        content_dicts = [block.model_dump() for block in response.content]
        current_messages.append({"role": "assistant", "content": content_dicts})

        if response.stop_reason == "end_turn":
            # Extract text from the response
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info("Tool call", tool=block.name, input=block.input)
                    result = await handle_tool_call(block.name, dict(block.input))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": _serialize_result(result),
                    })

            current_messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break

    return final_text, current_messages


def _serialize_result(result: Any) -> str:
    import json
    try:
        return json.dumps(result, default=str)
    except Exception:
        return str(result)
