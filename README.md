# skill-conductor

Full-lifecycle authoring for Claude Code agent skills: **draft → test → review → improve → package**. One skill to build, evaluate, and ship the rest.

## Install

Two one-liners, pick either:

```bash
# skills.sh
npx skills add smixs/skill-conductor
```

```bash
# Claude Code plugin
/plugin marketplace add smixs/skill-conductor
/plugin install skill-conductor@smixs
```

## What it does

Six modes, detected from context:

| Mode | When |
| ---- | ---- |
| **CREATE** | Build a new skill from scratch: intent → architecture → scaffold → write → test |
| **IMPROVE** | Fix a skill that doesn't trigger or underperforms; diagnose and run the eval loop |
| **VALIDATE** | Test a skill: structural checks + trigger testing + BinEval scoring |
| **REVIEW** | Quick quality gate for a third-party skill |
| **OPTIMIZE** | Auto-tune the description for accurate triggering with a train/test split |
| **PACKAGE** | Validate and bundle into a distributable `.skill` file |

## The 9 authoring principles

1. **Pre-flight** — check runtime (`uv`, env, LLM access) before any mode that runs scripts.
2. **No process in description** — triggers and purpose only; workflow steps in the description make the agent skip the body.
3. **MOC** — SKILL.md is a map (table of contents pointing to references), not a prose dump.
4. **Fresh-practitioner author** — write from real practice, for someone who has never done the task.
5. **TWI ("why")** — explain the reasoning behind a rule; explanation beats capitalized MUST/NEVER.
6. **Blind-agent test** — verify behavior by running the skill in a clean session.
7. **Inline checklists** — put checks at the risk points where things actually go wrong.
8. **One term per concept** — pick one word and stick with it (not template/boilerplate/scaffold).
9. **Cut the fat** — keep secrets, env values, keys, and user-absolute paths out of SKILL.md; reference them.

## Evaluation: BinEval

Quality is measured with **BinEval** — atomic binary yes/no questions per dimension, each answered 1/0 with grounding evidence, aggregated to a score in [0,1].

- **Five dimensions:** Discovery, Clarity, Structure, Robustness, Completeness.
- **Evidence-grounded:** every answer carries an explanation; deterministic checks plus generated questions.
- **Gate on critical:** the pass criterion is that every critical question answers 1 — not the scalar score.
- **Benchmark aggregation** — roll up multiple runs into stable per-dimension statistics.
- **Blind A/B comparison** — two versions answer the same questions without the judge knowing which is which; winner by yes-rate.
- **HTML eval-viewer** — interactive report of results, failing questions, and version-over-version deltas.

BinEval is adapted from *"Ask, Don't Judge: Binary Questions for Interpretable LLM Evaluation and Self-Improvement"* (arXiv 2606.27226).

## Requirements

- **`uv`** — required; checked in pre-flight. If absent, the run stops.
- **Anthropic API key** — for the executor subagents that run evals and comparisons.

## License

MIT — see [LICENSE](LICENSE).
