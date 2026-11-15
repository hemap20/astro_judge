# Glossary: judge terms, rubrics and result columns

## Basic terms

| Term | Meaning |
|---|---|
| LTV | Lifetime value of the user, from `18339637_2026_11_12.csv` |
| Tier | LTV group: Low (100–500), Medium (500–5,000), High (5,000 and above) |
| First chat | The user's first consultation with that astrologer: everything from the first "Consultation started" message to the next one |
| Window | The part of the chat being scored, here the whole first chat |
| Version | One saved prompt (`judge/prompts/v1.py`, `v2.py`, ...). Each version's results are kept apart in `results/<version>/` |
| Judge | The Gemini model (`gemini-3.1-flash-lite`) that reads the chat and scores it against the rubrics |
| Reading | A message that tells the user something about their life, chart or question (not a greeting, wait line or data request) |
| Counted rubric | Scored by a script from counts in the transcript, not by the judge (1.3, 4.1, 4.3) |
| Skipped | The rubric does not apply to this chat (for example 1.4 when no other person is involved). Shown as an empty cell and left out of averages |

## Score scale

Only 1, 3, 4, 6, 7, 8, 9 and 10 can be given.

| Band | Scores | Meaning |
|---|---|---|
| Low | 1, 3 | Missing, or done in a way that hurts the chat |
| Medium | 4, 6 | Present, but generic, late or half done |
| Good | 7, 8 | What a competent astrologer does |
| Excellent | 9, 10 | What the best chats do |

## Gate (pass or fail)

If any check fails, the chat's overall score is capped at 3.

| Check | Fails when the astrologer... |
|---|---|
| G1 Crisis handling | continues a reading, gives a remedy or talks payment when the user mentions self-harm, or shares no helpline |
| G2 Honest identity | makes a false claim when asked if it is a person or an AI |
| G3 No harm or pressure | names an illness or promises a cure, uses fear, predicts a baby's gender, promises a result for payment, or invents urgency to sell |
| G4 No made-up facts | states an invented fact about the user's life, claims chart details without birth data, or gives a date that has passed |

## Rubrics

### B1 Understanding the user
| Id | Name | What it checks |
|---|---|---|
| 1.1 | Acknowledges what the user shared | Whether the reply to the user's worry repeats their details and names their feeling |
| 1.2 | Questions fit the user | Whether questions build on what the user said, rather than being generic or asking for things already given |
| 1.3 | Gets to the reading (counted) | How many questions come before the first reading, and how many in a row |
| 1.4 | Other person's details | When the question is about a specific person, whether their details are asked with a reason and used |

### B2 Prediction quality
| Id | Name | What it checks |
|---|---|---|
| 2.1 | Relatable reading | Whether the first reading is about the present, new, specific and tied to a reason |
| 2.2 | Answers the main question | Whether the user's main question gets a clear direction (yes, no, likely, a time window or a reason) |
| 2.3 | Chart reason in plain words | Whether readings link a life statement to the user's chart in everyday words |
| 2.4 | Builds depth | Whether later readings add new points and use what the user said |
| 2.5 | Timing and consistency | Whether timing is given as a window, with no promises or contradictions |
| 2.6 | Guidance fits the problem | Whether remedies or advice suit the problem, with how and when, and no paid pitch |
| 2.7 | Holds the main thread | When the user asks a second question, whether the first one is still answered |

### B3 Curiosity and momentum
| Id | Name | What it checks |
|---|---|---|
| 3.1 | Opens a next layer | Whether, after answering, the astrologer points to a specific further thing tied to the user |
| 3.2 | No early close | Whether the chat avoids early goodbyes and empty replies like "ji" or "ok" |
| 3.3 | Ending at the wall | Whether the last messages before time runs out give a real reading and a reason to come back |

### B4 Human feel
| Id | Name | What it checks |
|---|---|---|
| 4.1 | Message shape (counted) | Message length, number of messages in the first 5 minutes, bursts of 4+ messages in a row |
| 4.2 | Easy language | No unexplained technical terms or bookish sentences, and reuse of the user's own words |
| 4.3 | Not repetitive (counted) | Repeated lines (4+ words, at most two changed) and repeated opening words |

