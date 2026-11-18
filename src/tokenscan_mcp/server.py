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
VERSION = "0.2.0"

mcp = FastMCP(
    "TokenAPI Scan",
)


async def _api_get(path: str) -> dict[str, Any] | None:
    """Make a GET request to the TokenAPI Scan API."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                f"{API_BASE}{path}",
                headers={"User-Agent": f"tokenscan-mcp/{VERSION}", "Accept": "application/json"},
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


@mcp.tool(
    name="list_free_quotas",
    description="List free-tier token/credit offers published by AI model providers (Google Gemini, DeepSeek, Kimi, GLM, etc). Filterable by vendor or cadence. Verified daily by independent checks — never fabricated, expired offers are pulled from the list.",
)
async def list_free_quotas(vendor: str = "", cadence: str = "", limit: int = 15) -> str:
    """List verified free-quota offers from AI model providers.

    Args:
        vendor: Optional vendor filter (e.g. 'Google', 'DeepSeek', 'Kimi', 'GLM')
        cadence: Optional cadence filter ('onboarding', 'daily', 'monthly', ...)
        limit: Max entries to return (default 15, max 50)
    """
    data = await _api_get("/api/free-quota.json")
    if not data or not data.get("items"):
        return "Free-quota data unavailable right now. Try again later."
    items = data["items"]
    if vendor:
        items = [i for i in items if vendor.lower() in (i.get("vendor", "") + " " + i.get("title", "")).lower()]
    if cadence:
        items = [i for i in items if i.get("cadence", "").lower() == cadence.lower()]
    total = len(items)
    items = items[: min(max(limit, 1), 50)]
    lines = [f"Verified free-quota offers ({total} match, showing {len(items)}; dataset generated {data.get('generated_at', '?')[:10]}):"]
    for i in items:
        val = i.get("value_usd") or i.get("value_cny")
        val_str = f"~{val}" if val is not None else "value stated on page"
        claim = i.get("claim_url") or "see provider page"
        lines.append(
            f"  - [{i.get('vendor', '?')}] {i.get('title', '?')} | quota: {i.get('quota', '?')} | "
            f"cadence: {i.get('cadence', '?')} | value: {val_str} | verified: {i.get('verified_at', '?')} | claim: {claim}"
        )
    return "\n".join(lines)


@mcp.tool(
    name="get_relay_catalog",
    description="Query the CN relay-catalog data node: 240+ AI API relay providers with trust level (from cryptographic model-authenticity detection), price floor, region and category. Filterable by category or keyword.",
)
async def get_relay_catalog(category: str = "", query: str = "", limit: int = 20) -> str:
    """Query the relay-catalog dataset.

    Args:
        category: Optional category filter ('claude-relay', '候选中转', '中文服务区中转', ...)
        query: Optional keyword matched against name/provider_id/endpoint
        limit: Max entries to return (default 20, max 50)
    """
    data = await _api_get("/data/relay-catalog.json")
    if not data:
        return "Relay-catalog data unavailable right now. Try again later."
    entries = data.get("relays") or data.get("entries") or []
    if query:
        q = query.lower()
        entries = [e for e in entries if q in json.dumps(e, ensure_ascii=False).lower()]
    if category:
        entries = [e for e in entries if e.get("category", "").lower() == category.lower()]
    total = len(entries)
    entries = entries[: min(max(limit, 1), 50)]
    lines = [f"Relay catalog ({total} match, showing {len(entries)}):"]
    for e in entries:
        trust = (e.get("trust") or {}).get("verified", "?")
        floor = (e.get("prices") or {}).get("min_input_usd_per_1m")
        floor_str = f"${floor}/1M in" if floor is not None else "price N/A"
        lines.append(
            f"  - {e.get('name', '?')} [{e.get('category', '?')}] trust={trust} | {floor_str} | {e.get('endpoint', '')}"
        )
    return "\n".join(lines)


def main() -> None:
    """Run the MCP server over stdio (for Claude Code integration)."""
    mcp.run()


if __name__ == "__main__":
    main()
