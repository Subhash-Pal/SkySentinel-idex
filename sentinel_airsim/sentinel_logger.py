"""Structured, tamper-evident run logging for SkySentinel AirSim + VLM/VLA runs.

One run = one folder:
    manifest.json   environment, versions, config hash, seed (no hostname, no secrets)
    events.jsonl    one JSON event per line, hash-chained (each line stores prev hash)
    frames/         saved camera frames (hash of each file is logged)
    summary.json    written by finalize(): counts, latency percentiles, chain check

All latency numbers are labelled proxy=True by default: they are measured on a
development machine (CPU / Colab), not on edge hardware.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import math
import platform
import subprocess
import sys
import time
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = "1.0"
GENESIS = "0" * 64


def _canon(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, default=str)


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pkg(name: str) -> str | None:
    try:
        return md.version(name)
    except Exception:
        return None


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p / 100.0
    lo = math.floor(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def verify_lines(lines: Iterable[str]) -> tuple[bool, int, str]:
    """Check the hash chain. Returns (ok, number_of_events, message)."""
    prev = GENESIS
    n = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            claimed = rec.pop("hash")
        except Exception:
            return False, n, f"line {i}: not valid JSON or missing hash"
        if rec.get("seq") != n:
            return False, n, f"line {i}: sequence break (expected {n}, got {rec.get('seq')})"
        if rec.get("prev") != prev:
            return False, n, f"line {i}: previous-hash mismatch"
        if _h(_canon(rec)) != claimed:
            return False, n, f"line {i}: content does not match its hash"
        prev = claimed
        n += 1
    return True, n, "chain intact"


def verify_chain(events_path: str | Path) -> tuple[bool, int, str]:
    with open(events_path, "r", encoding="utf-8") as fh:
        return verify_lines(fh)


class RunLogger:
    def __init__(self, root: str | Path = "runs", run_name: str = "run",
                 config: dict | None = None, seed: int | None = None, notes: str = ""):
        stamp = time.strftime("%Y%m%dT%H%M%S")
        self.run_id = f"{stamp}-{uuid.uuid4().hex[:6]}"
        self.dir = Path(root) / f"{run_name}-{self.run_id}"
        (self.dir / "frames").mkdir(parents=True, exist_ok=False)
        self._fh = open(self.dir / "events.jsonl", "w", encoding="utf-8")
        self._prev = GENESIS
        self._seq = 0
        self._t0 = time.perf_counter()
        self._lat: dict[str, list[float]] = {}
        self._kinds: dict[str, int] = {}
        self._closed = False
        cfg = config or {}
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {p: _pkg(p) for p in
                         ("airsim", "numpy", "torch", "transformers", "peft", "pillow", "opencv-python")},
            "git_commit": _git_commit(),
            "seed": seed,
            "config": cfg,
            "config_sha256": _h(_canon(cfg)),
            "notes": notes,
            "claim_label": "simulation only; latency is proxy (not edge-measured)",
        }
        (self.dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        self.event("run_start", run_id=self.run_id)

    # ---- core -------------------------------------------------------------
    def event(self, kind: str, **data: Any) -> int:
        if self._closed:
            raise RuntimeError("logger is closed")
        rec = {
            "seq": self._seq,
            "t_wall": time.time(),
            "t_run": round(time.perf_counter() - self._t0, 6),
            "kind": kind,
            "data": data,
            "prev": self._prev,
        }
        rec["hash"] = _h(_canon(rec))
        self._fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        self._fh.flush()
        self._prev = rec["hash"]
        self._kinds[kind] = self._kinds.get(kind, 0) + 1
        self._seq += 1
        return rec["seq"]

    def frame(self, name: str, image: Any, ext: str = "png") -> str:
        """Save a frame (encoded bytes, or a numpy array) and log its hash."""
        path = self.dir / "frames" / f"{self._seq:07d}_{name}.{ext}"
        if isinstance(image, (bytes, bytearray)):
            path.write_bytes(bytes(image))
        else:
            try:
                from PIL import Image
                Image.fromarray(image).save(path)
            except ImportError:
                import numpy as np
                path = path.with_suffix(".npy")
                np.save(path, image)
        data = path.read_bytes()
        rel = path.relative_to(self.dir).as_posix()
        self.event("frame", name=name, file=rel,
                   sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        return rel

    @contextmanager
    def timer(self, stage: str, proxy: bool = True, **extra: Any) -> Iterator[None]:
        t = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - t) * 1000.0
            self._lat.setdefault(stage, []).append(ms)
            self.event("latency", stage=stage, ms=round(ms, 3), proxy=proxy, **extra)

    # ---- domain helpers ---------------------------------------------------
    def scenario(self, scenario_id: str, label: str, **truth: Any) -> None:
        """Ground truth from the simulator (e.g. scripted target behaviour)."""
        self.event("scenario", scenario_id=scenario_id, label=label, **truth)

    def state(self, **s: Any) -> None:
        """Vehicle state sample (position, velocity, collision flag ...)."""
        self.event("state", **s)

    def vlm_call(self, frame: str, prompt: str, output: Any, latency_ms: float,
                 deadline_ms: float, prediction_set: list | None = None,
                 label: str | None = None, model: str | None = None,
                 stub: bool = False, **extra: Any) -> None:
        """One advisory-model call. timed_out/fallback_used are derived here.

        stub=True marks a placeholder model used only to test the pipeline.
        Stub rows must never enter evidence numbers.
        """
        timed_out = latency_ms > deadline_ms
        self._lat.setdefault("vlm", []).append(latency_ms)
        self.event("vlm_call", frame=frame, prompt=prompt, output=output,
                   latency_ms=round(latency_ms, 3), deadline_ms=deadline_ms,
                   timed_out=timed_out, fallback_used=timed_out,
                   prediction_set=prediction_set, label=label, model=model,
                   proxy=True, stub=stub, **extra)

    def gate_verdict(self, gate: str, verdict: str, reason: str, **extra: Any) -> None:
        self.event("gate_verdict", gate=gate, verdict=verdict, reason=reason, **extra)

    def escalation(self, reason: str, **extra: Any) -> None:
        self.event("escalation", reason=reason, **extra)

    # ---- finish -----------------------------------------------------------
    def finalize(self) -> Path:
        if self._closed:
            return self.dir / "summary.json"
        self.event("run_end")
        self._fh.close()
        self._closed = True
        ok, n, msg = verify_chain(self.dir / "events.jsonl")
        lat = {
            stage: {"n": len(v), "p50_ms": round(_pct(v, 50), 3),
                    "p95_ms": round(_pct(v, 95), 3), "max_ms": round(max(v), 3)}
            for stage, v in self._lat.items() if v
        }
        summary = {
            "run_id": self.run_id,
            "events": n,
            "event_counts": self._kinds,
            "latency_proxy": lat,
            "chain_ok": ok,
            "chain_message": msg,
            "duration_s": round(time.perf_counter() - self._t0, 3),
        }
        out = self.dir / "summary.json"
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return out

    def bundle(self, max_mb: float = 30.0) -> Path:
        """Zip the run for upload. If too big, keep every 2nd, 4th ... frame."""
        if not self._closed:
            self.finalize()
        zip_path = Path(str(self.dir) + ".zip")
        frames = sorted((self.dir / "frames").glob("*"))
        stride = 1
        while True:
            self._write_zip(zip_path, frames[::stride], stride, len(frames))
            too_big = zip_path.stat().st_size > max_mb * 1024 * 1024
            if not too_big or stride >= max(len(frames), 1):
                break
            stride *= 2
        return zip_path

    def _write_zip(self, zip_path: Path, frames: list[Path], stride: int, total: int) -> None:
        root = self.dir.name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for name in ("manifest.json", "events.jsonl", "summary.json"):
                p = self.dir / name
                if p.exists():
                    z.write(p, f"{root}/{name}")
            for f in frames:
                z.write(f, f"{root}/frames/{f.name}")
            z.writestr(f"{root}/BUNDLE_NOTE.txt",
                       f"frame_stride={stride}; frames_included={len(frames)} of {total}. "
                       "events.jsonl still lists every frame hash.\n")

    def __enter__(self) -> "RunLogger":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.finalize()
