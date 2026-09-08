"""TokenAPI Scan MCP Server.

MCP server that provides tools for verifying AI API relay services.
Uses the TokenAPI Scan public API at https://tokenscanai.com.
"""

import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("TOKENSCAN_API_BASE", "https://tokenscanai.com")
TIMEOUT = 15.0

mcp = FastMCP(
    "TokenAPI Scan",
)


async def _api_get(path: str) -> dict[str, Any] | None:
    """Make a GET request to the TokenAPI Scan API."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                f"{API_BASE}{path}",
                headers={"User-Agent": "tokenscan-mcp/0.1.0", "Accept": "application/json"},
            )
            if resp.status_code == 200:
                return resp.json()
        return None
    except Exception:
        return None


def _format_trust(trust: dict[str, Any] | None, name: str) -> str:
    """Format trust data into a readable string."""
    if not trust:
        return f"No verification data found for '{name}'."

    verified = trust.get("verified", "unknown")
    rate = trust.get("success_rate")
    rate_str = f"{rate * 100:.1f}%" if rate is not None else "N/A"
    tests = trust.get("detection_count") or trust.get("total_tests") or 0
    latest = trust.get("latest_detection", "unknown")
    latest_str = latest[:10] if latest and latest != "unknown" else "unknown"

    level_icon = {"high": "✅", "medium": "⚠️", "low": "❌"}.get(verified, "❓")

    return (
        f"{level_icon} Trust Level: **{verified}**\n"
        f"   Success Rate: {rate_str} ({tests} tests)\n"
        f"   Last Tested: {latest_str}"
    )


@mcp.tool(
    name="verify_relay",
    description="Check if an AI API relay/proxy service is verified. Returns trust level (high/medium/low), success rate, and last test time.",
)
async def verify_relay(relay_id: str) -> str:
    """Verify an AI API relay service by its ID or domain name.

    Args:
        relay_id: The relay provider ID or domain (e.g., 'openrouter', 'gptgod', 'deepseek')
    """
    # Try trust endpoint first
    data = await _api_get(f"/api/trust/providers?ids={relay_id}")
    if data and data.get("status") == "ok":
        providers = data.get("providers", {})
        pid = relay_id.lower()
        if pid in providers:
            entry = providers[pid]
            trust = entry.get("trust", {})
            provider = entry.get("provider", {})
            name = provider.get("name", relay_id)
            status = provider.get("service_status", "unknown")
            out = _format_trust(trust, name)
            out += f"\n   Service Status: {status}"
            return out

    # Fallback: search providers list
    data = await _api_get(f"/api/providers?q={relay_id}&limit=5")
    if data and data.get("status") == "ok":
        providers = data.get("providers", [])
        if providers:
            exact = [p for p in providers if p["name"].lower() == relay_id.lower()]
            if exact:
                p = exact[0]
                return _format_trust(p.get("trust"), p["name"])
            # Show close matches
            lines = [f"No exact match for '{relay_id}'. Did you mean one of these?"]
            for p in providers[:5]:
                t = p.get("trust", {})
                lines.append(f"  - {p['name']} (trust: {t.get('verified','?')})")
            return "\n".join(lines)

    return f"No data found for '{relay_id}'. The provider may not be in our database yet."


@mcp.tool(
    name="search_relays",
    description="Search for AI API relay/proxy services by name or keyword. Returns matching providers and their trust status.",
)
async def search_relays(query: str) -> str:
    """Search for relay providers by name or keyword.

    Args:
        query: Search keyword (e.g., 'claude', 'openai', 'deepseek', 'gpt')
    """
    data = await _api_get(f"/api/providers?q={query}&limit=20")
    if not data or data.get("status") != "ok":
        return f"Search failed or no results for '{query}'."

    providers = data.get("providers", [])
    if not providers:
        return f"No relays found matching '{query}'."

    lines = [f"Found {len(providers)} relay(s) matching '{query}':"]
    for p in providers:
        t = p.get("trust", {})
        verified = t.get("verified", "?")
        rate = t.get("success_rate")
        rate_str = f"{rate*100:.1f}%" if rate else "N/A"
        lines.append(
            f"  - {p['name']}: {verified} ({rate_str}, {t.get('total_tests',0)} tests)"
        )
    return "\n".join(lines)


@mcp.tool(
    name="relay_details",
    description="Get detailed verification data for a specific relay provider, including trust metrics, status, region, and category.",
)
async def relay_details(relay_id: str) -> str:
    """Get detailed verification data for a relay provider.

    Args:
        relay_id: The relay provider ID or domain (e.g., 'openrouter', 'gptgod')
    """
    data = await _api_get(f"/api/trust/providers?ids={relay_id}")
    if data and data.get("status") == "ok":
        providers = data.get("providers", {})
        pid = relay_id.lower()
        if pid in providers:
            entry = providers[pid]
            return json.dumps(entry, indent=2, ensure_ascii=False)

    # Fallback to providers list
    data = await _api_get(f"/api/providers?q={relay_id}&limit=1")
    if data and data.get("status") == "ok":
        providers = data.get("providers", [])
        exact = [p for p in providers if p["name"].lower() == relay_id.lower()]
        if exact:
            return json.dumps(exact[0], indent=2, ensure_ascii=False)

    return f"No detailed data found for '{relay_id}'."


def main() -> None:
    """Run the MCP server over stdio (for Claude Code integration)."""
    mcp.run()


if __name__ == "__main__":
    main()
