"""Counted rubrics (1.3, 4.1, 4.3) and the overall score.

Thresholds follow the rubric doc. They are "starting values" in the doc, so
they live here as constants you can tune.
"""
import re

LONG_WORDS = 30
VERY_LONG_WORDS = 60
FIRST_MIN_SEC = 5 * 60
BURST_LEN = 4
MIN_REP_WORDS = 4  # a line needs this many words to count as a repeat in 4.3
LIST_RE = re.compile(r"^\s*(\d+[.)]|[-*•])\s+", re.M)
WAIT_LINE_RE = re.compile(r"kundli dekh", re.I)

BUCKETS = {
    "B1": ["1.1", "1.2", "1.3", "1.4"],
    "B2": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"],
    "B3": ["3.1", "3.2", "3.3"],
    "B4": ["4.1", "4.2", "4.3"],
    "B5": ["5.1"],
}


def _words(t):
    return t.split()


def astro_msgs(msgs):
    return [m for m in msgs if m["role"] == "ASTRO" and m["text"] != "[empty / media]"]


# ---------- 1.3 Gets to the reading (uses the judge's per-message labels) ----------
def score_1_3(msgs, labels):
    """labels: {idx: {"q": bool, "r": bool}} for astro messages."""
    seq = []  # 'Q' / 'R' in order
    for m in astro_msgs(msgs):
        lab = labels.get(m["idx"], {})
        if lab.get("r"):
            seq.append("R")
        if lab.get("q"):
            seq.append("Q")
    T = seq.count("Q")
    if "R" not in seq:
        return {"score": 1, "Q": T, "R": None, "T": T}
    Q = seq[: seq.index("R")].count("Q")
    R = run = 0
    for s in seq:
        run = run + 1 if s == "Q" else 0
        R = max(R, run)
    if Q >= 5:
        s = 3
    elif Q == 4 or R >= 3:
        s = 4
    elif Q == 3:
        s = 6
    elif Q <= 1 and T <= 3 and R <= 1:
        s = 10
    elif T <= 3:
        s = 9
    elif T == 4:
        s = 8
    else:
        s = 7
    return {"score": s, "Q": Q, "R": R, "T": T}


# ---------- 4.1 Message shape ----------
def score_4_1(msgs):
    am = astro_msgs(msgs)
    if not am:
        return {"score": None}
    lens = [len(_words(m["text"])) for m in am]
    n = len(lens)
    long_frac = sum(l > LONG_WORDS for l in lens) / n
    M = sum(m["sec"] < FIRST_MIN_SEC for m in am)
    bursts, run = 0, 0
    for m in msgs:
        if m["role"] == "ASTRO":
            run += 1
            if run == BURST_LEN:
                bursts += 1
        elif m["role"] == "USER":
            run = 0
    has_list = any(LIST_RE.search(m["text"]) for m in am)
    avg = sum(lens) / n
    if long_frac > 0.5 or has_list:
        s = 1
    elif long_frac >= 0.25 or M > 24 or M < 5:
        s = 3
    elif max(lens) > VERY_LONG_WORDS or 21 <= M <= 24:
        s = 4
    elif long_frac >= 0.10 or 17 <= M <= 20 or 5 <= M <= 7 or bursts >= 2:
        s = 6
    elif max(lens) <= 25 and 10 <= M <= 14 and bursts == 0:
        s = 10 if avg <= 15 else 9
    elif long_frac == 0 and 8 <= M <= 16 and bursts <= 1:
        s = 8
    else:
        s = 7
    return {"score": s, "M": M, "long_frac": round(long_frac, 3), "max_words": max(lens),
            "avg_words": round(avg, 1), "bursts": bursts, "has_list": has_list}


# ---------- 4.3 Not repetitive ----------
def _near_dup(a, b):
    wa, wb = a.lower().split(), b.lower().split()
    # very short lines ("ok", "ji", "hmm") are acknowledgements, scored by 3.2, not repeats
    if min(len(wa), len(wb)) < MIN_REP_WORDS or abs(len(wa) - len(wb)) > 2:
        return False
    if len(wa) == len(wb):
        return sum(x != y for x, y in zip(wa, wb)) <= 2
    short, long_ = sorted([wa, wb], key=len)
    return len(set(long_) - set(short)) <= 2 and len(set(short) - set(long_)) == 0


def score_4_3(msgs):
    am = [m["text"] for m in astro_msgs(msgs)]
    if not am:
        return {"score": None}
    rep, wait_used = 0, False
    for i, t in enumerate(am):
        if any(_near_dup(t, p) for p in am[:i]):
            if WAIT_LINE_RE.search(t) and not wait_used:
                wait_used = True
                continue
            rep += 1
    openers = {}
    for t in am:
        w = t.lower().split()
        if len(w) >= 2:
            k = " ".join(w[:2])
            openers[k] = openers.get(k, 0) + 1
    top = max(openers.values(), default=0)
    if rep >= 6:
        s = 1
    elif rep >= 4:
        s = 3
    elif rep == 3:
        s = 4
    elif rep == 2 or top >= 4:
        s = 6
    elif rep == 1:
        s = 7
    elif top >= 3:
        s = 8
    elif top == 2:
        s = 9
    else:
        s = 10
    return {"score": s, "Rep": rep, "top_opener_count": top}


