"""Analyse a SkySentinel run folder or its .zip bundle.

Usage:  python analyze_run.py runs/<run-folder>      or      python analyze_run.py <bundle>.zip

Prints: chain check, event counts, proxy latency, VLM timeout/fallback/escalation
rates, and (when ground-truth labels are present) accuracy and set coverage,
overall and per subgroup (answered in time / timed out). Stub rows are excluded.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from sentinel_logger import _pct, verify_lines


def load_lines(path: Path) -> list[str]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.endswith("events.jsonl"))
            return z.read(name).decode("utf-8").splitlines()
    return (path / "events.jsonl").read_text(encoding="utf-8").splitlines()


def analyse(lines: list[str]) -> dict:
    ok, n, msg = verify_lines(lines)
    events = [json.loads(l) for l in lines if l.strip()]
    counts: dict[str, int] = {}
    lat: dict[str, list[float]] = {}
    vlm = []
    for e in events:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        d = e["data"]
        if e["kind"] == "latency":
            lat.setdefault(d["stage"], []).append(d["ms"])
        if e["kind"] == "vlm_call" and not d.get("stub"):
            vlm.append(d)

    def block(rows: list[dict]) -> dict:
        labelled = [r for r in rows if r.get("label") is not None]
        with_set = [r for r in labelled if r.get("prediction_set") is not None]
        out = {"calls": len(rows)}
        if rows:
            out["timeout_rate"] = round(sum(r["timed_out"] for r in rows) / len(rows), 4)
            sets = [r for r in rows if r.get("prediction_set") is not None]
            if sets:
                out["escalation_rate"] = round(
                    sum(len(r["prediction_set"]) != 1 for r in sets) / len(sets), 4)
                out["mean_set_size"] = round(sum(len(r["prediction_set"]) for r in sets) / len(sets), 4)
        if labelled:
            out["top1_accuracy"] = round(
                sum(r["output"] == r["label"] for r in labelled) / len(labelled), 4)
        if with_set:
            out["empirical_coverage"] = round(
                sum(r["label"] in r["prediction_set"] for r in with_set) / len(with_set), 4)
            out["coverage_n"] = len(with_set)
        return out

    return {
        "chain": {"ok": ok, "events": n, "message": msg},
        "event_counts": counts,
        "latency_proxy_ms": {s: {"n": len(v), "p50": round(_pct(v, 50), 2),
                                 "p95": round(_pct(v, 95), 2), "max": round(max(v), 2)}
                             for s, v in lat.items()},
        "vlm_all": block(vlm),
        "vlm_answered_in_time": block([r for r in vlm if not r["timed_out"]]),
        "vlm_timed_out": block([r for r in vlm if r["timed_out"]]),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(analyse(load_lines(Path(sys.argv[1]))), indent=2))
