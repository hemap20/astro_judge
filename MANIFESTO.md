# Astro Chat Judge: Manifesto

The full history and context of this project: what was built, why, every decision, every result and what is still open. Use it as the starting point for the next iteration.

Last updated: 2026-11-16 (after v5 and the Confluence write-up).

Confluence (published summary of the same work), folder "Astro Chat Judge LLM" in space ARL:
- Overview: https://getlokalapp.atlassian.net/wiki/spaces/ARL/pages/1902969040
- Rubrics explained: https://getlokalapp.atlassian.net/wiki/spaces/ARL/pages/1903001817
- Ideal conversation flow: https://getlokalapp.atlassian.net/wiki/spaces/ARL/pages/1903067411
- Results by version: https://getlokalapp.atlassian.net/wiki/spaces/ARL/pages/1903100138
- Technical reference: https://getlokalapp.atlassian.net/wiki/spaces/ARL/pages/1903100156

---

## 1. Goal

Build an LLM judge that scores the FIRST chat between a user and a (human) astrologer on AstroLokal, in order to:
1. Learn what a good first chat looks like, as input for an AI astrologer.
2. Compare first chats of Low, Medium and High LTV users, to see whether the rubrics differ between them.
3. Eventually split each LTV group into "good" and "bad" chats. The definition of good/bad is still open (see section 9).

Requirements set along the way:
- The judge model is **gemini-3.1-flash-lite** (not the `-preview` name).
- The prompt will be edited many times to calibrate the judge; **every version's scores must be saved separately**.
- Prompts are kept as **.py files**, not .md.
- Cumulative scores per LTV tier must be easy to compare.
- **G3 (pressure to pay) is a violation and must never be ignored**, including polite requests to extend time.
- Gate failures must **reduce** the final score.
- When a gate fails, save the **full** flagged messages with an **English translation**.
- Score the **full** first chat (not only the first 5 minutes). One judge run per chat is enough.
- Scoring must be **consistent** (hence the scoring reference in v5).
- Show **how close a chat is to the ideal conversation as a percentage**.

---

## 2. Source documents

| File | Role |
|---|---|
| `AI Astro First-Chat Rubric Framework ( For supply review).md` | The rubric framework: 4 gates, 5 buckets, 18 rubrics, score tables. Embedded in full in every prompt |
| `Chat flow- ai astro.md` | The ideal conversation flow ("blueprint"): 9 stages, 5-minute timeline, 3 milestones, adaptive timing table, hook library, behaviour rules. Embedded in full from v3 |
| `18339637_2026_11_12.csv` | LTV of all users: `user_id,name,ltv,paid_orders,chats_done,total_consults`. 323 users; LTV from 100 up to about 1.2M |

### Rubric framework in brief
- Scores: only 1, 3, 4, 6, 7, 8, 9, 10 (bands Low 1/3, Medium 4/6, Good 7/8, Excellent 9/10).
- Order: skip check → Low rules first → highest fully-true rule from 10 down → every yes needs a quote.
- Gates (pass/fail): G1 crisis handling, G2 honest identity, G3 no harm or pressure, G4 no made-up facts.
- Bucket 1 Understanding the user: 1.1 acknowledges, 1.2 questions fit, 1.3 gets to the reading (counted), 1.4 other person's details.
- Bucket 2 Prediction quality: 2.1 relatable reading, 2.2 answers the main question, 2.3 chart reason in plain words, 2.4 builds depth, 2.5 timing and consistency, 2.6 guidance fits, 2.7 holds the main thread.
- Bucket 3 Curiosity and momentum: 3.1 opens a next layer, 3.2 no early close, 3.3 ending at the wall.
- Bucket 4 Human feel: 4.1 message shape (counted), 4.2 easy language, 4.3 not repetitive (counted).
- Bucket 5 Difficult user (only when triggered): 5.1 adapts to the user.

### Blueprint in brief
Stages S1 greeting & rapport, S2 validate feelings, S3 understand the concern, S4 initial prediction, S5 relevant follow-up, S6 personalised prediction, S7 second layer, S8 remedy / practical guidance, S9 hook / next consultation.
Milestones (5-minute chat): initial prediction by 1:30, personalised prediction by 3:30, remedy by 4:15. The doc has a 5/10/15-minute timing table for longer chats.

---

## 3. Data preparation (what happened, in order)

### 3.1 Original folder contents
Each source folder had a `<folder>_users.csv` (columns `Sender ID,Sender Name`) and a folder of chat files:

