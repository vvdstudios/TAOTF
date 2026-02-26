"""
TAOTF Pipeline — raw wishes → structured aspiration signals.
By Vivid Studio (https://vividstudio.me)
"""
import os, json, re, time, asyncio, csv
from datetime import datetime
import pandas as pd
from taotf_llm import get_llm_client, get_model_name
from taotf_schema import normalize_signal

INPUT_FILE     = "wishes.xlsx"
OUTPUT_JSONL   = "taotf_signals.jsonl"   # written live
OUTPUT_EXCEL   = "taotf_signals.xlsx"    # written at end
MODEL          = get_model_name()
BATCH_SIZE     = 15   # smaller = faster per request; more parallel batches
CONCURRENCY    = 25   # more in-flight requests for higher throughput
MAX_TOKENS     = 4096 # cap response to avoid long tail latency

PILLAR_EMOJI = {
    "Health & Longevity":       "🏥",
    "Home & Living":            "🏠",
    "Education & Knowledge":    "📚",
    "Energy & Sustainability":  "⚡",
    "Space & Exploration":      "🚀",
    "Nation & Society":         "🌍",
    "Environment & Planet":     "🌿",
    "Human Connection":         "❤️",
    "Digital Identity":         "💻",
    "Human-AI Collaboration":   "🤖",
}
VALENCE_EMOJI = {
    "hope": "✨", "longing": "💭", "urgency": "⚡",
    "gratitude": "🙏", "grief": "😔", "joy": "😊", "neutral": "➖"
}

SYSTEM_PROMPT = """You are an expert cultural analyst for the TAOTF (The Archive of the Future) project.
Extract structured aspiration signals from human wishes collected at Omnia Experience Center, Sohar, Oman.
Wishes may be in Arabic, English, or mixed. Process natively.

For each wish return a JSON object with:
- wish_id: string (provided)
- translated: English translation if Arabic/mixed, null if already English
- quality: "valid" or "noise" (noise = gibberish, spam, URLs, <3 real chars)
- primary_pillar: one of the 10 TAOTF pillars
- secondary_pillars: array (can be empty)
- primary_pillar_confidence: float 0-1
- signal_type: one of the 5 types
- beneficiary: "self" | "family" | "community" | "humanity" | "unknown"
- emotional_valence: "hope" | "longing" | "urgency" | "gratitude" | "grief" | "joy" | "neutral"
- urgency_score: float 0-1
- time_horizon: "immediate" | "near_term" | "long_term" | "unspecified"
- key_themes: array of 1-3 short English strings

PILLARS: Health & Longevity | Home & Living | Education & Knowledge | Energy & Sustainability |
         Space & Exploration | Nation & Society | Environment & Planet | Human Connection |
         Digital Identity | Human-AI Collaboration

SIGNAL TYPES: protective_aspiration | access_aspiration | transformation_aspiration |
              connection_aspiration | self_directed_aspiration

Return ONLY a valid JSON array. No markdown, no extra text."""

def pre_filter(text):
    text = str(text).strip()
    if re.search(r'https?://', text): return False
    if len(re.sub(r'[^a-zA-Z\u0600-\u06FF]', '', text)) < 3: return False
    return True

# ── Global state ──────────────────────────────────────────────────────────────
processed   = 0
valid_count = 0
noise_count = 0
error_count = 0
pillar_tally = {}
write_lock  = asyncio.Lock()
print_lock  = asyncio.Lock()
start_time  = None

def format_elapsed():
    s = int(time.time() - start_time)
    return f"{s//60:02d}:{s%60:02d}"

def truncate(text, n=55):
    text = str(text)
    return text[:n] + "…" if len(text) > n else text

