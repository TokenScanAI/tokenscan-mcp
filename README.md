# TokenAPI Scan MCP Server

MCP server for verifying AI API relay services. Query real-time verification status, success rates, and trust data for 240+ relay providers.

## Tools

### `verify_relay`
Check if a relay site is verified and get its trust level.

### `search_relays`
Search for relay sites by name or keyword.

### `relay_details`
Get detailed verification statistics for a relay.

## Usage with Claude Code

```json
{
  "mcpServers": {
    "tokenscan": {
      "command": "uvx",
      "args": ["tokenscan-mcp"]
    }
  }
}
```

Or install directly: `pip install tokenscan-mcp`