| Folder | Files at start |
|---|---|
| bad | 43 |
| good | 65 |
| high_tt_pair_chats | 50 |
| medium | 39 |
| medium_2 | 134 |
| sitara(6 nov onw.) | 107 (no `_users.csv`) |

Chat file name: `conversation_<userID>_<astrologerID>.csv`; columns `Date,Time,Sender Name,Sender ID,Message`; rows newest first. Each file holds ALL consultations between one user and one astrologer; each consultation starts with a system message "Consultation started for #<id>" (Sender ID 0, Sender Name "Astrolokal").

### 3.2 Tiering
- Tiers by LTV: **Low 100–500, Medium 500–5,000, High 5,000–50,000**. Boundaries: Low `100 <= ltv < 500`, Medium `500 <= ltv < 5000`, High `5000 <= ltv`.
- 16 files of users with LTV above 50,000 were first left out, then **added to High** at the user's request.
- Files were **copied, not moved**. Exact duplicate files across source folders were kept once (93 skipped). A same-name file with different content would be prefixed `<folder>__` (none happened).
- 107 files from `sitara(6 nov onw.)` were **left out**: those users are not in the LTV file (its minimum LTV is 100, so they may be below that).
- Tier user lists: `Low_users.csv`, `Medium_users.csv`, `High_users.csv` (rows from the LTV file).

