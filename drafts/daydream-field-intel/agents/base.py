import asyncio
import json
import re
from groq import AsyncGroq, RateLimitError
from tools import TOOL_DEFINITIONS, execute_tool

FAST_MODEL  = "llama-3.1-8b-instant"      # replaces Haiku  (research agents)
SMART_MODEL = "llama-3.3-70b-versatile"   # replaces Sonnet (synthesis / factcheck / followup)

# Keep old names as aliases so other modules don't need to change
HAIKU  = FAST_MODEL
SONNET = SMART_MODEL


def _rate_limit_wait(error: RateLimitError) -> float:
    """Parse 'try again in Xs' from the error message, default 20s."""
    match = re.search(r"try again in ([\d.]+)s", str(error))
    return float(match.group(1)) + 1.0 if match else 20.0


def get_client() -> AsyncGroq:
    return AsyncGroq()   # reads GROQ_API_KEY from env


async def call_model(
    client: AsyncGroq,
    system: str,
    user: str,
    model: str = SMART_MODEL,
    max_tokens: int = 1024,
) -> str:
    """Single-turn LLM call with no tools. Used for extraction / structured output."""
    while True:
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        except RateLimitError as e:
            await asyncio.sleep(_rate_limit_wait(e))


async def run_agent(
    client: AsyncGroq,
    system: str,
    user_message: str,
    model: str = FAST_MODEL,
    max_iterations: int = 10,
) -> str:
    """
    Agentic tool-use loop (OpenAI-compatible format used by Groq).
    Runs until the model stops calling tools or max_iterations is hit.
    """
    messages = [
        {"role": "system",  "content": system},
        {"role": "user",    "content": user_message},
    ]

    response = None
    for _ in range(max_iterations):
        while True:
            try:
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=4096,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                )
                break
            except RateLimitError as e:
                wait = _rate_limit_wait(e)
                await asyncio.sleep(wait)

        choice = response.choices[0]

        if choice.finish_reason == "stop":
            return choice.message.content or ""

        if choice.finish_reason == "tool_calls":
            tool_calls = choice.message.tool_calls or []

            # Append assistant turn (with tool_calls)
            messages.append({
                "role":       "assistant",
                "content":    choice.message.content,
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool and append results
            for tc in tool_calls:
                inputs = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, inputs)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result,
                })

    # Fallback: return whatever the last response had
    if response:
        return response.choices[0].message.content or ""
    return ""
