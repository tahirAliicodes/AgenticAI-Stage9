# Stage9/tracer/token_counter.py


def estimate_tokens(text: str) -> int:
    """Rough token estimate — 1 token ≈ 4 characters."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_messages(messages: list[dict]) -> tuple[int, int]:
    """
    Given a messages list (like you pass to Ollama),
    returns (tokens_in, tokens_out).

    tokens_in  = everything in the messages list (the prompt)
    tokens_out = 0 here, pass the response text separately
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):  # multimodal content blocks
            for block in content:
                if isinstance(block, dict):
                    total += estimate_tokens(block.get("text", ""))
    return total, 0


def count_response(response_text: str) -> int:
    """Count tokens in the LLM's response."""
    return estimate_tokens(response_text)
