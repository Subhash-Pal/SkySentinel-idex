# SkySentinel: AirSim + VLM/VLA task. Context and prompt (22 Nov 2026)

Use with `SKYSENTINEL_IDEX_CONTEXT.md` (full project briefing). This file narrows it to the AirSim + VLM/VLA build (deliverables IDX-06 to IDX-09) on the owner's local Windows machine.

**Status labels used below:** DECIDED (owner said it), PROPOSAL (not yet chosen), VERIFY (from general knowledge, check before relying on it).

---

## PART A: CONTEXT

### A1. Machine and tools (DECIDED / stated by owner)
- AirSim binary: `C:\Blocks\Blocks\AirSimNH\AirSimNH\WindowsNoEditor\AirSimNH\Binaries\Win64\AirSimNH.exe` (AirSimNH packaged build, file date 28-03-2026, plugin 1.8.1). Start it in PowerShell with `.\AirSimNH.exe`.
- Local machine has **no discrete GPU**. Colab (Tesla T4) is the only GPU so far. Isaac Sim is out (needs a local NVIDIA RTX).
- YOLO + AirSim were implemented locally earlier, but that code is **not in the repo yet** (counts as reported, not done).
- Repo for this PoC: `Subhash-Pal/SkySentinel-idex` (confirm it is **private**). Work on branch `idex/poc-dec26` (pushed, commit 0b8cf00 on 23 Nov), never on main. Local clone: `C:\Users\Shubh\OneDrive\Documents\GitHub\SkySentinel-idex`; run output goes outside OneDrive (`D:\DRDO-iDEX\SkySentinel\runs`). The older repo `Subhash-Pal/Sky-Sentinel-Sim` holds earlier code (calibration, Gate 3); reuse is an open decision (copy the files needed, or vendor them).

### A2. What this task must prove (DECIDED)
Feature 1 of the iDEX PoC: an **uncertainty-gated, deadline-aware advisory slot** (Tier 3, before L22). A small vision-language model (VLM) looks at AirSim frames and answers a closed-set question. A **conformal prediction set** decides: one answer = may suggest; several answers or none = escalate to the human and hold. A fast classical path always runs. A **circuit breaker** falls back to the classical baseline when the VLM misses its deadline. The VLM never sits in the high-rate flight loop and never commands the vehicle; every output passes the L24 gate and a human.

Claim ceiling: simulation only; public datasets for sim-to-real; latency is **proxy**; no invented numbers; no "first".

### A3. Local setup that works without a GPU (PROPOSAL + VERIFY)
Split the work by what needs a GPU:

| Step | Needs GPU? | Where |
|---|---|---|
| Run AirSimNH, fly scripted scenarios, capture frames + ground truth | No (renders on CPU/integrated graphics, low FPS) | Local Windows |
| Zero-shot VLM baseline and closed-loop demo | No, if small and quantised | Local CPU (Ollama or llama.cpp; small models such as Moondream, SmolVLM-256M/500M, Qwen2.5-VL-3B 4-bit) |
| QLoRA fine-tune of the VLM | **Yes** | Colab T4, or an alternative below |
| Conformal calibration + coverage analysis | No (uses saved outputs) | Local or Colab |

GPU alternatives to Colab (VERIFY current quotas/prices): Kaggle notebooks (free GPU with a weekly quota); hourly rented GPUs (RunPod, Vast.ai, Lambda); a second-hand NVIDIA card in the local machine. Keep training short and capped; a T4 has no bf16 and no FlashAttention, so use fp16 and plain attention.

Python on the local machine (VERIFY): use a **Python 3.10 virtual environment**; newer Python versions often break the `airsim` package install. Typical order: `pip install numpy msgpack-rpc-python` then `pip install airsim`. `pytest` for tests.

AirSim settings file (VERIFY): `C:\Users\<you>\Documents\AirSim\settings.json`. Starting template, one drone plus one scripted target:

```json
{
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ClockSpeed": 1.0,
  "Vehicles": {
    "Drone1":  { "VehicleType": "SimpleFlight", "X": 0,  "Y": 0, "Z": 0 },
    "Target1": { "VehicleType": "SimpleFlight", "X": 15, "Y": 0, "Z": 0 }
  }
}
```
Launch with a small window to save rendering cost, e.g. `.\AirSimNH.exe -windowed -ResX=640 -ResY=480` (VERIFY flags). Expect low frame rates; reduce resolution before anything else.

