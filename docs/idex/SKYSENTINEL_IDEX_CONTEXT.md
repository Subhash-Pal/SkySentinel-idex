# SkySentinel: iDEX Open Challenge PoC. Full handoff context

Compiled 22 Nov 2026. Read this whole file before acting. Everything here is either (a) decided by the owner, (b) a proposal not yet chosen, or (c) a researched fact with a source and a confidence level. Do not blur the three.

---

## 1. Owner and working style
- Owner: Subhash, independent AI innovator and researcher in India. Solo, part-time on this project. 12+ years embedded C/C++; works in Python, PyTorch, Rust, AirSim, YOLOv8.
- Wants honest, direct assessments, not flattery. Flag weak ideas and over-claims.
- Math must be explained from foundations (symbol names, meanings, use cases) at undergraduate level.
- Every response is structured GATHER / SUMMARIZE ("Ground Truth", under 150 words) / DISPATCH, and ends with a "CURRENT STATE OVERVIEW" block.
- Group project talk under headings **Rodic / SkySentinel / Research**. Whenever "Research" appears, say which type: **Technical research**, **Market research**, or another named type (prior-art, legal, process). Never a bare "Research".
- Day routine: the first reply each day recalls the previous savepoint, restates the objective and task list, explains today's task, does it, summarises, and ends with the next day's task.
- Keep replies short: he reads on a phone.