def _print_one_signal(signal, raw_text):
    """Print one signal (call only while holding print_lock)."""
    global processed, valid_count, noise_count, error_count
    processed += 1
    quality = signal.get("quality", "error")

    if quality == "noise":
        noise_count += 1
        print(f"  \033[90m[{processed:04d}] 🚫 NOISE   {truncate(raw_text, 60)}\033[0m")
    elif quality == "error":
        error_count += 1
        print(f"  \033[31m[{processed:04d}] ❌ ERROR   {signal.get('error','?')[:60]}\033[0m")
    else:
        valid_count += 1
        pillar   = signal.get("primary_pillar", "Unknown")
        conf     = signal.get("primary_pillar_confidence", 0)
        valence  = signal.get("emotional_valence", "neutral")
        sig_type = signal.get("signal_type", "")
        themes   = ", ".join(signal.get("key_themes") or [])
        trans    = signal.get("translated") or raw_text
        emoji_p  = PILLAR_EMOJI.get(pillar, "📌")
        emoji_v  = VALENCE_EMOJI.get(valence, "➖")
        pillar_tally[pillar] = pillar_tally.get(pillar, 0) + 1
        bar_len  = 10
        filled   = int(conf * bar_len)
        conf_bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\033[0m  [{processed:04d}] {emoji_p} \033[1m{pillar:<26}\033[0m "
              f"\033[36m{conf_bar}\033[0m {conf:.2f}  "
              f"{emoji_v} \033[35m{valence:<10}\033[0m  "
              f"\033[33m{sig_type[:20]:<20}\033[0m")
        print(f"         \033[90m↳ {truncate(trans, 70)}\033[0m")
        if themes:
            print(f"         \033[90m  themes: {themes}\033[0m")
    if processed % 10 == 0:
        rate = processed / max(1, time.time() - start_time)
        print(f"\n  \033[32m── {processed} done │ {valid_count} valid │ "
              f"{noise_count} noise │ {error_count} err │ "
              f"{rate:.1f}/s │ {format_elapsed()} ──\033[0m\n")

async def print_batch(signals, wish_map):
    """Print all signals in batch under one lock."""
    async with print_lock:
        for s in signals:
            wid = str(s.get("wish_id", ""))
            _print_one_signal(s, wish_map.get(wid, ""))

async def write_batch(fh, signals, wish_map):
    """Write all signals to JSONL under one lock."""
    async with write_lock:
        now = datetime.utcnow().isoformat()
        for s in signals:
            wid = str(s.get("wish_id", ""))
            s["_raw_text"] = wish_map.get(wid, "")
            s["_written_at"] = now
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
        fh.flush()

async def process_batch(client, batch, semaphore, fh):
    async with semaphore:
        wish_map = {str(w["id"]): str(w["wish_text"]) for w in batch}
        payload  = json.dumps(
            [{"wish_id": w["id"], "wish_text": str(w["wish_text"])} for w in batch],
            ensure_ascii=False
        )

        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": payload}
                    ],
                    temperature=0.1,
                    max_tokens=MAX_TOKENS,
                    timeout=90,
                )
                raw = resp.choices[0].message.content.strip()
                raw = re.sub(r'^```[a-z]*\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    parsed = list(parsed.values())[0]

                # Normalize taxonomy fields to canonical values
                parsed = [normalize_signal(s) for s in parsed]

                # Print + write whole batch (one lock each)
                await asyncio.gather(
                    print_batch(parsed, wish_map),
                    write_batch(fh, parsed, wish_map)
                )
                return parsed

            except Exception as e:
                if attempt == 2:
                    err_signals = [{"wish_id": w["id"], "quality": "error", "error": str(e)} for w in batch]
                    err_map = {str(w["id"]): str(w["wish_text"]) for w in batch}
                    await asyncio.gather(
                        print_batch(err_signals, err_map),
                        write_batch(fh, err_signals, err_map)
                    )
                    return []
                await asyncio.sleep(2 ** attempt)

async def build_excel(df):
    """Read the JSONL and build final Excel"""
    print("\n\033[1mBuilding Excel report...\033[0m")
    signals = []
    with open(OUTPUT_JSONL) as f:
        for line in f:
            try: signals.append(json.loads(line))
            except: pass

    signals_df = pd.DataFrame(signals)
    if "_raw_text" in signals_df.columns:
        signals_df = signals_df.drop(columns=["_raw_text", "_written_at"], errors="ignore")
    signals_df = signals_df.rename(columns={"wish_id": "id"})

    result = df.merge(signals_df, on="id", how="left")

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        result.to_excel(writer, sheet_name="All Signals", index=False)

        if "quality" in result.columns:
            valid_out = result[result["quality"] == "valid"]
            valid_out.to_excel(writer, sheet_name="Valid Signals", index=False)

            if "primary_pillar" in valid_out.columns:
                ps = valid_out["primary_pillar"].value_counts().reset_index()
                ps.columns = ["pillar", "count"]
                ps["pct"] = (ps["count"] / len(valid_out) * 100).round(1)
                ps.to_excel(writer, sheet_name="Pillar Summary", index=False)

                st = valid_out["signal_type"].value_counts().reset_index()
                st.columns = ["signal_type", "count"]
                st.to_excel(writer, sheet_name="Signal Types", index=False)

                be = valid_out["beneficiary"].value_counts().reset_index()
                be.columns = ["beneficiary", "count"]
                be.to_excel(writer, sheet_name="Beneficiary", index=False)

                from collections import Counter
                all_themes = []
                for t in valid_out["key_themes"].dropna():
                    if isinstance(t, list): all_themes.extend(t)
                    elif isinstance(t, str):
                        try: all_themes.extend(json.loads(t))
                        except: pass
                if all_themes:
                    th = pd.DataFrame(Counter(all_themes).most_common(100), columns=["theme","count"])
                    th.to_excel(writer, sheet_name="Top Themes", index=False)

    print(f"\033[32m✅ Excel saved → {OUTPUT_EXCEL}\033[0m")

async def run():
    global start_time

    client = get_llm_client()

    print("\033[1m\n🌟 TAOTF Pipeline — Real-Time Processing\033[0m")
    print(f"   Model: {MODEL}  │  Batch: {BATCH_SIZE}  │  Concurrency: {CONCURRENCY}")
    print(f"   Output (live): {OUTPUT_JSONL}")
    print(f"   Output (final): {OUTPUT_EXCEL}\n")

    df = pd.read_excel(INPUT_FILE)
    df["pre_filter"] = df["wish_text"].apply(pre_filter)
    valid_df = df[df["pre_filter"]].copy()

    print(f"   Total wishes: {len(df)}")
    print(f"   Will process: {len(valid_df)}")
    print(f"   Pre-filtered: {len(df)-len(valid_df)} (noise/spam)\n")
    print("─" * 80)

    records = valid_df[["id", "wish_text"]].to_dict("records")

    # Resume: skip already-processed wish IDs
    processed_ids = set()
    if os.path.isfile(OUTPUT_JSONL):
        try:
            with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        wid = obj.get("wish_id")
                        if wid is not None:
                            processed_ids.add(str(wid))
                    except Exception:
                        pass
        except Exception:
            pass
        if processed_ids:
            n_before = len(records)
            records = [r for r in records if str(r["id"]) not in processed_ids]
            print(f"   \033[33mResume: skipping {len(processed_ids)} already done │ {len(records)} left\033[0m\n")

    batches   = [records[i:i+BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    semaphore = asyncio.Semaphore(CONCURRENCY)
    start_time = time.time()

    file_mode = "a" if processed_ids else "w"
    with open(OUTPUT_JSONL, file_mode, encoding="utf-8") as fh:
        tasks = [process_batch(client, b, semaphore, fh) for b in batches]
        await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    print("\n" + "─" * 80)
    print(f"\033[1m✅ Complete in {elapsed:.1f}s\033[0m")
    print(f"   Valid: {valid_count}  │  Noise: {noise_count}  │  Errors: {error_count}")
    print(f"\n   Top Pillars:")
    for p, c in sorted(pillar_tally.items(), key=lambda x: -x[1])[:5]:
        bar = "█" * int(c / max(pillar_tally.values()) * 20)
        print(f"   {PILLAR_EMOJI.get(p,'📌')} {p:<30} {bar} {c}")

    await build_excel(df)

if __name__ == "__main__":
    asyncio.run(run())