### A4. Task design (PROPOSAL; owner confirms)
- **Closed-set question per clip:** "What is Target1 doing relative to the camera drone?" Labels (single token each so class probabilities can be read from the model's logits): A NO_TARGET, B APPROACH, C LOITER, D PASS_BY, E RETREAT.
- **Input:** 3 frames (t-2 s, t-1 s, t) stitched into one image strip + the question. Ground truth comes from the scripted behaviour of `Target1` and its logged pose (never from the model).
- **Hard-case axes** (so uncertainty is real, not trivial): distance bands, occlusion behind buildings, time of day/weather, motion blur, similar-looking behaviours (slow APPROACH vs LOITER).
- **Splits:** train / calibration / test are separated by **scenario seed**, never by frame. Calibration must not overlap train or test. Suggested sizes: about 3,000 train, 500 calibration, 500 test clips (PROPOSAL; time per clip must be measured first).
- **Conformal prediction (symbols):** let n be the number of calibration clips, α the allowed error rate (e.g. 0.1), p_c the model's probability for class c. Nonconformity score s_i = 1 − p(true class of clip i). Take q̂ = the ⌈(n+1)(1−α)⌉/n quantile of {s_i}. For a new clip, the prediction set is every class c with 1 − p_c ≤ q̂. Coverage = fraction of test clips whose set contains the true label; the target is at least 1 − α. Caveat: this holds on average only if calibration data resembles test data, so report coverage **per subgroup** (answered in time / timed out; each distance band) and state the sim-to-real limit.
- **Circuit breaker:** if the VLM takes longer than T_deadline, mark `timed_out`, use the classical baseline answer, and escalate. The classical baseline must exist (for example, geometric rules on target pose/size in the frame, or a small CNN) so there is something to fall back to and compare against.
- **VLA (stage 2, later):** only after Feature 1 passes CP1/CP2. "VLA-lite" = a small action-intent head on a frozen encoder, output = a discrete advisory action (HOLD, CLIMB, YAW_LEFT ...), always through L24 and a human. From-scratch VLA is a separate side track, not in the December submission.

### A5. Logging (DONE; ships with this file)
`sentinel_airsim.zip` contains:
- `sentinel_logger.py`: one folder per run with `manifest.json` (versions, seed, config hash, git commit, no hostname/secrets), `events.jsonl` (**hash-chained**, so edits or deleted lines are detected), `frames/`, `summary.json`. Helpers: `frame`, `state`, `scenario` (ground truth), `vlm_call` (derives `timed_out` and `fallback_used`), `gate_verdict`, `escalation`, `timer` (proxy latency), `finalize`, `bundle` (zip for upload; thins frames if over the size cap; the log still lists every frame hash).
- `analyze_run.py`: reads a run folder or zip; checks the chain; prints counts, proxy latency percentiles, timeout / escalation rates, accuracy and coverage overall and per subgroup. Rows marked `stub=True` are excluded.
- `airsim_smoke_test.py`: `--mock` tests the pipeline with no AirSim (tested here); the live branch flies a small square and logs frames and state (**not yet run against real AirSim: the first run is the test**).
- `tests/`: 6 tests, all passing (chain integrity, tamper and deletion detection, bundling, analysis, stub exclusion).

Upload loop: run the script, then upload the `.zip` named in the last output line (default cap 30 MB) to the chat. The analysis can then be run on exactly what you uploaded.

### A6. First three days (PROPOSAL)
- **Day 1 (22 Nov, today):** IDX-01 branch and folders; copy `sentinel_airsim/` into the repo; run `pytest`; run `airsim_smoke_test.py --mock`, then start `AirSimNH.exe` and run the live smoke test; upload the zip.
- **Day 2:** write `settings.json`; script `Target1` behaviours (5 labels); generate 50 clips; log them with `scenario` ground truth; measure real seconds per clip.
- **Day 3:** zero-shot VLM baseline on CPU on those clips, logged through `vlm_call`; first conformal numbers from the baseline (poor is fine; report it); decide dataset size from measured generation time.

### A7. Risks
No GPU for rendering means low FPS and slow data; frames from a scripted target may be too easy (tune the hard-case axes); CPU VLM latency is seconds, which is fine for an advisory slot but must be labelled proxy; calibration/test leakage if split by frame; over-claiming from synthetic data.

---

## PART B: PROMPT (paste into any capable coding AI, attach SKYSENTINEL_IDEX_CONTEXT.md, this file and sentinel_airsim.zip)

You are the lead engineer for a solo founder building the AirSim + VLM/VLA part of SkySentinel's iDEX PoC. Read the attached briefing, this file and the code. Then design and build the task described in Part A on the owner's Windows machine (no discrete GPU), using Colab or an alternative GPU only for fine-tuning.

Rules:
1. Do not invent numbers, results, citations or "first" claims. Anything not run is "not run". Say what you could not verify.
2. Keep to the claim ceiling: simulation only, proxy latency, human approval always, no weapons-release or autonomous-engagement content.
3. Work on branch `idex/poc-dec26` in the private repo. No secrets or tokens in files or commits.
4. Treat Part A items marked PROPOSAL as open: ask the owner to confirm label schema and dataset size before building the generator at scale. Items marked VERIFY must be checked against current documentation before use.
5. Every run goes through `RunLogger`. Every VLM call is logged with `vlm_call`; stubs are labelled `stub=True` and never enter results. Ground truth comes only from the simulator.
6. Split train/calibration/test by scenario seed. Report coverage per subgroup, not only on average.
7. Explain any maths from foundations at undergraduate level (symbol names, meanings, use cases).
8. Keep replies short (phone-readable). Format: GATHER / SUMMARIZE (Ground Truth, under 150 words) / DISPATCH, grouped under Rodic / SkySentinel / Research; label research as Technical research or Market research; end with a CURRENT STATE OVERVIEW block.

Deliver, in order, each with an acceptance test and a log you can show:
1. Environment: Python 3.10 venv, `airsim` installed, `pytest` passing, `airsim_smoke_test.py` run live; confirm the log zip.
2. `settings.json` and a scripted `Target1` with five behaviours; 50-clip generator with ground-truth logging; measured seconds per clip.
3. Classical baseline for the same question; zero-shot CPU VLM baseline; both on the same clips.
4. Dataset build (scenario-seed splits), QLoRA fine-tune script for Colab T4 (or the alternative), and export of per-class probabilities for conformal calibration.
5. Conformal calibration and coverage report per subgroup, circuit-breaker test, and the proxy latency table.
6. A one-page results card with negative results included.

Start with step 1 and tell me exactly what you need from the owner.
