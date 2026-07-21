# BinEval Method

Atomic binary evaluation: decompose a target into requirements, ask one yes/no question per criterion, answer each 1/0 **with evidence**, aggregate to a score in `[0,1]`. Replaces holistic numeric scoring (old 5-axis 1-10, comparator 1-5 rubric) with interpretable, auditable judgments.

Source: *"Ask, Don't Judge: Binary Questions for Interpretable LLM Evaluation and Self-Improvement"* (arXiv 2606.27226).

## Two-step meta-prompt (generated questions)

Generate questions in two passes — never write questions straight from raw intuition.

1. **Summarize → requirements.** Turn the target (a skill, or an eval output) into an explicit set `R = {r1..rK}`, each a distinct, checkable criterion. One requirement = one idea.
2. **Decompose → binary questions.** For each requirement emit `>=1` yes/no question where **"yes" = satisfied, "no" = violated**. Pair each question with a concise `violation_example` — the concrete "no" case. Tag `dimension` and `requirement_id`.

A good question is answerable from the artifact alone, has an unambiguous yes/no, and tests exactly one thing.

## Binary evaluation

Each question gets:
- `answer`: `1` (yes/satisfied) or `0` (no/violated) — no middle values.
- `explanation`: evidence grounding the answer (quote a line, cite a count, name the missing section). Evidence is mandatory; an answer without evidence is not auditable.

Deterministic checks come from `scripts/eval_skill.py --json` (the sole emitter, ids `DET-*`). LLM-judged questions come from the two-step meta-prompt (`source: "llm"`).

## Scoring

- Per-dimension: `S_d = mean(answers in dimension d)`, in `[0,1]`.
- Overall: `S = (1/N) * sum(all answers)`, where `N` = total questions.

Display bands:

| S | display |
|------|---------|
| `>= 0.90` | production-ready |
| `0.70–0.89` | solid |
| `0.50–0.69` | needs-work |
| `< 0.50` | rewrite |

Optional 50-pt display = `round(S * 50)`.

## The GATE

`gate_passed = every CRITICAL question answered 1` (deterministic criticals + critical bank questions).

The GATE — not the scalar `S` — is the pass criterion. A skill can score `S = 0.88` and still fail the gate if one critical question is `0`. Report both, but block on the gate.

## Gated self-update loop (Mode 2 IMPROVE)

Borrowed from SkillOpt (microsoft/SkillOpt): treat the skill document as trainable state, but accept an edit only when it survives evidence the editor never saw. Without this, edits are accepted by the same evals that produced them — which optimizes the skill for the test, not the task.

1. Freeze the train/held-out split (once per session).
2. Run ALL evals → grade → collect `failing[]`.
3. Note-taker turns TRAIN failing questions + explanations into generalized, deduped lessons.
4. Apply a bounded set of edits (see Edit budget).
5. Re-run ALL evals → apply the gate → record case transitions.

**Terminate** when train `failing[]` (or its critical subset) is empty, OR after 3 iterations. Keep the best ACCEPTED version by `(held-out pass-rate, then train pass-rate)`. **Revert any edit that introduces a NEW failing question** — under the gate this is automatic for critical questions (condition c) and advisory for the rest.

### Held-out gate

Split the eval set once per session with `scripts/split_evals.py` (deterministic: fixed seed, items sorted by id, stratified by the optional `category` field). Freeze the split to `split.json` in the workspace BEFORE looking at any results, and never re-split afterwards — choosing a split after seeing scores is choosing the answer.

Discipline: lessons and edits are formed from TRAIN transcripts and gradings only. Held-out grading files are opened exactly once per iteration — at the accept/reject step. The directories are flat, so nothing enforces this technically; the rule is the enforcement.

**Accept a candidate iff all three hold:**

- **(a) No held-out regression.** No held-out assertion flips pass→fail versus the parent version. Assertion-level, not aggregate — an aggregate score can hide a regression compensated by an improvement elsewhere. Single runs are noisy: before rejecting on a flip, re-run just that flipped cell once; reject only if the flip reproduces.
- **(b) Train strictly improves.** Train pass-rate must exceed the parent's — otherwise the edits didn't do their job.
- **(c) No new critical failure.** No NEW failing critical BinEval question (the GATE above still applies).

Why not "strict improvement on held-out" (the original SkillOpt criterion)? With 5–8 held-out cases, edits formed from train failures will often have nothing to fix on held-out — demanding held-out gains at that scale measures luck, not overfit. Held-out is the tripwire against regressions, not the scoreboard.

### Edit budget

At most **3 atomic edits** per iteration. Atomic = one coherent lesson applied in one place: a rule, a paragraph, a table row. An edit that touches a SKILL.md line AND its expanded entry in references/ for the same lesson counts as one. Label each edit with its lesson.

No wholesale rewrites. With ≤3 edits, a gate rejection is attributable: drop one edit, re-run, and the culprit is visible. A rewritten skill that fails the gate teaches nothing.

### Case transitions

Diff the parent's and candidate's grading assertion-by-assertion into four categories:

| Category | Parent → Candidate | Meaning |
|---|---|---|
| improved | fail → pass | the edit worked |
| regressed | pass → fail | warning even when the gate passes (train) or reject fuel (held-out) |
| persistent-fail | fail → fail | fuel for the next iteration |
| stable-success | pass → pass | counted, not listed |

Record as the `transitions` block in benchmark.json (see `references/schemas.md`).

## Fixed bank vs generated questions

- **Fixed bank → skill-artifact quality.** Stable, reusable questions (deterministic `DET-*` + curated bank). Use when evaluating the skill itself: structure, discovery, robustness are largely the same across skills, so fixed questions give comparable, repeatable scores.
- **Generated → output quality.** Run the two-step meta-prompt against the eval output, because correctness criteria are task-specific and can't be pre-listed.
- **Hybrid** (`question_source: "hybrid"`): deterministic + bank + generated together — the default for a full skill eval.

## Limitation: over-decomposition

Splitting a target into too many questions inflates objective/structural signal and drowns subjective judgment — many easy "yes" answers swamp the few hard quality calls. Mitigate:
- **Cap** the number of generated questions per requirement and per dimension.
- **Mark subjective questions non-critical**, so the gate hinges on objective, verifiable criteria, not on contestable taste judgments.