### B5 Difficult user (only when triggered)
| Id | Name | What it checks |
|---|---|---|
| 5.1 | Adapts to the user | When the user is vague, unengaged, angry or pushing for certainty, whether the astrologer changes approach quickly and gives a reading |

## Blueprint (v3 onwards)

How close the chat is to the ideal flow in `Chat flow- ai astro.md`. The judge marks nine stages; a script turns them into a score.

| Stage | Name | Counts when the astrologer... |
|---|---|---|
| S1 | Greeting & rapport | greets warmly and invites the user to share |
| S2 | Validates feelings | acknowledges the emotion behind the question |
| S3 | Understands the concern | identifies the main question and the outcome wanted |
| S4 | Initial prediction | gives a first meaningful answer (milestone) |
| S5 | Relevant follow-up | asks a follow-up about the user's real situation |
| S6 | Personalised prediction | ties the user's situation to their chart and answers the main question (milestone) |
| S7 | Second layer | probes a further relevant question |
| S8 | Remedy / practical guidance | gives an actionable step with how or when (milestone) |
| S9 | Hook / next consultation | after answering, names a specific next topic and invites the user back |

Each stage gets a quality: 0 = absent (or done through fear or a paid pitch), 1 = generic or half done, 2 = done as the blueprint describes and tied to this user.

**Blueprint score (1–10)** = 1 + 9 × (60% coverage + 30% milestones + 10% order)
- Coverage: sum of stage qualities out of 18.
- Milestones: S4, S6 and S8 reached by the deadline for the chat's length (doc's adaptive timing table). On time = 1, late = 0.5, missing = 0.
  - 5-minute chat (up to 7.5 min): S4 by 1:30, S6 by 3:30, S8 by 4:15
  - 10-minute chat (up to 12.5 min): S4 by 2:30, S6 by 6:00, S8 by 8:30
  - 15-minute chat (longer): S4 by 3:30, S6 by 9:00, S8 by 13:00
- Order: share of stage pairs that happen in blueprint order.

## Final score and label (v3 onwards)

**final** = 50% rubric_score + 50% blueprint, minus gate penalties, never below 1.

| Gate failed | Points off |
|---|---|
| G1 Crisis handling | 4 |
| G2 Honest identity | 3 |
| G3 Pressure to pay | 3 (v3), 1.5 (v4) |
| G3a Pressure to pay (v5+): a paid push on its own, e.g. "time badha lijiye" | 1.5 |
| G3b Fear for payment (v5+): a paid push with fear, urgency or a guarantee | 3 |
| G4 Made-up facts | 2 |

**label** (provisional, relative): within each version, the top 25% of final scores = good, the bottom 25% = bad, the rest = mixed.
**label_fixed**: the earlier fixed thresholds, kept for reference: good = final 6.5 or more; bad = 4.5 or less.
Weights, penalties and thresholds are constants at the end of `judge/metrics.py`.

From v3, G3 fails only when the judge names both a fear/urgency message and a paid-element message; the script passes G3 if either is missing.
From v4, the paid element must be one of: a price or payment; a request to extend time, reconnect or move to a call; or the astrologer offering to perform a pooja, jaap or healing. Remedies the user does themselves and a vague "upay karna hoga" do not count.

## Scoring reference (v5 onwards)

For the rubrics the judge was least consistent on (1.2, 1.4, 2.1, 2.2, 2.7, 3.2, 4.2), the judge no longer picks the number. It answers fixed yes/no checks and counts, and `judge/rubric_rules.py` applies the rubric doc's table to them, so the same answers always give the same score.
- The main question is fixed once (`main_question_idx`) and used by every rubric.
- Each rubric is scored only on its own rules (e.g. a promise lowers 2.5, not 2.2).
- Some checks are worked out by script: bare acknowledgements for 3.2, and whether a counter-question came before the answer for 2.2.
- The judge's own number for these rubrics is kept in the raw JSON under `reference.judge_own_scores`, for comparison.
- Gemini runs with a fixed seed (42).

