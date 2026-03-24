---
name: claude-api
description: Build applications using the Claude API and Anthropic SDKs. Use when the user asks to integrate Claude, call the Anthropic API, build AI-powered features, or work with Claude models programmatically.
metadata:
  author: anthropic
  version: "1.0.0"
---

# Claude API

Help users build applications with the Claude API and Anthropic SDKs.

## When to Trigger

Activate when code imports `anthropic`, `@anthropic-ai/sdk`, or `claude_agent_sdk`, or when the user asks to use the Claude API, Anthropic SDKs, or Agent SDK.

Do NOT trigger when code imports `openai` or other AI SDKs, or for general programming or ML/data-science tasks unrelated to Claude.

## SDK Installation

### Python
```bash
pip install anthropic
```

### TypeScript/JavaScript
```bash
npm install @anthropic-ai/sdk
```

## Authentication

The API key should be set as an environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Never hardcode API keys in source code. Use environment variables or secret managers.

## Basic Usage

### Python
```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ]
)
print(message.content[0].text)
```

### TypeScript
```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const message = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 1024,
  messages: [
    { role: "user", content: "Hello, Claude!" }
  ],
});
console.log(message.content[0].text);
```

## Model Selection

Use the latest model IDs:
- **Claude Opus 4.6**: `claude-opus-4-6` — Most capable, best for complex reasoning
- **Claude Sonnet 4.6**: `claude-sonnet-4-6` — Balanced performance and speed
- **Claude Haiku 4.5**: `claude-haiku-4-5-20251001` — Fastest, best for simple tasks

## Advanced Features

### Streaming
```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Tool Use
```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"}
            },
            "required": ["location"]
        }
    }],
    messages=[{"role": "user", "content": "What's the weather in London?"}]
)
```

### Vision
```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_data}},
            {"type": "text", "text": "Describe this image."}
        ]
    }]
)
```

### Extended Thinking
```python
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[{"role": "user", "content": "Solve this complex problem..."}]
)
```

## Best Practices

1. **Set reasonable max_tokens** — Don't use excessively large values; match to expected output size
2. **Use system prompts** — Provide clear context and instructions via the `system` parameter
3. **Handle rate limits** — Implement exponential backoff for 429 responses
4. **Use streaming** — For user-facing applications, stream responses for better UX
5. **Validate inputs** — Sanitize user inputs before sending to the API
6. **Monitor usage** — Track token consumption via response `usage` fields

## Error Handling

```python
from anthropic import APIError, RateLimitError, APIConnectionError

try:
    message = client.messages.create(...)
except RateLimitError:
    # Implement backoff and retry
    pass
except APIConnectionError:
    # Handle network issues
    pass
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```