## 2. Goal and deadline
- Submit SkySentinel to the **iDEX Open Challenge** as a **simulation-based proof of concept (PoC)**, asking for funds to build the prototype.
- Portal row shows deadline **31 Dec 2026, 23:59** (owner's paste). One official page fetched showed 30 Sep 2026, probably an earlier cycle. **Confirm on the live portal.**
- Internal submit window: 25-29 Dec 2026. Work starts Sun 22 Nov 2026 (about 40 days).
- Grant ceiling per public pages: up to Rs 1.5 crore (non-repayable, equity-free). Matching-funds rule and tranche structure are unconfirmed.

## 3. What iDEX Open Challenge actually asks (confirmed vs not)
Confirmed from the owner's uploaded PDF ("iDEX Open Challenge, General Description", created 2023) and idex.gov.in/disc-category/18:
- Open to Indian startups, individual innovators, MSMEs, with defence/aerospace-relevant solutions.
- Themes include aerospace, autonomous systems, AI, quantum.
- Proposals must describe the technology, its applications, and "preferably" a demonstration of feasibility. An "idea, technology or a product" is eligible.
- Submission only through the iDEX portal.
- Neither the PDF nor the portal page states a required stage or TRL.

Not confirmed (third-party sites only; treat as unverified): TRL 3+ requirement; 50% matching contribution; milestone tranches; selection by expert panel then iDEX Grand Jury (judging novelty, feasibility, impact, strategic relevance, team).

Conclusion adopted: a simulation PoC is the right evidence level; do not claim a prototype.

**Possible conflict to check first:** memory says earlier iDEX applications (May/June 2026, including DISC 14 ten problem statements "plus Open Challenge") are still under review. Confirm whether SkySentinel is already filed under the Open Challenge, and whether this is a new cycle or a resubmission. Remaining Apply-form fields (title, abstract limit, uploads, stage field, funding ask) are visible only after sign-in.

Domain picks suggested: AI/ML, Autonomous Systems, Unmanned/Autonomous Systems. "Smart Weapon Systems" only with a "decision-support, human approval required" first page. Skip "Automated Ammunition".

## 4. What SkySentinel is
- Positioning: the **"AI brain"** (software/AI layer) for autonomous drones and defensive counter-UAS, working with existing sensors and effectors. Not new anti-drone hardware, not UCAS. Human always approves: HITL (human-in-the-loop) progressing to HOTL (human-on-the-loop), never fully autonomous. Swarm only for the counter-drone case. Simulation first until hardware is confirmed.
- Architecture **v-3: 26 layers (L0-L25)** in four runtime tiers above an untouched PX4 firmware loop:
  - Tier 0: PX4 firmware, 50-1000 Hz, no AI inside.
  - Tier 1 (20-100 Hz, parallel): perception/navigation, L0-L9, L12-L15.
  - Tier 2 (10-50 Hz, sequential): fusion/situational awareness, L10, L11, L16-L21.
  - Tier 3 (1-10 Hz): L22 path planning (PPO/SAC + classical planner/MPC), L23 multi-agent (GNN + MARL), L24 mission safety gate.
  - Tier 4 (async/post-mission): L25 self-correction, offline, human-gated write-back only.
- Key rules: L24 is a **gate, not a generator**; it withholds, never substitutes. RL is never inside L24. Heavy models (VLM/VLA/world model) never sit in the high-rate control loop. L24 talks to PX4 only via uXRCE-DDS or MAVLink offboard (never uORB); fail-closed via PX4's offboard-loss watchdog; RC override always wins; every L24 verdict is correlated with the PX4 .ulog.
- Gate 3 = L24 Behavioral Invariants Verifier (17 checks, five domains). Gates 1 and 2 are an unconfirmed assumption (Gate 1 at the Tier 1-2 hand-off near L11; Gate 2 at the Tier 2-3 hand-off before L22/L23).
- **Naming caution:** the project schedule below uses **Checkpoints CP1-CP3** to avoid clashing with architecture Gates 1-3.
- Key layer models (baselines): L0 YOLOv8n/YOLO26; L2 1D-CNN/Transformer/Autoencoder; L6 EKF + learned inertial model; L11 autoencoder/Isolation Forest; L16 multimodal ViT/CLIP; L17 YOLO/RT-DETR + ByteTrack/Kalman.
- Candidate additions (unverified, pluggable, none finalized): Mamba/SSM at L2/L4/L5/L6; N1 reversibility-ranked action selection; N4 red-team agent; N6 hash-chained decision ledger; H1 conformal intent gate; H2 learned barrier certificates; H3 Bayesian inverse planning; H4 activation probes; H5 event cameras; GRAFT (preliminary, out of the submission).

## 5. Repo and tooling state
- Repo: `Subhash-Pal/Sky-Sentinel-Sim` (**private**; keep nothing public). Last known main state: D0 skeleton, `eval/calibration.py` (ECE, reliability bins, accuracy at coverage), D1 tools (`scripts/make_splits.py`, `scripts/licence_log.py`), D7 harness `eval/gate3_harness.py` + `eval/run_d7.py`, Gate 3 v0.1 in `safety/gate3.py` (17 checks, `configs/gate3_policy.yaml`, spec `docs/gate3-spec.md`), 96 tests passing as of Nov 9. Docs: `docs/deliverable-status.md`, `docs/layer-status.md`, `docs/evidence-matrix.md`, `docs/data-licence-log.md`, `docs/reasoning-layer-plan.md`.
- Gate 3 v0.1 results are conformance on synthetic inputs with placeholder policy values, not an effectiveness claim.
- YOLO and AirSim are implemented **locally with no GPU**, but that code is **not in the repo yet** (counts as "reported, not done").
- Tools: AirSim (AirSimNH packaged binary, plugin 1.8.1) runs locally on a machine with **no GPU**; Colab **T4** is the only GPU (training only). Isaac Sim is not possible without a local NVIDIA RTX GPU.
- Datasets shortlisted: Anti-UAV, Drone-vs-Bird (real test set must come from these), VisDrone, UAVDT (images from drones, not drones as targets). **Licences not yet read** (the fetch tool was blocked); the owner must read them. Split by sequence; real-only fixed test set.
- No hardware available; hardware work is out of scope for this submission.

## 6. Decisions made by the owner
1. Submission uses a **pretrained model plus fine-tuning**; from-scratch work is a separate side effort.
2. Add 1-2 practical features to the 26-layer architecture, to be showcased with validation.
3. Cover four themes: near-real-time latency, self-learning, preventing reward hacking, decision under uncertainty.
4. Claim ceiling: "demonstrated in simulation, tested on public datasets, edge-readiness checked with hardware-independent measures". Latency from Colab/CPU is labelled **proxy**. No battlefield or field claims. No invented numbers.
5. Start work Sun 22 Nov inside the Sentinel GitHub; branch/folder delegated to the assistant.
6. Plan to be shown for India's need first; Japan, Taiwan, UAE and others are shown separately as roadmap.

## 7. Proposals NOT yet chosen (owner picks Feature 1 alone or both)
**Feature 1: uncertainty-gated, deadline-aware reasoning slot** (new Tier 3 advisory slot before L22).
- QLoRA-fine-tuned small VLM on AirSim-generated data. Split **conformal prediction**: from a calibration set, build a prediction set that contains the true label with probability at least 1 - alpha (alpha = chosen error rate; "coverage" = how often the set contains the truth). One answer = may suggest; several answers or none = escalate to human and hold.
- Fast classical path always runs. A **circuit breaker** falls back to the classical baseline if the VLM misses its deadline T_deadline.
- Metrics: empirical coverage vs 1 - alpha; average set size; escalation rate; accuracy at coverage; per-stage latency proxy vs T_total <= T_deadline. Reuse `eval/calibration.py`.
- Honest caveat: marginal (average) coverage can hide subgroup failures, so report coverage per subgroup (VLM answered in time vs timed out). Guarantees assume calibration data resembles test data; sim-to-real shift is a stated limit.

**Feature 2 (conditional): reward-hack monitor at L22** on a toy PPO task with a planted shortcut (dynamic speed governor). Compare no monitor vs reward penalty vs constrained optimisation. Metric: exploit rate. Include a "verifier coverage" ablation (shortcut covered by the verifier vs not). GRAFT stays out. Only start if Feature 1 passes CP2.

**Novelty claims (proposals; strength is modest; none is a breakthrough):**
- SN1 deadline-conditioned conformal escalation (Feature 1). Closest prior art: edge-cloud cascades via conformal alignment, arXiv 2510.17543.
- SN2 gate-as-monitor reward-hack test (Feature 2); resembles constrained-MDP cost signals, so claim an evaluation protocol only.
- SN3 promotion bundle for gated post-mission improvement: planned, not demonstrated.
- SN4 sim-to-real coverage gap on Anti-UAV / Drone-vs-Bird: a measurement contribution, publishable either way.
- Backbone (cheap, high credibility): N6 hash-chained decision ledger on L24 verdicts; tamper test.
- Other candidates ranked: N1 reversibility-ranked actions; GNSS spoof/jam detection feeding the L11 trust gate (Mamba vs 1D-CNN); N4 red-team scenario generator.
- Prior art to read in full (only abstract-level so far, **verify before any "first" claim**): SafeVLA (NeurIPS 2025); VLSA arXiv 2512.11891; conformal prediction on VLA action tokens (2025 thesis); learnable conformal prediction on edge arXiv 2509.21955; arXiv 2510.17543; EcoVLA arXiv 2608.15502; latency-tolerant cloud-edge VLA arXiv 2608.00569; KnowNo arXiv 2307.01928; conformal predictive safety filter arXiv 2306.02551; Lindemann et al. arXiv 2602.12616 (conformal under shift).

## 8. Showcase frame and wording rules
- Pitch the **assurance layer**: it knows when the AI is unsure, falls back to a classical method within a deadline, asks a human to approve, and logs every decision for audit. Position as a component that plugs into platforms (partner, not rival). This is the assistant's strategic judgment; test it with one outside contact in week 1 (the PDF says engagement is facilitated by DIO and its Partner Incubators).
- Competitors are strong (BEL's SAKSHAM grid; Edge Group claims over 85% of Iranian drones stopped). Do not compete on interception.
- **Say:** "simulation PoC", "proxy latency", "reduces measured exploit rate", "offline, gated post-mission improvement", "combination", "measured", "decision support, human approval required".
- **Never say:** "first", "prevents reward hacking", "self-learning", "real-time" without a measured budget, "field-proven", "autonomous engagement", anything implying weapons release or fully autonomous action.
- Report negative results. Label proxy numbers as proxy. Check dataset licences before commercial use. Check export rules (SCOMET) before sharing technical detail abroad; share an IP-safe brief, not code.

## 9. Demand evidence (Market research). VERIFY against primary sources before quoting
**India (drives the December build; shown separately)**
- Northern Command tender: 90 counter-UAS, 4 AI-enabled swarm sets, 274 data links, about Rs 16.92 crore. https://idrw.org/?p=427679
- SAKSHAM AI-enabled counter-UAS grid (with BEL), fast-track induction. https://www.armyrecognition.com/archives/archives-aerospace-defense/defense-news-aerospace-2025/india-fields-saksham-counter-drone-grid-to-secure-tactical-airspace-above-frontline-units
- ADE "Heterogeneous Swarm AI" programme: hardware-in-the-loop early 2027, 50+ drone trials late 2027; swarms to work in contested electronic environments. https://idrw.org/?p=404593
- DISC 14 problem statements incl. "AI Enabled Multi Agent Module for UAS Functions" and "AI Module for UAS for Autonomous Recognition Identification and Targeting". https://www.ddpmod.gov.in/offerings/innovations?page=2
- Indigenisation push after Operation Sindoor; 45 contracts (about Rs 2,326 crore) signed with iDEX winners as of Feb 2026. https://inc42.com/features/why-defence-tech-is-becoming-indias-next-big-deeptech-bet and https://www.policyedge.in/p/ministry-of-defence-mission-mode-for-drone-manufacturing-and-deep-tech-innovation
- Imported flight controllers/sensors/processors seen as a security risk. https://www.outlookbusiness.com/magazine/indepth-battle-tested-homegrown-and-ready-to-scale-can-indian-defence-tech-start-ups-go-the-distance
- India features to show: Feature 1; ledger; GNSS-denied robustness; open-source/PX4 stack for indigenisation.

**Taiwan (separate)**
- Funds GPS-independent, jam-resistant drone technology: https://www.scmp.com/news/china/politics/article/3333755/taiwan-military-budgets-us32-million-drone-tech-amid-beijings-pressure
- Audit: jamming-based anti-drone measures may fail against fibre-optic and AI-guided drones: https://www.taipeitimes.com/News/front/archives/2026/07/26/2003861386
- Counter-drone systems not yet integrated with a C2 system under development (target end 2027): https://focustaiwan.tw/politics/202608050013
- Special budget includes 200,000+ UAVs and counter-UAS: https://insideunmannedsystems.com/taiwan-plans-massive-drone-and-c-uas-expansion-in-new-special-defense-budget/
- Features: non-RF detection/tracking (EO/IR, acoustic: L16/L17/L21); GNSS-denied navigation (L6, L7, L8); standard model interface for others' C2.

**Japan (separate)**
- FY2027 request about 8.9 trillion yen; priorities AI and unmanned assets; AI-powered decision support; command and control that survives disruption. https://news.usni.org/2026/09/01/japan-budget-requests-record-55-6b-for-unmanned-long-range-strike-capabilities ; https://www.mod.go.jp/en/d_act/d_budget/pdf/fy2027_20261009.pdf ; https://www.dailysabah.com/business/economy/japan-looks-to-ai-as-it-seeks-record-556b-defense-budget/amp
- Features: calibrated-uncertainty decision support with human approval (Feature 1 + ledger); degraded-link behaviour (no operator reply means hold via PX4 failsafe).

**UAE (separate)**
- Edge Group: cost-exchange problem (expensive interceptors vs cheap drones), demand for layered integrated architectures, fast field updates, autonomous-or-manual modes. https://www.khaleejtimes.com/uae/drone-warfare-cheap-uavs-shift-air-defence-uaes-edge ; https://www.thenationalnews.com/business/economy/2026/05/05/more-than-85-of-irans-drone-strikes-on-uae-thwarted-by-edge-defence-systems/ ; https://armyrecognition.com/news/umex-2026/uae-edge-develops-new-generation-counter-drone-capability-with-vortex-e-autonomous-kinetic-interceptor
- Features: cost-aware response ladder (softest, cheapest effective action first; extends N1); HITL/HOTL mode switch; signed fast post-mission model updates (planned L25).

**Common core (build once):** uncertainty gate, audit ledger, GNSS-denied robustness, standard interface. International items stay on the roadmap slide, not in the December build. Most sources are trade press.

## 10. Deliverables (project IDs IDX-xx; do not confuse with older D0-D17)
Repo `Subhash-Pal/Sky-Sentinel-Sim`, branch `idex/poc-dec26`, folder `docs/idex/`.

| ID | Type | Deliverable | Done when | Target |
|---|---|---|---|---|
| IDX-01 | Setup | Branch + `docs/idex/` skeleton + `CLAIMS.md` | Pushed, claim ceiling committed | 22 Nov |
| IDX-02 | Technical research (prior art) | `prior_art.md` for SN1, SN4, SN2: what they did / what we add / what we do not claim; start with arXiv 2510.17543 | Full papers read | 22-25 Nov |
| IDX-03 | Market research | `demand.md`: every demand claim with a primary source; drop unverifiable ones | Every quoted claim linked | 22-26 Nov |
| IDX-04 | Market research | One outreach message to a partner incubator or industry contact: is an assurance layer a real need? | Sent, reply logged | 23 Nov |
| IDX-05 | Writing | One-page problem / gap / claim sheet v0 | Passes CLAIMS.md | 23 Nov |
| IDX-06 | Feature 1 | AirSim data generator, label schema, first dataset | Reproducible, fixed seeds | 24-27 Nov |
| IDX-07 | Feature 1 | Pretrained small VLM + QLoRA fine-tune + classical baseline | Both run on same test set | 27 Nov-1 Dec |
| IDX-08 | Feature 1 | Split conformal calibration + coverage metrics | Coverage vs 1-alpha, set size, escalation rate, accuracy at coverage | 28 Nov-1 Dec |
| IDX-09 | Feature 1 | Deadline-aware circuit breaker + latency proxy log | Coverage per subgroup (answered / timed out) | 1 Dec |
| **CP1** | | First coverage numbers incl. timeout subgroup | Numbers exist, honest even if poor | **1 Dec** |
| IDX-10 | Feature 1 (SN4) | Sim-to-real coverage gap on Anti-UAV / Drone-vs-Bird | Gap measured and plotted | 2-6 Dec |
| IDX-11 | Backbone | Hash-chained decision ledger on L24 verdicts + tamper test | Edited entry always detected; overhead measured | 2-8 Dec |
| **CP2** | | Feature 1 passes, or cut rule | If slipped, Feature 2 becomes "planned"; submit one solid result | **8 Dec** |
| IDX-12 | Feature 2 (conditional) | Toy PPO planted-shortcut test | Exploit rate + verifier-coverage ablation | 8-15 Dec |
| IDX-13 | Writing | Proposal text draft (title, abstract, approach, milestones, funding ask) | Complete | 8-15 Dec |
| **CP3** | | Freeze results | No new experiments | **15 Dec** |
| IDX-14 | Evidence | Colab notebook + results card (negative results included) | Runs end to end clean | 16-20 Dec |
| IDX-15 | Showcase | 3-minute simulation demo video | Shows gate, fallback, ledger | 18-22 Dec |
| IDX-16 | Review | Wording review against CLAIMS.md; independent over-claim read | Zero banned phrases | 23-24 Dec |
| IDX-17 | Writing | Roadmap slide: sim PoC, HIL, field trial; India first; Japan/Taiwan/UAE as future | One slide | 23-24 Dec |
| IDX-18 | Submit | Fill Apply form, upload, submit | Confirmation received | 25-29 Dec |

Recommended order of priority: prior-art check (IDX-02) before writing any "novel" sentence; Feature 1 is the flagship; add Feature 2 only if CP2 passes; if short of time cut Feature 2 first.

## 11. Open items (need the owner)
1. Feature 1 alone, or both.
2. Name one outreach contact for IDX-04.
3. Dataset licence wording (Anti-UAV, Drone-vs-Bird, VisDrone, UAVDT).
4. Whether SkySentinel is already filed under the Open Challenge; the remaining Apply-form fields; the exact deadline.
5. Push the local YOLO/AirSim code into the repo so it counts.
6. Contact line for the IP-safe brief; export-control query (DGFT or trade lawyer).

## 12. Top risks
Calibration data not matching test data; fine-tuning time sink on a Colab T4 (cap compute); over-claiming; solo capacity (cut nice-to-haves first); dataset licence terms; no hardware.

## 13. Never do
- Never invent numbers, citations, or a "first" claim. Never present proxy latency as edge-measured.
- Never include secrets (tokens, keys, personal emails) in files or commits.
- Never push to `main` directly for this work; use `idex/poc-dec26`.
- Never add content on weapons release, autonomous engagement, or targeting. Everything stays decision-support with human approval.
- Never edit uploaded originals; work on copies.
