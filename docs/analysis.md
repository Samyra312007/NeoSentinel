# NeoSentinel v2.0 — Strategic Analysis

_Arm AI Optimization Challenge · repo state at Week 1 of 7 (~15% built)_

> **Bottom line:** The concept is a top-of-track contender and the Week-0/1 foundation is real
> — clean contracts, injectable seams, a green test gate, and a plan that maps onto all four
> judging criteria better than most submissions will. The risk is **execution volume across
> 7 weeks and 2 people**, with the highest-scoring pieces concentrated in the back half.

---

## 1. Verified foundation health

Run directly against the repo — not taken on trust from the plan.

| Check         | Result                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------ |
| Full suite    | **46 passed, 6 skipped** — skips are integration tests that self-skip when Docker isn't up (graceful, not broken) |
| Unit tier     | 44 passed in 0.34s                                                                          |
| `ruff check .`| All checks passed                                                                          |
| Stack         | Python 3.12.3, pydantic 2.13.3, pytest 9.0.3                                                |

Two things read as real engineering, not hackathon glue:

- **Tight contract validators** — `node-\d{3}` regex, `ge/le` bounds, `max_length=3` nodes — so bad telemetry fails at the boundary, not deep in the agent (`neosentinel/contracts/telemetry.py`).
- **Injectable seams** — `PerformixDaemon` takes a `runner` callable, so the Arm PMU path is exercised without a real `apx` binary (`neosentinel/telemetry/performix.py:109`).

---

## 2. Fit against the judging rubric

Stage 2 is four weighted criteria (100 pts). NeoSentinel maps unusually cleanly onto all four —
the concept is well-aimed; execution is what's unproven.

| Criterion                     | Pts | Fit          | Why                                                                            |
| ----------------------------- | --- | ------------ | ----------------------------------------------------------------------------- |
| Technological Implementation  | 40  | Strong       | The project *is* Arm optimization: SVE2, DRAM BW, KleidiAI, INT4, on-device agent under a <5% CPU budget. |
| "WOW" Factor                  | 25  | High-ceiling | Live self-heal — SVE2 29%→79%, TTFT 312→131ms in <90s — is a genuine jaw-drop *if* the demo lands. |
| Potential Impact              | 20  | Strong       | Ships reusable artifacts the rubric names explicitly: an SDK, Performix recipes, migration-ready templates. |
| User / Developer Experience   | 15  | Good         | One-command offline `simulate`, `doctor` diagnostics, `pip install`. Docs must keep pace to bank it. |

---

## 3. Where it's genuinely strong

- **Bullseye on the theme (Tech, 40 pts).** Stage-1 pass/fail is trivial — every layer touches Arm silicon. Hits **Cloud AI** *and* **Edge AI** tracks at once, so it competes for a Best-in-Track $1k on top of the grand prize.
- **Two planes, one contract.** Data/intelligence (Sahil) and control/experience (Divyansh) run fully parallel for 6 weeks, merging only in Week 7 via frozen Pydantic contracts + mock adapters. This is how teams actually ship — and it de-risks integration up front.
- **Judge-proof offline demo (WOW, 25 pts).** Rules say judges may score on video alone. `simulate --scenario sve2_underutilization --speed 3x` runs the entire heal narrative on any laptop — deterministic, replayable, zero AWS. That's the actual winning move.
- **Artifacts, not just a demo (Impact, 20 pts).** A `SentinelEngine` SDK with `@on_alert` / `@register_action`, PyPI packaging, and Performix recipe wrappers mean other Arm developers can *adopt* the framework, not just watch it run.
- **Tests as a gate, from day one.** "No merge without tests · 80% coverage per module" is already live: 52 tests across contracts, parser, Traefik, compose, and vLLM before any feature code.
- **Submission hygiene handled.** Apache-2.0 license present and visible, public repo, English docs, clean directory layout — the boring requirements that disqualify others are already satisfied.

---

## 4. Weaknesses & risks — the honest read

Everything above the Week-1 line is plan, not code. Scored by likelihood × impact on the final submission.

| Risk                          | Severity | Why it bites                                                                                                          | Mitigation                                                                                       |
| ----------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Scope vs. two people          | **High** | 7 weeks, ~80 deliverables, 2 owners. The WOW pieces (D3 flame graph, live heal, orchestrator) all sit in Weeks 3–7. | Treat Weeks 3–4 (agent + simulate) as the true MVP. Ship a scored-complete offline demo before touching Ray/quorum polish. |
| Demo is the deliverable       | **High** | The entire "WOW" score rides on a <3-min video showing a real heal. If the offline sim isn't rock-solid and legible, 25 pts evaporate regardless of backend quality. | Build the video-facing path first and protect it. Rehearse the 29%→79% / 312→131ms beat until it's boring. |
| Real Graviton4 validation     | Medium   | Week-0 exit still blocks on "3 instances reachable via SSH." Mocks carry Weeks 1–6, but SVE2 / KleidiAI must prove out on hardware in Week 6+ or the Arm claim is theoretical. | Provision one node early for a smoke test; don't let first-real-hardware be Week 7.              |
| Agent brain believability     | Medium   | A grammar-constrained llama.cpp agent that makes *sound* healing decisions is the hardest component — and the one judges will poke at for "real AI or a rules engine?" | Make the decision tree legible in the Agent Thought stream; show the model reasoning, not just an outcome. |
| Integration bunched in Week 7 | Low      | Parallel tracks are a strength, but all wiring lands in one week with no slack. Contract drift surfaces only at merge. | Contracts are frozen and tested — hold that line. Do one dry-run integration in Week 5, not Week 7. |

---

## 5. How to win the $3,000

Prioritized by points-per-effort against the rubric. Do these in order.

1. **Make the offline heal demo the north star.** The 25-pt WOW score and the "judges test nothing" escape hatch both live here. Everything else serves a flawless 3-minute video: inject SVE2 underutilization, watch the agent think, watch it heal, show the git audit commit. Build and freeze this path early. → *banks WOW (25) + de-risks the whole submission.*
2. **Prove it on one real Graviton4 node before Week 7.** Tech Implementation (40) rewards *clearly leveraging Arm*. A single before/after Performix report with real SVE2 counters — even on one node — converts the Arm story from "claimed" to "measured." → *unlocks the top of Tech Implementation (40).*
3. **Make the agent's reasoning visible.** Stream the decision word-by-word and show the branching logic (TTFT / SVE2 / DRAM / KV-eviction). A black-box heal reads as scripted; a visible chain of reasoning reads as intelligence. → *amplifies WOW (25) + Tech (40).*
4. **Ship the SDK + a 5-minute quickstart as first-class.** Impact (20) and DX (15) are 35 points most teams under-invest in. A clean `pip install neosentinel`, a working `@register_action` example, and a README a stranger can follow are cheap points competitors leave on the table. → *Impact (20) + DX (15) = 35 pts of low-hanging fruit.*
5. **Lead every judge-facing surface with the money numbers.** SVE2 29%→79%. TTFT 312→131ms. Heal in <90s. Autonomous. On Arm. Put those in the video's first 20 seconds, the README's first screen, and the Devpost overview's first line. → *compounds all four criteria.*

---

## Win condition

Protect the offline heal demo above all else, prove the Arm numbers on real silicon at least
once, and make the agent's reasoning visible. Do that and this is a top-of-track submission.

_Analysis generated from repo state at Week 1/7 · 46 tests green · Apache-2.0._
