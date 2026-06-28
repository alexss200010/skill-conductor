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

## Self-update loop (Mode 2 IMPROVE)

1. Generate questions.
2. Evaluate → collect `failing[]`.
3. Note-taker turns failing questions + explanations into generalized, deduped lessons.
4. Apply targeted edits.
5. Re-evaluate.

**Terminate** when `failing[]` (or its critical subset) is empty, OR after 3 iterations. Keep the best result by `(gate_passed, then overall S)`. **Revert any edit that introduces a NEW failing question.**

## Fixed bank vs generated questions

- **Fixed bank → skill-artifact quality.** Stable, reusable questions (deterministic `DET-*` + curated bank). Use when evaluating the skill itself: structure, discovery, robustness are largely the same across skills, so fixed questions give comparable, repeatable scores.
- **Generated → output quality.** Run the two-step meta-prompt against the eval output, because correctness criteria are task-specific and can't be pre-listed.
- **Hybrid** (`question_source: "hybrid"`): deterministic + bank + generated together — the default for a full skill eval.

## Limitation: over-decomposition

Splitting a target into too many questions inflates objective/structural signal and drowns subjective judgment — many easy "yes" answers swamp the few hard quality calls. Mitigate:
- **Cap** the number of generated questions per requirement and per dimension.
- **Mark subjective questions non-critical**, so the gate hinges on objective, verifiable criteria, not on contestable taste judgments.
