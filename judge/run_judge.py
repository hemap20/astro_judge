"""Score first chats with a Gemini judge.

  python judge/run_judge.py --version v1                 # all tiers, all chats
  python judge/run_judge.py --version v2 --limit 10      # 10 chats per tier, for calibration
  python judge/run_judge.py --version v1 --tiers High --files conversation_123_45.csv

Prompt:  judge/prompts/<version>.py (a PROMPT string)
Output:  results/<version>/
           prompt.py        frozen copy of the prompt used
           meta.json        model, prompt hash, run settings
           raw/<tier>/<chat>.json   full judge output + counted metrics
           scores.csv       one row per chat (rebuilt after every run)
Re-running a version only scores chats that are not done yet. If the prompt
file changed since the version was first run, the run stops: save the change
as a new version (v2.py, ...) so old scores stay comparable.
"""
import argparse
import concurrent.futures as cf
import csv
import glob
import hashlib
import importlib.util
import shutil
import json
import os
import random
import sys
import time

from google import genai
from google.genai import types

sys.path.insert(0, os.path.dirname(__file__))
from chat_parser import load_first_chat, render_transcript, user_id_from_path  # noqa: E402
import metrics  # noqa: E402
import rubric_rules  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS = ["Low", "Medium", "High"]
LTV_CSV = os.path.join(ROOT, "18339637_2026_11_12.csv")
JUDGED = ["1.1", "1.2", "1.4", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7",
          "3.1", "3.2", "3.3", "4.2", "5.1"]
ALL_RUBRICS = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
               "2.7", "3.1", "3.2", "3.3", "4.1", "4.2", "4.3", "5.1"]
ALLOWED = {1, 3, 4, 6, 7, 8, 9, 10}
MIN_ASTRO_MSGS = 2   # too_short = fewer astro messages than this...
MAX_SHORT_MSGS = 10  # ...and no more than this many messages in total


def load_ltv():
    with open(LTV_CSV) as f:
        return {r["user_id"]: r for r in csv.DictReader(f)}


