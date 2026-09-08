"""Test the MCP server tools."""
import asyncio
from tokenscan_mcp.server import mcp


async def test():
    # List tools
    result = await mcp.list_tools()
    print("=== TOOLS ===")
    for t in result:
        print(f"  {t.name}: {t.description[:80]}")

    # Test verify_relay
    print("\n=== verify_relay('openrouter') ===")
    r = await mcp.call_tool("verify_relay", {"relay_id": "openrouter"})
    print(f"type: {type(r)}")
    if isinstance(r, tuple):
        for i, item in enumerate(r):
            print(f"  [{i}] type={type(item)}")
            if hasattr(item, 'text'):
                print(f"      text={item.text[:300]}")
            elif isinstance(item, str):
                print(f"      str={item[:300]}")
            elif hasattr(item, '__str__'):
                print(f"      str={str(item)[:300]}")
    elif isinstance(r, list):
        print(f"  list len={len(r)}")
        for item in r[:3]:
            print(f"    type={type(item)}, str={str(item)[:200]}")
    else:
        print(f"  str={str(r)[:500]}")

    # Test search_relays
    print("\n=== search_relays('claude') ===")
    r = await mcp.call_tool("search_relays", {"query": "claude"})
    print(str(r)[:500])

    # Test relay_details
    print("\n=== relay_details('deepseek') ===")
    r = await mcp.call_tool("relay_details", {"relay_id": "deepseek"})
    print(str(r)[:500])


asyncio.run(test())