### 3.3 Incident: case-insensitive folders
macOS folder names are not case-sensitive. Creating `Medium/` wrote into the existing `medium/` folder, and writing `Medium_users.csv` **overwrote the original `medium_users.csv`** (the list of 39 medium users is lost; no backup found).
Fix (user's choice): rename the mixed folder to `medium_old_mixed/` and rebuild `Medium/` from `medium_old_mixed`, `medium_2` and `sitara`, filtering by LTV 500–5,000.
**Lesson: never create folders or files whose names differ only by case.**

### 3.4 Incident: emptied folders
`bad/`, `good/` and `high_tt_pair_chats/` were found empty at 13:05 on 2026-11-13, after our last script finished at 13:03; our scripts only copied. Cause unknown (not this work). A `bad.zip` exists in the user's Downloads. Their tier-relevant files had already been copied into the tier folders.

### 3.5 Final dataset
| Tier | Files | Users | Judged in v5 | Too short |
|---|---|---|---|---|
| Low | 35 | 35 | 28 | 7 |
| Medium | 177 | 175 | 154 | 23 |
| High | 119 | 113 | 104 | 15 |
| Total | 331 | 323 | 286 | 45 |

Facts about the data:
- **Every user–astrologer pair has 5+ consultations.** No user here dropped the astrologer after the first chat, so there are no true "bad outcome" cases.
- First-chat length: median about 11 minutes; 162 chats fall in the 5-minute bucket, 51 in 10-minute, 73 in 15-minute (v5).
- First chats often run straight into a second consultation within minutes (median gap 7 min Low, 19 min High).
- 116 distinct astrologers; the largest has 17 chats (astrologer 347).
- Languages: Hindi, Hinglish, Telugu, Tamil, Bengali, English and others.

---

## 4. Code map

```
judge_llm_astro/
  MANIFESTO.md                 this file
  .env                         GEMINI_API_KEY (never share or commit)
  .venv/                       Python 3.9 venv with google-genai, pandas (system pydantic is too old)
  judge/
    run_judge.py               runs one version; resumable; writes results/<version>/
    compare.py                 tier tables, cross-version table, outcome check
    chat_parser.py             first-chat extraction and transcript rendering
    metrics.py                 counted rubrics, overall, blueprint, final, labels, ALL constants
    rubric_rules.py            v5 scoring reference: judge checks -> rubric scores
    outcomes.py                what the user did after the first chat
    prompts/v1.py … v5.py      PROMPT string per version (v5 also SCHEMA = 5)
    GLOSSARY.md                definitions of every term and column
    README.md                  quick start
  results/<version>/
    prompt.py, meta.json       frozen prompt and settings
    raw/<tier>/<chat>.json     full judge output per chat
    scores.csv                 one row per chat
    tier_summary.csv           per-metric tier averages, High-Low, rho_ltv
    outcome_check.csv          labels vs outcomes (v3+)
  results/comparison.csv       last multi-version compare
```

### Running
```bash
cd judge_llm_astro
set -a; source .env; set +a
.venv/bin/python judge/run_judge.py --version v5 --limit 10   # same 10 chats per tier every time (seed 42)
.venv/bin/python judge/run_judge.py --version v5              # all chats; resumes
.venv/bin/python judge/compare.py v4 v5
```
Options: `--model` (default gemini-3.1-flash-lite), `--tiers`, `--files`, `--workers 8`, `--temperature 0`.

### Pipeline behaviour
1. Prompt module loaded from `judge/prompts/<version>.py` (`PROMPT`, optional `SCHEMA`).
2. First chat = rows from the first "Consultation started" to the next one (file reversed, stable sort by timestamp). Roles: Sender ID 0 = SYSTEM; the user ID from the file name = USER; else ASTRO. Transcript lines: `#<idx> [mm:ss] ROLE: text`. Empty messages become `[empty / media]`.
3. **too_short**: fewer than 2 astrologer messages AND 10 or fewer messages in total. Not judged. (Originally "fewer than 2 astrologer messages"; changed so one 18-message chat would be judged.)
4. Gemini call: system prompt = PROMPT, user content = transcript, JSON output, temperature 0, seed 42 (added in v5), 5 retries with backoff. About 10k input + 1.3k output tokens per chat.
5. Scores computed (section 6); gate evidence translated by a second Gemini call; raw JSON saved; `scores.csv` rebuilt with relative labels.
6. Versioning guard: if `results/<version>/meta.json` exists with a different prompt hash or model, the run stops ("save as a new version"). Changes to `metrics.py` / `rubric_rules.py` are NOT covered by the hash; final scores are stored at judge time, so old versions keep the formula they ran with, but `scores.csv` columns derived at rebuild (relative label, ideal_pct) use current code when rebuilt.

---

## 5. Versions: what changed, results, learnings

Tier sizes for all versions: Low 28, Medium 154, High 103–104 judged.

### v1: rubric doc as written (2026-11-13)
- Prompt: judging instructions + JSON output spec + the full rubric doc. The judge scores 15 rubrics; 1.3/4.1/4.3 are counted by script (1.3 uses the judge's per-message labels q = question, r = reading).
- Overall = mean of bucket means (B5 only if triggered), **capped at 3** on any gate failure.
- Results: overall 4.91 / 4.82 / 5.06 (High−Low +0.15); rubric score without cap 5.21 / 5.12 / 5.73 (+0.51); gate fail 14.3 / 22.7 / 33.0%; G3 flags 4 / 34 / 34 (72). 285 judged (1 chat kept returning broken JSON).
- Learned: the cap hides tier differences; best separating rubrics 2.7 (+1.91), 1.4 (+1.33), 1.1 (+1.15), 2.4 (+1.00); Bucket 4 does not separate; 2.5 timing points the wrong way (Low 6.85, High 5.51) because High-LTV astrologers state timing more firmly; Bucket 5 triggered in only 6 chats.
- Additions during v1: too_short rule change; **gate evidence + English translation** saved by a pipeline step (`gate_fail_quote`, `gate_fail_quote_en`, `gate_fail_reason`), backfilled into v1.
- User feedback: G3 quotes showed "fear and urgency used to push a paid service" without any payment; show the full quote.

### v2: G3 needs a paid element (2026-11-13)
- G3 = fear/urgency/guarantee + paid element (pooja for money, product, price, payment, extending/recharging the chat). Naming an illness and predicting a baby's gender **removed from G3**. Gate evidence as message numbers (`evidence_idx`) → the pipeline pulls full messages verbatim, with time and role.
- Results: overall 5.08 / 4.81 / 5.46 (+0.38); rubric 5.33 / 5.25 / 5.83 (+0.51); gate fail 17.9 / 26.0 / 24.0%; G3 5 / 37 / 24 (66).
- Learned: High-tier gate failures dropped 33% → 24%; ~20 of 66 G3 flags still doubtful (payment without fear, or fear without payment); mind-control promises (Mohini mantra, "brainwash") and black-magic claims are common in High-tier chats.

### v3: blueprint, final score, labels (2026-11-13)
- Judge marks the 9 blueprint stages: present, first message idx, quality 0/1/2 (0 also when done through fear or a paid pitch).
- Blueprint score = 1 + 9 × (0.6 coverage + 0.3 milestones + 0.1 order). Milestones: S4/S6/S8 by the deadline of the chat's length bucket (≤7.5 min → 5-minute column, ≤12.5 → 10, else 15); on time 1, late 0.5, missing 0.
- Final = 0.5 rubric score (no cap) + 0.5 blueprint − gate penalties (G1 4, G2 3, G3 3, G4 2), floor 1. **Penalties replace the cap.**
- Labels fixed: good ≥ 6.5, bad ≤ 4.5.
- G3 must name `fear_idx` and `paid_idx`; script passes G3 if either is empty.
- Results: final 3.59 / 3.43 / 3.79 (+0.20); rubric 4.73 / 4.80 / 4.97 (+0.24); closeness to ideal 27.9 / 28.2 / 34.5% (+6.6 pts); gate fail 21.4 / 28.6 / 28.8%; G3 6 / 41 / 30 (77); good 0 / 2.6 / 7.7%, bad 57.1 / 66.9 / 60.6%.
- Learned: the blueprint separates tiers better than the rubrics; separating stages S7 (rho 0.30 with LTV), S2 (0.21), S9; S8 remedy and S9 hook rare everywhere; only 2–10% reach the remedy milestone on time; all gate-fail chats labelled bad; the G3 override only fired 4 times; thresholds too high (median final 3.94).

### v4: explicit paid element, relative labels (2026-11-13)
- Paid element = exactly one of: (1) price/amount/fee/payment/dakshina; (2) request to extend/add time, recharge, reconnect, join again, or move to a (video) call; (3) astrologer or a pandit they arrange offers to PERFORM a pooja/jaap/healing/ritual/spell/"process". NOT paid: self-done remedies (mantra incl. Mohini, fasting, donating, diya, wallpaper), vague "upay karna hoga", photo/details/rating requests, "manage your time", a guaranteed prediction alone.
- G3 penalty 3 → **1.5**. Labels **relative**: top 25% good, bottom 25% bad (`label`); fixed thresholds kept as `label_fixed`.
- Bug fixes: G3 with missing fear/paid fields now passes; gate evidence includes fear_idx and paid_idx messages (no more empty quotes).
- Results: final 3.83 / 3.71 / 3.86 (+0.03); rubric 4.80 / 4.80 / 4.87 (+0.07); closeness 28.6 / 28.8 / 33.4% (+4.8); gate fail 21.4 / 31.8 / 37.5%; G3 6 / 46 / 37 (89); good 28.6 / 22.1 / 28.8%, bad 17.9 / 25.3 / 26.9%.
- Learned: the explicit list made G3 broader (89 flags, ~80% with a clear paid element, mostly polite "time badhaiye"); final no longer separates tiers; 60 of 72 bad chats have a gate failure.
- Diagnostics run before v5:
  - **Judge consistency** (v3 vs v4, identical rubric/blueprint prompt): rubric_score rho 0.89, blueprint rho 0.91; exact agreement per rubric: 1.2 0.49, 2.2 0.58, 2.7 0.58, 3.2 0.59, 1.4 0.60, 2.1 0.63, 4.2 0.63 … blueprint stages 0.86–0.97, counted 1.0. Causes seen: different main question picked; criteria bleeding between rubrics (2.2 marked down for a promise, which is 2.5's job); no structured checks.
  - **Length bias**: blueprint vs number of messages rho 0.5; good share 20% (5-min) / 27% (10-min) / 36% (15-min).
  - Only 20 of 89 G3 flags contained real fear words.
- User decisions: G3 stays a violation (polite extension requests included); score the full chat; run once; build a reference for consistency.

### v5: scoring reference, G3a/G3b, outcome check (2026-11-16)
- **G3 split** (both violations): G3 fails whenever `paid_idx` is non-empty; **G3b** if `fear_idx` is also non-empty (−3), else **G3a** (−1.5).
- **Scoring reference** (`judge/rubric_rules.py`): for 1.2, 1.4, 2.1, 2.2, 2.7, 3.2, 4.2 the judge fills a fixed `checks` object; the script applies the rubric table. Main question fixed once (`main_question_idx`). Prompt says: score each rubric only on its own rules. Script-computed: bare acknowledgements for 3.2 (regex on astro messages: ji/ok/hmm/theek hai/accha…), and 2.2's counter-question-before-answer (any astro question between main_question_idx and answer_idx). The judge's own numbers are kept in `reference.judge_own_scores`.
- Fixed seed 42. Too-short chats labelled `bad_no_service`. Outcome check added to compare.py. `ideal_pct` column added (closeness to ideal, 0–100%).
- Results: final 3.75 / 3.47 / 3.81 (+0.06); rubric 5.16 / 5.10 / 5.35 (+0.19); closeness 31.4 / 29.7 / 36.4% (+4.9); gate fail 35.7 / 43.5 / 45.2%; G3 10 / 65 / 47 (122 = 63 G3a + 59 G3b); good 32.1 / 19.5 / 31.7%, bad 17.9 / 24.7 / 27.9%.
- Outcome check (same astrologer):

| Label | Chats | Consultations | Within 7 days | Median minutes to return | First chat (median min) |
|---|---|---|---|---|---|
| good | 72 | 7.75 | 5.54 | 6.25 | 9.15 |
| mixed | 142 | 6.95 | 5.70 | 2.15 | 5.00 |
| bad | 72 | 8.49 | 6.81 | 4.80 | 7.00 |
| bad_no_service | 45 | 6.93 | 6.07 | 6.70 | 0.00 |

  Final vs consultations within 7 days: rho −0.21 overall (Low −0.47, Medium −0.20, High −0.23). By gate: none 5.49, G3a 6.11, G3b 7.02 consultations within 7 days. Low-quality + G3b chats: 7.71 (highest). High-quality + no gate (78 chats): 5.51 (average).
- Reference vs the judge's own number (same chat, same run): exact match 1.2 0.62, 2.7 0.59, 1.4 0.57, 2.1 0.57, 2.2 0.42, 3.2 0.19, 4.2 0.19.
- Closeness to ideal: mean 32%, median 30%, max 88%; 8 chats (3%) ≥ 70%. Top: `High/conversation_3385183_546.csv` 88%, `High/conversation_90605_2324.csv` 86%, `Medium/conversation_790870_2283.csv` 84% (all final > 8, no gate failure). Distribution: 0–10% 29, 10–20% 36, 20–30% 83, 30–40% 64, 40–50% 31, 50–60% 22, 60–70% 13, 70%+ 8.

### Trend
| Metric | v1 | v2 | v3 | v4 | v5 |
|---|---|---|---|---|---|
| Headline High−Low (overall v1–v2, final v3+) | +0.15 | +0.38 | +0.20 | +0.03 | +0.06 |
| Rubric score High−Low | +0.51 | +0.51 | +0.24 | +0.07 | +0.19 |
| Closeness to ideal High−Low | — | — | +6.6 | +4.8 | +4.9 |
| Gate fail %, High | 33.0 | 24.0 | 28.8 | 37.5 | 45.2 |
| G3 flags | 72 | 66 | 77 | 89 | 122 |

---

## 6. Current scoring model (v5) in full

| Item | Definition |
|---|---|
| Bucket averages B1–B5 | Mean of non-skipped rubric scores in the bucket |
| rubric_score | Mean of bucket averages (B5 only when triggered), no cap |
| overall | rubric_score capped at 3 on any gate failure (headline in v1–v2 only) |
| ideal_pct | 100 × (0.6 coverage + 0.3 milestones + 0.1 order) |
| blueprint | 1 + 9 × ideal_pct/100 |
| final | max(1, 0.5 rubric_score + 0.5 blueprint − Σ penalties) |
| Penalties | G1 4, G2 3, G3a 1.5, G3b 3, G4 2 (v3 G3 = 3, v4 G3 = 1.5) |
| label | top 25% final = good, bottom 25% = bad, else mixed; too_short = bad_no_service |
| label_fixed | good ≥ 6.5, bad ≤ 4.5 |

Counted rubrics (metrics.py): long message > 30 words, very long > 60, M = astro messages in the first 5 min, burst = 4 astro messages in a row, list/numbering detection; repeats need ≥ 4 words and ≤ 2 changed words; one "kundli dekh" wait line allowed.
Constants all live at the end of `judge/metrics.py` (GATE_PENALTY, W_*, MILESTONES, GOOD_TOP_SHARE, BAD_BOTTOM_SHARE, GOOD_MIN, BAD_MAX).

---

## 7. Decision log

| # | Decision | When | Reason |
|---|---|---|---|
| 1 | Tiers Low 100–500, Medium 500–5,000, High 5,000+; >50k added to High | Data | Compare by user value |
| 2 | Copy, don't move; keep exact duplicates once | Data | Keep sources intact |
| 3 | Leave out sitara users (no LTV) | Data | Can't tier them |
| 4 | Rebuild Medium after the case-insensitivity mix-up; old folder kept as medium_old_mixed | Data | Fix the merge |
| 5 | Score the first consultation only, in full | v1, confirmed v5 | Rubrics are first-chat rubrics; 5-min window declined |
| 6 | gemini-3.1-flash-lite, temperature 0, one run per chat | v1, confirmed v5 | Cost; 3 runs/median declined |
| 7 | Prompts as .py; separate results per version; ran prompts locked | v1 | Calibration history |
| 8 | 1.3, 4.1, 4.3 counted by script | v1 | Doc marks them counted |
| 9 | too_short = <2 astro messages AND ≤10 messages | v1 | Don't drop long chats |
| 10 | Save gate evidence with English translation | v1–v2 | Reviewability |
| 11 | G3 needs a paid element; illness/baby-gender out of G3 | v2 | Flags lacked payment |
| 12 | Blueprint added; final = 50/50 rubric + blueprint | v3 | Closeness to ideal |
| 13 | Gate penalties instead of cap | v3 | Failures should reduce, not flatten |
| 14 | Explicit paid-element list; self-done remedies excluded | v4 | Doubtful flags |
| 15 | Relative labels (25/25) | v4 | Fixed thresholds labelled most chats bad |
| 16 | G3 always a violation; G3a −1.5 / G3b −3 | v5 | User requirement; fear is worse |
| 17 | Scoring reference for 7 rubrics; fixed main question; seed | v5 | Consistency |
| 18 | bad_no_service label; outcome check | v5 | No-service chats are bad; validate labels |
| 19 | ideal_pct column | v5 | Readable closeness to ideal |
| 20 | Documentation in Confluence (5 pages) + this manifesto | After v5 | Shared reference and next-iteration baseline |

---

## 8. Key findings

1. First chats are far from the ideal: average 32% closeness; remedy (S8) and hook (S9) rare.
2. High-LTV first chats are closer to the ideal (+5 pts), driven by S7 second layer, S2 validating feelings, S9 hook.
3. High-LTV chats also fail G3 most (45% in v5), so the combined final score barely separates tiers.
4. **Chats scored bad lead to more repeat consultations.** Fear-for-payment (G3b) chats bring users back most. A good, compliant experience and good revenue currently point in opposite directions.
5. High-quality, compliant chats bring users back no more than average: something the rubrics do not capture drives return visits.
6. The judge is not fully consistent run to run on several rubrics; v5's reference changes those scores substantially; v5 consistency not yet measured.
7. Rubric 2.5 (timing) penalises the firm timelines High-LTV astrologers use.
8. Bucket 5 is triggered in only 2–6% of chats.

---

## 9. Open questions (for the next iteration)

1. **What does "good" mean?** A good, compliant experience, or a chat that brings the user back? Proposed: two separate numbers, a quality score (rubric + blueprint) and a compliance flag (gates), then outcomes per combination. Chats to copy = bring users back without a gate failure.
2. **Harm-only claims:** should mind-control promises (Mohini mantra, brainwash, "bring them back"), black-magic claims, illness claims and baby-gender predictions be their own gate, without any payment? (Removed from G3 in v2; pending.)
3. Rubric 2.5: keep or revise for firm timelines?
4. Measure v5 consistency: rerun ~50 chats once (~$0.30 estimated) and compare per rubric with v5.
5. Get first chats of users who **never returned** (true negatives); the current data has none.
6. Correct for chat length in the blueprint (e.g. per-length-bucket normalisation or scoring the first N minutes for milestones only).
7. More Low-tier chats (only 28 judged).
8. Keep each astrologer's chats on one side of any train/test split (clustering: 116 astrologers, largest 17 chats).
9. Retry the occasional chat that returns broken JSON (consider passing a response schema to Gemini).

---

## 10. Conventions and preferences to keep

- New prompt = copy the latest `judge/prompts/vN.py` to `vN+1.py`; never edit a prompt that has run. A raw string `r'''…'''` is used; don't put `'''` inside.
- Keep reporting results with the same fixed metric rows per version (final, rubric score, closeness to ideal, gate fail %, G3 flags, good/bad %) and a trend table, as on the Confluence results page.
- Percentages are rounded individually and may total 100.1% (e.g. Low 8/15/5 of 28).
- Use `.venv/bin/python`; load the key with `set -a; source .env; set +a`. Never print or share the key.
- The tier folders are copies; source folders are left untouched. Avoid names differing only by case.
- Update `judge/GLOSSARY.md` when adding columns or terms, the Confluence pages when results change, and this manifesto at the end of each iteration.
