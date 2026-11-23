import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate_clips as g  # noqa: E402
from sentinel_logger import RunLogger, verify_chain  # noqa: E402


def test_specs_are_deterministic_and_cover_all_labels():
    a = [g.make_spec(i, 0) for i in range(400)]
    b = [g.make_spec(i, 0) for i in range(400)]
    assert a == b
    assert {s["label"] for s in a} == set(g.LABELS)
    assert a != [g.make_spec(i, 1) for i in range(400)]


def test_split_ratios_and_label_balance_across_splits():
    specs = [g.make_spec(i, 0) for i in range(4000)]
    c = Counter(s["split"] for s in specs)
    assert 0.65 < c["train"] / 4000 < 0.75
    assert 0.10 < c["cal"] / 4000 < 0.20 and 0.10 < c["test"] / 4000 < 0.20
    for split in ("cal", "test"):
        labs = Counter(s["label"] for s in specs if s["split"] == split)
        assert set(labs) == set(g.LABELS)           # every class present in every split


def test_mock_run_logs_ground_truth_and_passes_qa(tmp_path):
    be = g.MockBackend()
    log = RunLogger(tmp_path, "t")
    results = [g.run_clip(be, log, i, 0) for i in range(60)]
    log.finalize()
    assert all(r["qa"]["ok"] for r in results), [r for r in results if not r["qa"]["ok"]][:2]
    assert verify_chain(log.dir / "events.jsonl")[0]
    ev = [json.loads(l) for l in (log.dir / "events.jsonl").read_text().splitlines()]
    assert sum(e["kind"] == "frame" for e in ev) == 60 * g.CLIP_FRAMES
    sc = [e for e in ev if e["kind"] == "scenario"]
    assert len(sc) == 60 and all(e["data"]["source"] == "script" for e in sc)


def test_qa_catches_a_wrong_label():
    spec = {"label": "APPROACH", "speed": 2.0}
    assert not g.qa_check(spec, (20.0, 0.0, 0.0), (22.0, 0.0, 0.0), 2.0)["ok"]   # actually retreating
    assert g.qa_check(spec, (20.0, 0.0, 0.0), (16.0, 0.0, 0.0), 2.0)["ok"]
    assert not g.qa_check({"label": "LOITER", "speed": 0.1}, (20, 0, 0), (25, 0, 0), 2.0)["ok"]


def test_no_target_is_out_of_view():
    spec = {**g.make_spec(0, 0), "label": "NO_TARGET"}
    t = g.target_start(spec, (0.0, 0.0, -5.0))
    assert t[0] < -100