## Outcome check (compare.py, v3 onwards)

Compares the labels with what the user did next with the same astrologer, read from the conversation file. Saved as `results/<version>/outcome_check.csv`.

| Column | Meaning |
|---|---|
| n_consults | Consultations in the file |
| consults_7d | Consultations started within 7 days of the first |
| median_return_min | Minutes from the end of the first chat to the start of the second (lower = came back faster) |
| first_chat_min | Length of the first chat in minutes |

Every pair in this data has 5+ consultations, so this measures how much and how fast users came back, not whether they did.

## scores.csv columns (one row per chat)

| Column | Meaning |
|---|---|
| tier | Low, Medium or High |
| file | Chat file name: `conversation_<userID>_<astrologerID>.csv` |
| user_id | The user's ID |
| ltv | The user's LTV |
| status | `ok` = judged; `too_short` = fewer than 2 astrologer messages and 10 or fewer messages in total; not judged |
| n_msgs | Messages in the first chat, including app messages |
| n_astro_msgs | Astrologer messages in the first chat |
| final | Final score (v3+): rubric and blueprint combined, minus gate penalties |
| label | good / mixed / bad: top 25% / middle / bottom 25% of final within the version (v3+); bad_no_service for too-short chats (v5+) |
| label_fixed | good / mixed / bad from the fixed 6.5 / 4.5 thresholds (v3+) |
| rubric_score | Average of the bucket averages with no gate cap |
| blueprint | Blueprint score, 1–10 (v3+) |
| ideal_pct | How close the chat is to the ideal blueprint conversation, 0–100% (same as blueprint, before scaling to 1–10) (v3+) |
| S1–S9 | Quality of each blueprint stage, 0–2 (v3+) |
| on_time_S4 / S6 / S8 | Milestone timing: 1 on time, 0.5 late, 0 missing (v3+) |
| length_bucket_min | Which timing column was used: 5, 10 or 15-minute chat (v3+) |
| overall | Average of the bucket averages (B1–B5, leaving out skipped ones), capped at 3 if any gate check failed |
| gate_fail | Which gate checks failed (empty = passed) |
| gate_fail_quote | The line from the chat the judge quoted for each failed check, as written (e.g. `G3: ...`) |
| gate_fail_quote_en | The same line translated into English by Gemini |
| gate_fail_reason | The judge's reason the line fails the check |
| B1–B5 | Average of the rubric scores in that bucket |
| r1.1 … r5.1 | Score for each rubric (empty = skipped) |
| trigger | Difficult-user type found by the judge: none, vague, not_engaging, angry_testing, pushing_certainty |

## tier_summary.csv / compare.py columns (one row per metric)

| Column | Meaning |
|---|---|
| metric | The score being summarised: overall, a bucket (B1–B5) or a rubric (1.1 …) |
| Low / Medium / High | Average of that score across the tier's judged chats |
| High-Low | High average minus Low average. Positive = higher-LTV users' first chats score better on this |
| rho_ltv | Rank correlation between the score and LTV, across all chats (−1 to 1). Near 0 = the score has no link to LTV; 0.2 or more is a meaningful link for data this noisy |
| scored% | Share of chats where the rubric applied (not skipped) |
| n_chats | Judged chats per tier |
| gate_fail% | Share of judged chats in the tier that failed at least one gate check |

## Files in results/<version>/

| File | Contents |
|---|---|
| prompt.py | Exact copy of the prompt used for this version |
| meta.json | Model, prompt fingerprint, temperature, start time |
| raw/<tier>/<chat>.json | Full judge output for one chat: reasoning and quotes per rubric, gate details, counted metrics, token use |
| scores.csv | One row per chat |
| tier_summary.csv | Tier averages, High-Low and rho_ltv per metric |
