import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze_run import analyse, load_lines  # noqa: E402
from sentinel_logger import RunLogger, verify_chain  # noqa: E402


def make_run(tmp_path, frames=3):
    log = RunLogger(tmp_path, "t", config={"a": 1}, seed=7)
    for i in range(frames):
        ref = log.frame("f", b"\x89PNG-fake-%d" % i)
        log.state(x=i)
        with log.timer("stage_a"):
            pass
        log.vlm_call(ref, "p", "APPROACH", 100.0 + i * 1000, 500.0,
                     prediction_set=["APPROACH"] if i % 2 == 0 else ["APPROACH", "LOITER"],
                     label="APPROACH", model="m")
    log.finalize()
    return log


def test_chain_ok_and_summary(tmp_path):
    log = make_run(tmp_path)
    ok, n, _ = verify_chain(log.dir / "events.jsonl")
    assert ok and n > 0
    s = json.loads((log.dir / "summary.json").read_text())
    assert s["chain_ok"] and s["event_counts"]["vlm_call"] == 3
    assert "stage_a" in s["latency_proxy"]


def test_tamper_detected(tmp_path):
    log = make_run(tmp_path)
    p = log.dir / "events.jsonl"
    lines = p.read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if '"vlm_call"' in l)
    assert '"APPROACH"' in lines[i]
    lines[i] = lines[i].replace('"APPROACH"', '"RETREAT"', 1)
    p.write_text("\n".join(lines) + "\n")
    ok, _, msg = verify_chain(p)
    assert not ok and "line" in msg


def test_deleted_line_detected(tmp_path):
    log = make_run(tmp_path)
    p = log.dir / "events.jsonl"
    lines = p.read_text().splitlines()
    del lines[2]
    p.write_text("\n".join(lines) + "\n")
    assert not verify_chain(p)[0]


def test_bundle_and_analysis(tmp_path):
    log = make_run(tmp_path, frames=4)
    z = log.bundle(max_mb=30)
    assert zipfile.is_zipfile(z)
    a = analyse(load_lines(z))
    assert a["chain"]["ok"]
    assert a["vlm_all"]["calls"] == 4
    assert a["vlm_timed_out"]["calls"] + a["vlm_answered_in_time"]["calls"] == 4
    assert a["vlm_all"]["empirical_coverage"] == 1.0


def test_bundle_shrinks_frames_when_over_limit(tmp_path):
    import os
    log = RunLogger(tmp_path, "big")
    for i in range(8):
        log.frame("f", os.urandom(200_000))  # incompressible
    log.finalize()
    z = log.bundle(max_mb=0.5)
    with zipfile.ZipFile(z) as zf:
        n = sum("/frames/" in x for x in zf.namelist())
    assert n < 8
    assert verify_chain(log.dir / "events.jsonl")[0]


def test_stub_rows_excluded_from_analysis(tmp_path):
    log = RunLogger(tmp_path, "s")
    ref = log.frame("f", b"x")
    log.vlm_call(ref, "p", "A", 10, 500, prediction_set=["A"], label="A", stub=True)
    log.finalize()
    a = analyse(load_lines(log.dir))
    assert a["vlm_all"]["calls"] == 0
