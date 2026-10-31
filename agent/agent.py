"""The agent loop: send the conversation to Claude, run any tools it asks for, repeat until it answers.

Every tool call and result is recorded in a trace (shown in the app, saved as test evidence).
"""
import json

import anthropic

from agent.prompts import PROMPTS
from agent.tools import TOOLS, execute

MODEL = "claude-haiku-5-5"
MAX_TOOL_TURNS = 8
MAX_TOKENS = 8000


def run_agent(api_key, messages, prompt_version="v1"):
    """messages: conversation so far (list of {"role", "content"}), ending with the user's message.
    Returns (answer_text, messages_with_this_turn, trace)."""
    client = anthropic.Anthropic(api_key=api_key)
    messages = list(messages)
    trace = []

    for turn in range(MAX_TOOL_TURNS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=PROMPTS[prompt_version],
            tools=TOOLS,
            messages=messages,
        )
        # Keep the full content (including thinking blocks) so the next request is valid.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "\n".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason == "max_tokens":
                text += "\n\n[Stopped: the answer hit the length limit. Ask again or narrow the question.]"
            elif response.stop_reason == "refusal":
                text = "[The model declined this request.]"
            trace.append({"step": "final_answer", "stop_reason": response.stop_reason,
                          "usage": {"input_tokens": response.usage.input_tokens,
                                    "output_tokens": response.usage.output_tokens}})
            return text, messages, trace

        if turn == MAX_TOOL_TURNS:
            break

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            output, is_error = execute(block.name, block.input)
            trace.append({"step": len(trace) + 1, "tool": block.name, "input": block.input,
                          "output": json.loads(output), "is_error": is_error})
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    # Turn limit reached: stop rather than loop forever, and escalate.
    stop_note = (f"[Stopped after {MAX_TOOL_TURNS} tool rounds without a final answer. "
                 "This needs human review.]")
    messages.append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": b.id, "content": "Stopped: tool-round limit reached.",
         "is_error": True} for b in response.content if b.type == "tool_use"]})
    trace.append({"step": "stopped", "reason": "max tool rounds reached"})
    return stop_note, messages, trace
