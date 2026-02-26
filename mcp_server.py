"""
TAOTF Agent Verification — MCP server for safe agent checkups.

By Vivid Studio (https://vividstudio.me)

Exposes tools so humans or agents can:
1. get_probe — get a dynamic question (probe) to send to an agent under test
2. verify_agent — submit the agent's response and get verified (bool) + message only

The TAOTF API (with reference data and threshold) must be running. Set TAOTF_API_URL
if it is not at http://localhost:8000.

Run: python mcp_server.py
Or: fastmcp dev mcp_server.py
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = None  # optional

BASE_URL = os.environ.get("TAOTF_API_URL", "http://localhost:8000")


def _get_probe(seed: str = "") -> dict:
    url = f"{BASE_URL}/v1/probe"
    if seed:
        url += "?" + urlencode({"seed": seed})
    req = Request(url)
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _verify(response_text: str, seed: str | None = None) -> dict:
    url = f"{BASE_URL}/v1/verify"
    body = {"response_text": response_text}
    if seed:
        body["seed"] = seed
    req = Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


if FastMCP is not None:
    mcp = FastMCP(
        "TAOTF Agent Verification",
        description="Verify AI agents using dynamic aspiration probes. Get a probe, send it to the agent, submit the response to verify.",
    )

    @mcp.tool()
    def get_probe(seed: str = "") -> dict:
        """
        Get a dynamic verification probe (question) to send to an agent under test.
        The question changes with the seed so it cannot be memorized. Returns probe_id, prompt, and seed.
        Use the same seed when calling verify_agent so the session can be logged.
        """
        try:
            return _get_probe(seed)
        except (URLError, HTTPError) as e:
            return {"error": str(e), "hint": "Ensure TAOTF API is running (e.g. uvicorn api:app --port 8000)."}

    @mcp.tool()
    def verify_agent(response_text: str, seed: str = "") -> dict:
        """
        Submit an agent's response to a verification probe. Returns only verified (bool) and message.
        Use after get_probe: send the prompt to the agent, then pass the agent's reply here.
        Safe for agent-to-agent: one agent can verify another before cooperating.
        """
        try:
            return _verify(response_text, seed or None)
        except (URLError, HTTPError) as e:
            return {"error": str(e), "verified": False, "message": "Verification service unavailable."}


def main():
    if FastMCP is None:
        print("Install FastMCP to run the MCP server: pip install fastmcp")
        return
    mcp.run()


if __name__ == "__main__":
    main()