def call_judge(client, model, system_prompt, transcript, temperature, retries=5):
    cfg = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        seed=42,
        response_mime_type="application/json",
    )
    last = None
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model, contents="TRANSCRIPT:\n" + transcript, config=cfg)
            text = resp.text.strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            usage = resp.usage_metadata
            return json.loads(text), {
                "input_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None)}
        except Exception as e:  # rate limits, bad JSON, timeouts
            last = e
            time.sleep(min(60, 2 ** attempt + random.random()))
    raise RuntimeError(f"judge failed after {retries} tries: {last}")


def clean_score(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return v if v in ALLOWED else None


def judge_one(path, tier, client, args, system_prompt, out_dir, ltv):
    out_path = os.path.join(out_dir, "raw", tier, os.path.basename(path) + ".json")
    if os.path.exists(out_path):
        return "skip"
    msgs = load_first_chat(path)
    rec = {"file": os.path.basename(path), "tier": tier, "user_id": user_id_from_path(path),
           "ltv": float(ltv.get(user_id_from_path(path), {}).get("ltv") or 0),
           "n_msgs": len(msgs), "n_astro_msgs": len(metrics.astro_msgs(msgs))}
    if rec["n_astro_msgs"] < MIN_ASTRO_MSGS and rec["n_msgs"] <= MAX_SHORT_MSGS:
        rec["status"] = "too_short"
    else:
        judge, usage = call_judge(client, args.model, system_prompt,
                                  render_transcript(msgs), args.temperature)
        labels = {int(l["idx"]): l for l in judge.get("message_labels", []) if "idx" in l}
        scores = {}
        for rid in JUDGED:
            r = (judge.get("rubrics") or {}).get(rid) or {}
            scores[rid] = None if r.get("skipped") else clean_score(r.get("score"))
        c13, c41, c43 = metrics.score_1_3(msgs, labels), metrics.score_4_1(msgs), metrics.score_4_3(msgs)
        scores.update({"1.3": c13["score"], "4.1": c41["score"], "4.3": c43["score"]})
        gate = judge.get("gate") or {}
        g3 = gate.get("G3") or {}
        ref_details = None
        if args.schema >= 5:
            # scoring reference: checks -> scores by rule; the judge's own number is kept for comparison
            ref_scores, ref_details = rubric_rules.apply(judge, msgs)
            ref_details["judge_own_scores"] = {rid: scores.get(rid) for rid in ref_scores}
            scores.update(ref_scores)
            # G3 fails when a paid element is named; G3b when fear/urgency/guarantee comes with it
            g3["fail"] = bool(g3.get("paid_idx"))
            g3["severity"] = ("G3b" if g3.get("fear_idx") else "G3a") if g3["fail"] else None
        # v3 (prompts with the blueprint) ask for fear_idx and paid_idx; missing counts as empty
        if args.schema < 5 and g3.get("fail") and ("blueprint" in judge or "fear_idx" in g3 or "paid_idx" in g3) \
                and not (g3.get("fear_idx") and g3.get("paid_idx")):
            g3["fail"] = False  # v3+: G3 needs both a fear message and a paid message
            g3["overridden"] = "fear_idx or paid_idx empty"
        gate_fails = [g for g in ("G1", "G2", "G3", "G4") if (gate.get(g) or {}).get("fail")]
        if args.schema >= 5 and "G3" in gate_fails:
            gate_fails[gate_fails.index("G3")] = g3["severity"]
        ov, buckets, rubric_uncapped = metrics.overall(scores, bool(gate_fails))
        bp = metrics.blueprint_score(judge.get("blueprint"), msgs)
        final, label = (metrics.final_score(rubric_uncapped, bp["score"], gate_fails)
                        if bp["score"] is not None else (None, None))
        rec.update(status="ok", scores=scores, gate_fails=gate_fails, overall=ov,
                   rubric_score=rubric_uncapped, blueprint=bp, final=final, label=label,
                   buckets=buckets, counted={"1.3": c13, "4.1": c41, "4.3": c43},
                   judge=judge, usage=usage, reference=ref_details)
        add_gate_translations(rec, client, args.model, msgs)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return rec["status"]


TRANSLATE_PROMPT = (
    "Translate each chat line below into natural English. The lines come from an astrology "
    "chat and may be in Hindi, Hinglish, Telugu, Tamil, Bengali or another language, written "
    "in any script. Keep names and astrology terms (Shani, dasha, kundli, pooja) as they are. "
    "If a line is already English, return it unchanged. Keep any '#12 [01:05] ASTRO:' prefix "
    "and line breaks exactly, translating only the message text. Return ONLY a JSON object mapping each "
    "key to its translation, e.g. {\"G3\": \"...\"}.\n\n")


def gate_quote(g_out, msgs):
    """Full text of the messages the judge pointed to (v2+: evidence_idx), else its quote (v1)."""
    idx = []
    for key in ("fear_idx", "paid_idx", "evidence_idx"):
        v = g_out.get(key) or []
        idx += v if isinstance(v, list) else [v]
    try:
        idx = sorted({int(i) for i in idx})
    except (TypeError, ValueError):
        pass
    by_idx = {m["idx"]: m for m in msgs or []}
    lines = []
    for i in idx:
        try:
            m = by_idx.get(int(i))
        except (TypeError, ValueError):
            m = None
        if m:
            mm, ss = divmod(m["sec"], 60)
            lines.append(f"#{m['idx']} [{mm:02d}:{ss:02d}] {m['role']}: {m['text']}")
    return "\n".join(lines) if lines else (g_out.get("quote") or "")


def add_gate_translations(rec, client, model, msgs=None):
    """For each failed gate check, store the full flagged messages and their English
    translation in rec["gate_evidence"]. Returns True when rec was changed."""
    if rec.get("status") != "ok" or not rec.get("gate_fails") or "gate_evidence" in rec:
        return False
    gate = (rec.get("judge") or {}).get("gate") or {}
    ev = {g: {"quote": gate_quote(gate.get(g[:2]) or {}, msgs),
              "reason": (gate.get(g[:2]) or {}).get("reason") or ""} for g in rec["gate_fails"]}
    to_tr = {g: e["quote"] for g, e in ev.items() if e["quote"].strip()}
    tr = {}
    if to_tr:
        cfg = types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json")
        for attempt in range(4):
            try:
                resp = client.models.generate_content(
                    model=model, contents=TRANSLATE_PROMPT + json.dumps(to_tr, ensure_ascii=False),
                    config=cfg)
                tr = json.loads(resp.text.strip().strip("`").removeprefix("json").strip())
                break
            except Exception:
                time.sleep(2 ** attempt + random.random())
    for g, e in ev.items():
        e["quote_en"] = tr.get(g) if e["quote"].strip() else None
    rec["gate_evidence"] = ev
    return True


def backfill_gate_translations(out_dir, client, model, workers):
    """Add translations to chats judged before this step existed."""
    def one(p):
        with open(p) as f:
            rec = json.load(f)
        if add_gate_translations(rec, client, model):
            with open(p, "w") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
            return 1
        return 0
    paths = glob.glob(os.path.join(out_dir, "raw", "*", "*.json"))
    with cf.ThreadPoolExecutor(workers) as ex:
        n = sum(ex.map(one, paths))
    if n:
        print(f"added English translations of gate-fail quotes to {n} earlier chats")


def rebuild_scores_csv(out_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(out_dir, "raw", "*", "*.json"))):
        with open(p) as f:
            r = json.load(f)
        row = {k: r.get(k) for k in ("tier", "file", "user_id", "ltv", "status", "n_msgs", "n_astro_msgs")}
        row["final"] = r.get("final")
        row["label"] = None  # relative label, filled in below
        row["label_fixed"] = r.get("label")
        row["rubric_score"] = r.get("rubric_score")
        row["blueprint"] = (r.get("blueprint") or {}).get("score")
        row["ideal_pct"] = round((row["blueprint"] - 1) / 9 * 100, 1) if row["blueprint"] is not None else None
        row["overall"] = r.get("overall")
        row["gate_fail"] = ",".join(r.get("gate_fails", [])) if r.get("status") == "ok" else None
        ev = r.get("gate_evidence") or {}
        row["gate_fail_quote"] = " | ".join(f"{g}: {e['quote']}" for g, e in ev.items()) or None
        row["gate_fail_quote_en"] = " | ".join(f"{g}: {e.get('quote_en') or ''}" for g, e in ev.items()) or None
        row["gate_fail_reason"] = " | ".join(f"{g}: {e['reason']}" for g, e in ev.items()) or None
        for b, v in (r.get("buckets") or {}).items():
            row[b] = v
        for rid in ALL_RUBRICS:
            row["r" + rid] = (r.get("scores") or {}).get(rid)
        row["trigger"] = (r.get("judge") or {}).get("difficult_user_trigger")
        bp = r.get("blueprint") or {}
        for s, qv in (bp.get("stage_quality") or {}).items():
            row[s] = qv
        for s, v in (bp.get("milestones") or {}).items():
            row[f"on_time_{s}"] = v
        if bp.get("length_bucket_min"):
            row["length_bucket_min"] = bp["length_bucket_min"]
        rows.append(row)
    for row, lab in zip(rows, metrics.relative_labels([row["final"] for row in rows])):
        row["label"] = lab
    if any(row["final"] is not None for row in rows):
        for row in rows:
            if row["status"] == "too_short":
                row["label"] = "bad_no_service"
    if rows:
        cols = list(dict.fromkeys(k for r in rows for k in r))
        with open(os.path.join(out_dir, "scores.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="prompt name, e.g. v1 -> judge/prompts/v1.py")
    ap.add_argument("--model", default="gemini-3.1-flash-lite")
    ap.add_argument("--tiers", nargs="+", default=TIERS)
    ap.add_argument("--limit", type=int, help="max chats per tier (same sample every time)")
    ap.add_argument("--files", nargs="+", help="only these chat file names")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    prompt_path = os.path.join(ROOT, "judge", "prompts", args.version + ".py")
    spec = importlib.util.spec_from_file_location(f"prompt_{args.version}", prompt_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    system_prompt = mod.PROMPT.strip()
    args.schema = getattr(mod, "SCHEMA", 1)
    phash = hashlib.sha256(system_prompt.encode()).hexdigest()[:12]

    out_dir = os.path.join(ROOT, "results", args.version)
    meta_path = os.path.join(out_dir, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        if meta["prompt_hash"] != phash or meta["model"] != args.model:
            sys.exit(f"{args.version} was run with a different prompt or model. "
                     f"Save your edit as a new version (e.g. judge/prompts/v{len(glob.glob(os.path.join(ROOT, 'judge/prompts/v*.py'))) + 1}.py).")
    else:
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(prompt_path, os.path.join(out_dir, "prompt.py"))
        with open(meta_path, "w") as f:
            json.dump({"version": args.version, "model": args.model, "prompt_hash": phash,
                       "temperature": args.temperature,
                       "created": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=1)

    jobs = []
    for tier in args.tiers:
        files = sorted(glob.glob(os.path.join(ROOT, tier, "*conversation_*.csv")))
        if args.files:
            files = [p for p in files if os.path.basename(p) in set(args.files)]
        if args.limit:
            files = random.Random(42).sample(files, min(args.limit, len(files)))
        jobs += [(p, tier) for p in files]

    client = genai.Client()  # reads GEMINI_API_KEY
    ltv = load_ltv()
    counts = {}
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(judge_one, p, t, client, args, system_prompt, out_dir, ltv): p for p, t in jobs}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            try:
                st = fut.result()
            except Exception as e:
                st = "error"
                print(f"  ERROR {os.path.basename(futs[fut])}: {e}")
            counts[st] = counts.get(st, 0) + 1
            if i % 10 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} {counts}")
    backfill_gate_translations(out_dir, client, args.model, args.workers)
    n = rebuild_scores_csv(out_dir)
    print(f"done. {n} chats in {os.path.relpath(out_dir, ROOT)}/scores.csv  "
          f"-> next: python judge/compare.py {args.version}")


if __name__ == "__main__":
    main()
