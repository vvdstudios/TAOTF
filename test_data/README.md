# TAOTF test data — real vs unreal

*By [Vivid Studio](https://vividstudio.me).*

- **real_from_middle.jsonl** — 15 valid signals taken from the middle of `taotf_signals.jsonl` (human aspirations).
- **unreal_agent.jsonl** — 15 synthetic “agent” signals with a skewed distribution (Digital Identity / Human-AI Collaboration / Space, beneficiary mostly “humanity”, valence all “neutral”).

## Run comparison (ADI script)

From project root:

```bash
# Real (middle) vs unreal
python scripts/aspiration_divergence.py --human test_data/real_from_middle.jsonl --agent test_data/unreal_agent.jsonl -o test_data/report_real_vs_unreal.json

# Full human archive vs unreal
python scripts/aspiration_divergence.py --human taotf_signals.jsonl --agent test_data/unreal_agent.jsonl -o test_data/report_full_vs_unreal.json
```

## Expected results

- **Real vs unreal:** Aspiration Alignment Score ~0.42 (clearly divergent; emotional_valence divergence = 1.0 because humans are hope-dominant, agent is all neutral).
- **Full archive vs unreal:** Score ~0.29 (even more divergent from full human distribution).

Reports are written to `report_real_vs_unreal.json` and `report_full_vs_unreal.json`.

## API compare

With the API running (`uvicorn api:app --port 8000`):

```bash
curl -X POST http://localhost:8000/v1/compare -H "Content-Type: application/json" -d @test_data/compare_payload.json
```

`compare_payload.json` is the same 15 unreal signals in the API request format.
