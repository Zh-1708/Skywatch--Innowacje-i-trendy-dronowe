---
name: mcp-builder
description: Build Model Context Protocol (MCP) servers for Claude. Use when the user asks to create an MCP server, add tools for Claude, build integrations, or connect Claude to external services.
metadata:
  author: anthropic
  version: "1.0.0"
---

# MCP Builder

Help users build Model Context Protocol (MCP) servers that provide tools, resources, and prompts to Claude.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that lets AI assistants like Claude connect to external data sources and tools. An MCP server exposes:
- **Tools** — Functions that Claude can call (e.g., query a database, call an API)
- **Resources** — Data that Claude can read (e.g., files, database records)
- **Prompts** — Pre-built prompt templates for common tasks

## Quick Start

### Python MCP Server

```bash
pip install mcp
```

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

@mcp.resource("config://app")
def get_config() -> str:
    """Return application configuration."""
    return "App config data here"

if __name__ == "__main__":
    mcp.run()
```

### TypeScript MCP Server

```bash
npm install @modelcontextprotocol/sdk
```

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

server.tool("greet", { name: z.string() }, async ({ name }) => ({
  content: [{ type: "text", text: `Hello, ${name}!` }],
}));

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Project Structure

```
my-mcp-server/
├── src/
│   └── index.ts          # Server entry point
├── package.json
├── tsconfig.json
└── README.md
```

## Registering with Claude Code

Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["path/to/server/dist/index.js"]
    }
  }
}
```

Or for Python:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

## Tool Design Guidelines

1. **Clear names** — Use descriptive, action-oriented tool names (e.g., `search_issues`, `create_file`)
2. **Good descriptions** — Write clear descriptions so Claude knows when to use each tool
3. **Typed parameters** — Use proper types and mark required vs optional parameters
4. **Error handling** — Return helpful error messages, not stack traces
5. **Idempotency** — Where possible, make tools safe to retry
6. **Minimal scope** — Each tool should do one thing well

## Common Patterns

### Database Query Tool
```python
@mcp.tool()
def query_database(sql: str) -> str:
    """Execute a read-only SQL query against the database."""
    # Validate it's a SELECT query
    if not sql.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed"
    result = db.execute(sql)
    return json.dumps(result, default=str)
```

### API Integration Tool
```python
@mcp.tool()
def search_jira(query: str, max_results: int = 10) -> str:
    """Search Jira issues using JQL query syntax."""
    response = jira_client.search(query, maxResults=max_results)
    return json.dumps([{
        "key": issue.key,
        "summary": issue.fields.summary,
        "status": issue.fields.status.name
    } for issue in response])
```

### File Resource
```python
@mcp.resource("docs://{path}")
def read_doc(path: str) -> str:
    """Read a documentation file."""
    doc_path = DOCS_DIR / path
    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    return doc_path.read_text()
```

## Testing

Test your MCP server using the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

Or test tools directly:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"greet","arguments":{"name":"World"}}}' | node dist/index.js
```

## Best Practices

- Keep servers focused — one server per domain/service
- Use environment variables for secrets, never hardcode them
- Implement proper input validation on all tool parameters
- Add logging for debugging but keep output clean on stdio transport
- Handle graceful shutdown
- Document all tools and resources clearly
