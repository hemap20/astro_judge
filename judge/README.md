# First-chat judge

Scores each user's FIRST consultation (from the first "Consultation started"
to the next one) in Low/ Medium/ High/ against the rubric doc.

## Setup (once)
    export GEMINI_API_KEY=...        # .venv already has google-genai + pandas

## Run
    .venv/bin/python judge/run_judge.py --version v1 --limit 10   # small calibration sample per tier
    .venv/bin/python judge/run_judge.py --version v1              # everything (resumes; done chats are skipped)
    .venv/bin/python judge/compare.py v1                          # tier table
    .venv/bin/python judge/compare.py v1 v2                       # + how versions differ

Use `--limit` with the same number across versions: the sample is fixed (seed 42),
so v1 and v2 score the same chats.

## Calibrating
1. Copy judge/prompts/v1.py to v2.py and edit the PROMPT string in v2.py. Never edit a prompt that has
   been run: the runner refuses, so old scores stay valid.
2. Run v2, then open results/v2/raw/<tier>/<chat>.json to read the judge's
   reasoning and quotes next to the transcript.
3. Counted rubrics (1.3, 4.1, 4.3) and the overall formula are in judge/metrics.py.
   Changing them affects every version on re-run, so note the change.

## Outputs (results/<version>/)
- prompt.py, meta.json: exact prompt and model used
- raw/<tier>/<chat>.json: judge output, quotes, counted metrics, token usage
- scores.csv: one row per chat (overall, bucket means B1-B5, each rubric, gate fails)
- tier_summary.csv: mean per tier, High-Low gap, rank correlation with LTV

## Choices not in the doc
- Overall = mean of bucket means; skipped rubrics and an untriggered Bucket 5 are left out;
  capped at 3 when any gate fails.
- First chats with fewer than 2 astrologer messages and 10 or fewer messages in total are marked too_short and not judged (45 chats).
- 1.3 uses the judge's per-message labels (question / reading); the script does the counting.
- 4.3 ignores lines under 4 words when counting repeats.
