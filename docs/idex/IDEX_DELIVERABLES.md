# SkySentinel: iDEX Open Challenge PoC deliverables

Note: CP1-CP3 are project checkpoints, not the architecture Gates 1-3.

Repo: `Sky-Sentinel-Sim` · Branch: `idex/poc-dec26` · Folder: `docs/idex/`
Start: Sun 22 Nov 2026 · Submit window: 25-29 Dec 2026 (portal deadline shown as 31 Dec 23:59, confirm on the portal)

## The one claim
Any AI decision reaches the operator through an uncertainty-gated, deadline-safe, auditable human-approval path, with measured (not assumed) coverage. Simulation PoC only. Funds requested to build the prototype.

## Claim ceiling (put in `docs/idex/CLAIMS.md`)
- Say: "simulation PoC", "proxy latency", "reduces measured exploit rate", "offline, gated post-mission improvement", "combination", "measured".
- Do not say: "first", "prevents reward hacking", "self-learning", "real-time" without a measured budget, "field-proven".

## Deliverables

| ID | Type | Deliverable | Done when | Target |
|---|---|---|---|---|
| IDX-01 | Setup | Branch + `docs/idex/` skeleton + `CLAIMS.md` | Branch pushed, claim ceiling committed | 22 Nov |
| IDX-02 | Technical research (prior art) | `prior_art.md`: SN1, SN4, SN2, each as "what they did / what we add / what we do not claim"; start with arXiv 2510.17543 | Full-paper read, not abstract, for each | 22-25 Nov |
| IDX-03 | Market research | `demand.md`: each demand claim with a primary source (Army tender, ADE programme, MoD Japan FY2027 PDF, Taiwan audit); drop what cannot be verified | Every quoted claim has a primary link | 22-26 Nov |
| IDX-04 | Market research | One outreach message sent to a partner incubator or industry contact; question: is an assurance layer a real need? | Message sent, reply logged | 23 Nov |
| IDX-05 | Writing | One-page problem / gap / claim sheet v0 | One page, passes CLAIMS.md check | 23 Nov |
| IDX-06 | Feature 1 | AirSim data generator + label schema + first dataset (size set in the spec) | Reproducible script, fixed seeds | 24-27 Nov |
| IDX-07 | Feature 1 | Pretrained small VLM + QLoRA fine-tune, plus classical baseline | Both produce outputs on the same test set | 27 Nov-1 Dec |
| IDX-08 | Feature 1 | Split conformal calibration + coverage metrics (reuse `eval/calibration.py`) | Coverage vs 1-alpha, set size, escalation rate, accuracy at coverage | 28 Nov-1 Dec |
| IDX-09 | Feature 1 | Deadline-aware circuit breaker + latency proxy log (VLM timeout falls back to classical) | Coverage reported per subgroup: answered in time / timed out | 1 Dec |
| **CP1** | | First coverage numbers incl. timeout subgroup | Numbers exist, honest even if poor | **1 Dec** |
| IDX-10 | Feature 1 (SN4) | Sim-to-real coverage gap on Anti-UAV / Drone-vs-Bird | Gap measured and plotted | 2-6 Dec |
| IDX-11 | Backbone | Hash-chained decision ledger on L24 verdicts + tamper test | Any edited entry detected; overhead measured | 2-8 Dec |
| **CP2** | | Feature 1 passes, or cut rule | If slipped, Feature 2 becomes "planned" and one solid result is submitted | **8 Dec** |
| IDX-12 | Feature 2 (conditional) | Toy PPO with planted shortcut; compare no monitor / reward penalty / constrained optimisation | Exploit rate reported; verifier-coverage ablation | 8-15 Dec |
| IDX-13 | Writing | Proposal text draft (title, abstract, approach, milestones, funding ask) | Draft complete | 8-15 Dec |
| **CP3** | | Freeze results | No new experiments after this | **15 Dec** |
| IDX-14 | Evidence | Colab notebook + results card (all metrics, negative results included) | Runs end to end from a clean session | 16-20 Dec |
| IDX-15 | Showcase | 3-minute simulation demo video | Shows gate, fallback, ledger | 18-22 Dec |
| IDX-16 | Review | Wording review against CLAIMS.md; independent read for over-claims | Zero banned phrases | 23-24 Dec |
| IDX-17 | Writing | Roadmap slide: sim PoC, HIL, field trial; India need first; Japan / Taiwan / UAE as future scale | One slide | 23-24 Dec |
| IDX-18 | Submit | Fill Apply form, upload, submit | Confirmation received | 25-29 Dec |

## Open items
- Feature 1 alone or both (Feature 2 only if Gate 2 passes)
- Apply-form fields: abstract limits, uploads, stage field, matching-funds rule (visible after sign-in)
- Confirm the deadline on the portal (31 Dec shown; one official page shows 30 Sep)
- Name one outreach contact for IDX-04

## Weekly rule
End each week with: what was achieved, what slipped, go/no-go for the next gate.
