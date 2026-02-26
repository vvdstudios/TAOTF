# TAOTF Agent Verification — Dynamic Probes & Closed-Box Evaluation

This document describes how TAOTF is used to **check agent behavior** using dynamic probes and distributional comparison. The system is designed to be dynamic and scalable, though it has known limitations.

---

## Goals

1. **Check agent behavior** using aspiration signals: does the agent's stated intention resemble human-like aspiration?
2. **Dynamic** — the probe (question) changes so it can't be memorized or optimized for a fixed prompt.
3. **Closed-box evaluation** — the API returns only verified/not-verified + message, without exposing scores or thresholds. Note: the scoring logic (JS divergence, threshold) is in the open-source code, so agents with source access can study it.
4. **MCP server** — humans (and agents) can safely check up on an agent before dealing with it; agent-to-agent verification is supported.

---

## What is public vs. server-side

| What is public / in source code | What is server-side at runtime |
|----------------------------------|-------------------------------|
| Probe **templates** (many variants) | **Which** probe is chosen for this session (seed-dependent) |
| Scoring formula (JS divergence) and threshold default (0.35) | **Exact reference distribution** (loaded from TAOTF data file) |
| That we compare pillar/valence/beneficiary/type | **Runtime threshold** (configurable via env var) |
| GET /v1/probe returns a prompt | **Tagged response** (how the response maps to taxonomy) |

**Honest assessment:** An agent with access to the source code *can* study the scoring formula and threshold. The main defense is that passing requires consistently producing human-like aspiration across many dynamic probes, which is the intended behavior. This is a distributional similarity check, not a cryptographic proof.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│  Human / Agent  │     │  TAOTF Verification (server-side)                │
│  (verifier)     │     │                                                  │
│                 │     │  - Probe generator (deterministic from seed)      │
│  1. get_probe   │────>│  - Reference: human signals (loaded at runtime)  │
│     (dynamic Q) │     │  - Tag response (LLM, server-side)              │
│                 │     │  - Compare to reference → score                  │
│  2. send Q to   │     │  - Apply threshold → verified: true/false       │
│     agent under │     │  - Return { verified, message, disclaimer }      │
│     test        │     │                                                  │
│                 │     └──────────────────────────────────────────────────┘
│  3. verify      │
│     (response)  │────>  No score or distribution in response.
└─────────────────┘
```

---

## Dynamic probes

- **Templates:** A set of prompt templates (e.g. "What do you wish for [X]?") with placeholders.
- **Seed:** Each verification session uses a **seed**. From the seed we derive which template and which placeholder values to use.
- The question is different for each seed. We can add more templates over time.

---

## Verification flow (human or agent-to-agent)

1. **Verifier** calls **get_probe(seed)** → receives `{ probe_id, prompt }`.
2. Verifier sends **prompt** to the **agent under test**.
3. Verifier collects the agent's **response** (raw text).
4. Verifier calls **verify(response)** → server tags response, compares to reference, returns `{ verified, message, disclaimer }`.
5. Verifier uses the result to decide whether to trust or engage.

---

## MCP server for safe checkups

- **get_probe** — Returns a dynamic probe.
- **verify_agent** — Sends response text; returns verified + message.
- Humans or agents use an MCP client to call these tools.

---

## Limitations

- **Single response:** One response per probe. For stronger assurance, run multiple probes and require k-of-n to pass.
- **Stated vs behavior:** We measure **stated** aspiration similarity, not behavior. An agent can say human-like things without acting human-like.
- **Open scoring:** The scoring formula and default threshold are in the source code. An agent that studies the code could potentially learn to game it.
- **Language/model:** Tagging quality depends on the LLM model. Reference data is primarily Arabic/English from Omnia Experience Centers.
- **Not a security mechanism:** This is a distributional similarity check, not an authentication or safety proof.

---

## How to run

1. **API** (must run first):
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000
   ```
   Set LLM backend (see `.env.example`). Load `taotf_signals.jsonl` (use `/v1/reload` after updating).

2. **MCP server**:
   ```bash
   pip install fastmcp
   python mcp_server.py
   ```

3. **Flow:** Call `get_probe(seed?)` → get `prompt` → send to agent → call `verify_agent(response_text, seed)` → get result.

---

*By [Vivid Studio](https://vividstudio.me). See [EXAMPLES.md](EXAMPLES.md) for probe + verify examples.*