# ---------- overall ----------
def overall(scores: dict, gate_failed: bool):
    """Mean of bucket means (skipped rubrics and an untriggered Bucket 5 are left
    out); capped at 3 when any gate check fails."""
    bucket_means = {}
    for b, ids in BUCKETS.items():
        vals = [scores[i] for i in ids if scores.get(i) is not None]
        bucket_means[b] = round(sum(vals) / len(vals), 2) if vals else None
    present = [v for v in bucket_means.values() if v is not None]
    uncapped = round(sum(present) / len(present), 2) if present else None
    ov = min(uncapped, 3.0) if (uncapped is not None and gate_failed) else uncapped
    return ov, bucket_means, uncapped


# ---------- blueprint ("Chat flow- ai astro.md") ----------
STAGES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
# milestone deadlines in seconds, from the doc's adaptive timing table (end of each stage's window)
#                 initial prediction (S4), personalised prediction (S6), remedy (S8)
MILESTONES = {5: {"S4": 90, "S6": 210, "S8": 255},
              10: {"S4": 150, "S6": 360, "S8": 510},
              15: {"S4": 210, "S6": 540, "S8": 780}}
W_COVERAGE, W_MILESTONES, W_ORDER = 0.6, 0.3, 0.1


def chat_length_bucket(duration_sec):
    """Which column of the adaptive timing table to use (5, 10 or 15 minutes)."""
    if duration_sec <= 7.5 * 60:
        return 5
    if duration_sec <= 12.5 * 60:
        return 10
    return 15


def blueprint_score(bp: dict, msgs: list):
    """bp: judge output {S1: {present, idx, quality}, ...}. Returns a 1-10 score and parts."""
    if not bp:
        return {"score": None}
    sec = {m["idx"]: m["sec"] for m in msgs}
    duration = max((m["sec"] for m in msgs), default=0)
    bucket = chat_length_bucket(duration)

    q = {}
    first_sec = {}
    for s in STAGES:
        st = bp.get(s) or {}
        try:
            qual = int(st.get("quality") or 0)
        except (TypeError, ValueError):
            qual = 0
        qual = max(0, min(2, qual)) if st.get("present") else 0
        q[s] = qual
        try:
            idx = int(st["idx"]) if st.get("idx") is not None else None
        except (TypeError, ValueError):
            idx = None
        if qual > 0 and idx in sec:
            first_sec[s] = sec[idx]
    coverage = sum(q.values()) / (2 * len(STAGES))

    # milestone met = stage present and first reached by the deadline; half credit if late
    ms = {}
    for s, deadline in MILESTONES[bucket].items():
        if s not in first_sec:
            ms[s] = 0.0
        else:
            ms[s] = 1.0 if first_sec[s] <= deadline else 0.5
    milestones = sum(ms.values()) / len(ms)

    # order: share of present-stage pairs that appear in blueprint order
    seq = [s for s in STAGES if s in first_sec]
    pairs = [(a, b) for i, a in enumerate(seq) for b in seq[i + 1:]]
    order = (sum(first_sec[a] <= first_sec[b] for a, b in pairs) / len(pairs)) if pairs else 0.0

    pct = W_COVERAGE * coverage + W_MILESTONES * milestones + W_ORDER * order
    return {"score": round(1 + 9 * pct, 2), "coverage": round(coverage, 3),
            "milestones": {k: v for k, v in ms.items()}, "order": round(order, 3),
            "length_bucket_min": bucket, "stage_quality": q,
            "stage_sec": first_sec}


# ---------- final score and label ----------
W_RUBRIC, W_BLUEPRINT = 0.5, 0.5
GATE_PENALTY = {"G1": 4.0, "G2": 3.0, "G3": 1.5, "G3a": 1.5, "G3b": 3.0, "G4": 2.0}  # G3 = v4 and earlier   # points off the final score (1-10)
GOOD_MIN = 6.5    # fixed thresholds: final >= this -> "good" (stored as label_fixed)
BAD_MAX = 4.5     # final <= this -> "bad"; in between -> "mixed"
# relative label written to scores.csv "label": share of judged chats in each version
GOOD_TOP_SHARE = 0.25   # top 25% of final scores -> "good"
BAD_BOTTOM_SHARE = 0.25  # bottom 25% -> "bad"


def final_score(rubric_uncapped, blueprint, gate_fails):
    parts = [(W_RUBRIC, rubric_uncapped), (W_BLUEPRINT, blueprint)]
    parts = [(w, v) for w, v in parts if v is not None]
    if not parts:
        return None, None
    base = sum(w * v for w, v in parts) / sum(w for w, _ in parts)
    penalty = sum(GATE_PENALTY.get(g, 0) for g in gate_fails)
    final = round(max(1.0, base - penalty), 2)
    label = "good" if final >= GOOD_MIN else "bad" if final <= BAD_MAX else "mixed"
    return final, label


def relative_labels(finals):
    """finals: list of final scores (None allowed). Top GOOD_TOP_SHARE -> good,
    bottom BAD_BOTTOM_SHARE -> bad, rest mixed."""
    vals = sorted(v for v in finals if v is not None)
    if not vals:
        return [None] * len(finals)
    def q(p):
        return vals[min(len(vals) - 1, max(0, int(round(p * (len(vals) - 1)))))]
    hi, lo = q(1 - GOOD_TOP_SHARE), q(BAD_BOTTOM_SHARE)
    return [None if v is None else "good" if v >= hi else "bad" if v <= lo else "mixed" for v in finals]
