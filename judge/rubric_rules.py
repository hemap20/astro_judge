"""Scoring reference: turns the judge's yes/no checks into rubric scores (v5+).

The judge answers fixed checks for the rubrics it was least consistent on; these
functions apply the rubric doc's tables to those answers, so the same answers
always give the same score. Each function returns None when the rubric is skipped.
"""
import re

BARE_ACK_RE = re.compile(
    r"^\s*(ji+|ok+|okay|okk+|hmm+|hm+|haan+|ha+|theek hai|thik hai|thik h|theek h|acha+|accha+|achha+)"
    r"\s*(ji)?\s*[.!🙏👍]*\s*$", re.I)


def _b(c, k):
    return bool((c or {}).get(k))


def _i(c, k):
    try:
        return int((c or {}).get(k) or 0)
    except (TypeError, ValueError):
        return 0


def r1_2(c):
    qs = (c or {}).get("questions") or []
    types = [str(q.get("type", "")).upper()[:1] for q in qs if isinstance(q, dict)]
    n = len(types)
    if n == 0:
        return None
    a, b, cc = types.count("A"), types.count("B"), types.count("C")
    used = [bool(q.get("answer_used")) for q in qs if isinstance(q, dict) and str(q.get("type", "")).upper()[:1] == "A"]
    if cc > n / 2:
        return 1
    if cc >= 2:
        return 3
    if cc == 1:
        return 4
    if b > n / 2:
        return 6
    if a == n:
        if used and all(used):
            return 10
        if any(used):
            return 9
        return 8
    return 7


def r1_4(c):
    if not _b(c, "about_specific_person"):
        return None
    if _b(c, "user_did_not_know_details") and _b(c, "asked_with_reason"):
        return 7
    if not _b(c, "asked") and not _b(c, "details_used"):
        return 1
    if _b(c, "demand_at_start_before_question"):
        return 3
    if not _b(c, "asked_with_reason"):
        return 4
    if _b(c, "asked_three_plus_times") or not _b(c, "details_used"):
        return 6
    if _b(c, "reading_about_person") and _b(c, "tied_to_user_question"):
        return 10
    if _b(c, "reading_about_person"):
        return 9
    if _b(c, "name_used_after"):
        return 8
    return 7


def r2_1(c):
    if not _b(c, "has_reading"):
        return 1
    if not _b(c, "new"):
        return 3
    if not _b(c, "now"):
        return 4
    if not _b(c, "specific"):
        return 6
    if _b(c, "reason") and _b(c, "concrete_marker"):
        return 10 if _i(c, "strong_statements") >= 2 else 9
    if _b(c, "reason"):
        return 8
    return 7


def r2_2(c):
    if not _b(c, "user_asked_question"):
        return None
    if not _b(c, "answered"):
        return 1 if _b(c, "reply_is_pitch_or_remedy") else 3
    if not _b(c, "gives_direction"):
        return 4
    if _b(c, "user_had_to_repeat"):
        return 6
    if _b(c, "counter_question_before_answer"):
        return 7
    if _b(c, "reason_given") and _b(c, "says_what_it_depends_on_or_next"):
        return 10
    if _b(c, "reason_given"):
        return 9
    return 8


def r2_7(c):
    if not _b(c, "user_asked_second_question"):
        return None
    if not _b(c, "first_answered_after_switch"):
        return 1
    if _b(c, "all_partial_in_one_message"):
        return 3
    if _b(c, "returned_only_when_user_asked"):
        return 4
    if not _b(c, "order_stated"):
        return 6
    if _b(c, "both_fully_answered") and _b(c, "returned_without_reminder"):
        return 10 if _b(c, "two_answers_connected") else 9
    if _b(c, "returned_without_reminder"):
        return 8
    return 7


def bare_ack_stats(msgs):
    """Count bare acknowledgements among astrologer messages and the longest run of them."""
    astro = [m for m in msgs if m["role"] == "ASTRO"]
    total = run = longest = 0
    for m in astro:
        if BARE_ACK_RE.match(m["text"]):
            total += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return total, longest


def r3_2(c, msgs):
    total, longest = bare_ack_stats(msgs)
    if _b(c, "early_goodbye_while_time_left"):
        return 1, total, longest
    if _b(c, "user_thanks_answered_with_goodbye"):
        return 3, total, longest
    if longest >= 3:
        return 4, total, longest
    if longest == 2:
        return 6, total, longest
    if total == 1:
        return 7, total, longest
    if not _b(c, "every_reply_after_first_reading_has_content"):
        return 8, total, longest
    if _b(c, "user_thanks_met_with_new_point"):
        return 10, total, longest
    return 9, total, longest


def r4_2(c):
    if _b(c, "replies_in_other_language"):
        return 1
    u, f = _i(c, "unexplained_terms"), _i(c, "formal_sentences")
    if u >= 5 or _b(c, "most_messages_formal"):
        return 3
    if u >= 3 or f >= 3:
        return 4
    if u >= 1 or f >= 1:
        return 6
    if not _b(c, "every_term_explained"):
        return 7
    reuse = _i(c, "user_word_reuse_count")
    if reuse >= 3:
        return 10
    if reuse >= 1:
        return 9
    return 8


RULES = {"1.2": r1_2, "1.4": r1_4, "2.1": r2_1, "2.2": r2_2, "2.7": r2_7, "4.2": r4_2}


def apply(judge, msgs):
    """Return {rubric_id: score or None} for the reference-scored rubrics, plus 3.2 details."""
    rub = judge.get("rubrics") or {}
    # 2.2 counter-question: worked out from message numbers, not left to the judge
    c22 = (rub.get("2.2") or {}).get("checks")
    mq = judge.get("main_question_idx")
    if isinstance(c22, dict) and isinstance(mq, int) and isinstance(c22.get("answer_idx"), int):
        qs = {int(l["idx"]) for l in judge.get("message_labels") or []
              if isinstance(l, dict) and l.get("q") and str(l.get("idx", "")).lstrip("-").isdigit()}
        c22["judge_counter_question"] = c22.get("counter_question_before_answer")
        c22["counter_question_before_answer"] = any(mq < i < c22["answer_idx"] for i in qs)
    out = {}
    for rid, fn in RULES.items():
        out[rid] = fn((rub.get(rid) or {}).get("checks") or {})
    s32, acks, longest = r3_2((rub.get("3.2") or {}).get("checks") or {}, msgs)
    out["3.2"] = s32
    return out, {"bare_acks": acks, "longest_ack_run": longest}
