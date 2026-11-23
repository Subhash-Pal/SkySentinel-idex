"""Scripted-target clip generator for the Feature 1 advisory-slot dataset (IDX-06).

Two AirSim drones: Drone1 (observer, hovers, its front camera is the sensor) and
Target1 (scripted). Each clip = 3 frames, 1 s apart, with ground truth taken ONLY
from the script (never from a model). Labels:
    NO_TARGET, APPROACH, LOITER, PASS_BY, RETREAT        (PROPOSAL, owner may change)

Modes
    --mock         no AirSim; exact fake physics; tests the generator logic
    --calibrate    live AirSim: check frame offsets and teleport behaviour, then stop
    (default)      live AirSim: generate --clips clips

settings.json must define both vehicles with the SAME offsets as OFFSETS below
(see settings_two_drone.json). The live branch has NOT been run against a real
AirSim yet: run --calibrate first and read its output literally.
"""
from __future__ import annotations

import argparse
import math
import random
import time
from collections import Counter

from sentinel_logger import RunLogger

LABELS = ["NO_TARGET", "APPROACH", "LOITER", "PASS_BY", "RETREAT"]
OBSERVER, TARGET = "Drone1", "Target1"
OFFSETS = {OBSERVER: (0.0, 0.0, 0.0), TARGET: (15.0, 0.0, 0.0)}  # = settings.json X,Y,Z
HOVER_Z = -5.0          # NED: negative is up
CLIP_FRAMES, FRAME_GAP_S, CLIP_T = 3, 1.0, 2.0
DISTANCES = [10.0, 20.0, 35.0, 50.0]


# ---------- pure logic (tested) -------------------------------------------
def split_for(idx: int) -> str:
    """Deterministic 70/15/15 split by clip index (each clip has its own seed)."""
    r = ((idx * 2654435761) >> 8) % 20
    return "train" if r < 14 else "cal" if r < 17 else "test"


def distance_band(d: float) -> str:
    return "near" if d < 15 else "mid" if d < 30 else "far" if d < 45 else "very_far"


def make_spec(idx: int, base_seed: int) -> dict:
    rng = random.Random(base_seed * 1_000_003 + idx)
    label = rng.choice(LABELS)
    d0 = rng.choice(DISTANCES) + rng.uniform(-2.0, 2.0)
    side = rng.choice([-1, 1])
    moving = label in ("APPROACH", "RETREAT", "PASS_BY")
    speed = rng.choice([1.0, 2.0, 4.0]) if moving else rng.uniform(0.0, 0.3)
    lateral = (-side * 0.4 * d0) if label == "PASS_BY" else rng.uniform(-0.15 * d0, 0.15 * d0)
    return {"clip": idx, "label": label, "split": split_for(idx), "d0": d0,
            "band": distance_band(d0), "side": side, "speed": speed, "lateral": lateral,
            "dz": rng.uniform(-1.5, 1.5), "drift": (rng.uniform(-1, 1), rng.uniform(-1, 1))}


def target_start(spec: dict, obs: tuple) -> tuple:
    if spec["label"] == "NO_TARGET":
        return (obs[0] - 150.0, obs[1], obs[2])
    return (obs[0] + spec["d0"], obs[1] + spec["lateral"], obs[2] + spec["dz"])


def target_velocity(spec: dict, obs: tuple, tpos: tuple) -> tuple:
    dx, dy = tpos[0] - obs[0], tpos[1] - obs[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n                      # unit vector observer -> target
    s, lab = spec["speed"], spec["label"]
    if lab == "APPROACH":
        return (-ux * s, -uy * s, 0.0)
    if lab == "RETREAT":
        return (ux * s, uy * s, 0.0)
    if lab == "PASS_BY":
        return (0.0, spec["side"] * s, 0.0)
    return (spec["drift"][0] * s, spec["drift"][1] * s, 0.0)   # LOITER / NO_TARGET


def qa_check(spec: dict, rel0: tuple, rel2: tuple, T: float) -> dict:
    """Check the measured motion agrees with the script. Never used as a label."""
    dx, dy = rel2[0] - rel0[0], rel2[1] - rel0[1]
    n = math.hypot(rel0[0], rel0[1]) or 1.0
    ux, uy = rel0[0] / n, rel0[1] / n
    radial = dx * ux + dy * uy
    tang = abs(-dx * uy + dy * ux)
    disp = math.hypot(dx, dy)
    s, lab = spec["speed"], spec["label"]
    half = 0.5 * s * T
    ok = {"APPROACH": radial < -half, "RETREAT": radial > half,
          "PASS_BY": tang > half and abs(radial) < tang,
          "LOITER": disp < 1.0, "NO_TARGET": n > 100.0}[lab]
    return {"ok": bool(ok), "radial_m": round(radial, 3), "tangential_m": round(tang, 3),
            "start_range_m": round(n, 2)}


def rng3(a: tuple, b: tuple) -> tuple:
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


# ---------- backends ---------------------------------------------------------
class MockBackend:
    """Exact kinematics on a fake clock. Tests logic only; says nothing about AirSim."""

    def __init__(self):
        self.t = 0.0
        self.pos = {OBSERVER: (0.0, 0.0, HOVER_Z), TARGET: (15.0, 0.0, HOVER_Z)}
        self.vel = (0.0, 0.0, 0.0)
        self.until = 0.0

    def now(self): return self.t

    def sleep(self, s): self._advance(s)

    def _advance(self, s):
        step = max(0.0, min(s, self.until - self.t)) if self.until > self.t else 0.0
        p = self.pos[TARGET]
        self.pos[TARGET] = tuple(p[i] + self.vel[i] * step for i in range(3))
        self.t += s

    def place_target(self, w): self.pos[TARGET] = tuple(w); self.vel = (0.0, 0.0, 0.0)

    def set_target_velocity(self, v, duration):
        self.vel, self.until = tuple(v), self.t + duration

    def pose(self, who): return self.pos[who]

    def frame(self): self._advance(0.4); return b"\x89PNG\r\n\x1a\nmock"

    def close(self): pass


class AirSimBackend:
    def __init__(self, pose_frame: str = "world"):
        import airsim
        self.a, self.pose_frame = airsim, pose_frame
        self.c = airsim.MultirotorClient()
        self.c.confirmConnection()
        for v in (OBSERVER, TARGET):
            self.c.enableApiControl(True, v)
            self.c.armDisarm(True, v)
        f1 = self.c.takeoffAsync(vehicle_name=OBSERVER)
        f2 = self.c.takeoffAsync(vehicle_name=TARGET)
        f1.join(); f2.join()
        self.c.moveToPositionAsync(0, 0, HOVER_Z, 2, vehicle_name=OBSERVER).join()

    def now(self): return time.perf_counter()

    def sleep(self, s): time.sleep(s)

    def pose(self, who):
        p = self.c.getMultirotorState(vehicle_name=who).kinematics_estimated.position
        o = OFFSETS[who]
        return (p.x_val + o[0], p.y_val + o[1], p.z_val + o[2])

    def place_target(self, w):
        o = OFFSETS[TARGET]
        x, y, z = (w if self.pose_frame == "world" else (w[0] - o[0], w[1] - o[1], w[2] - o[2]))
        pose = self.a.Pose(self.a.Vector3r(x, y, z), self.a.to_quaternion(0, 0, 0))
        self.c.simSetVehiclePose(pose, True, vehicle_name=TARGET)
        self.c.moveByVelocityAsync(0, 0, 0, 0.5, vehicle_name=TARGET)

    def set_target_velocity(self, v, duration):
        self.c.moveByVelocityAsync(v[0], v[1], v[2], duration, vehicle_name=TARGET)

    def frame(self):
        r = self.c.simGetImages(
            [self.a.ImageRequest("0", self.a.ImageType.Scene, False, True)], vehicle_name=OBSERVER)
        return bytes(r[0].image_data_uint8)

    def close(self):
        for v in (OBSERVER, TARGET):
            self.c.landAsync(vehicle_name=v).join()
            self.c.armDisarm(False, v)
            self.c.enableApiControl(False, v)


# ---------- generation -------------------------------------------------------
def run_clip(be, log: RunLogger, idx: int, base_seed: int) -> dict:
    spec = make_spec(idx, base_seed)
    t_clip = be.now()
    obs0 = be.pose(OBSERVER)
    tpos = target_start(spec, obs0)
    be.place_target(tpos)
    be.sleep(0.5)
    vel = target_velocity(spec, obs0, tpos)
    be.set_target_velocity(vel, CLIP_T + 1.0)
    t_start, samples = be.now(), []
    for k in range(CLIP_FRAMES):
        wait = t_start + k * FRAME_GAP_S - be.now()
        if wait > 0:
            be.sleep(wait)
        ref = log.frame(f"c{idx:05d}_f{k}", be.frame())
        o, t = be.pose(OBSERVER), be.pose(TARGET)
        rel = rng3(o, t)
        samples.append({"k": k, "t_s": round(be.now() - t_start, 3), "frame": ref,
                        "obs": [round(x, 3) for x in o], "tgt": [round(x, 3) for x in t],
                        "range_m": round(math.hypot(rel[0], rel[1]), 3)})
    be.set_target_velocity((0.0, 0.0, 0.0), 0.5)
    r0, r2 = rng3(samples[0]["obs"], samples[0]["tgt"]), rng3(samples[-1]["obs"], samples[-1]["tgt"])
    qa = qa_check(spec, r0, r2, samples[-1]["t_s"] - samples[0]["t_s"])
    log.scenario(f"clip-{idx:05d}", spec["label"], split=spec["split"], band=spec["band"],
                 d0=round(spec["d0"], 2), speed=round(spec["speed"], 2), side=spec["side"],
                 planned_velocity=[round(x, 3) for x in vel], source="script")
    log.event("clip_samples", clip=f"clip-{idx:05d}", samples=samples)
    log.event("clip_qa", clip=f"clip-{idx:05d}", **qa, seconds=round(be.now() - t_clip, 2))
    return {"spec": spec, "qa": qa}


def calibrate(be) -> None:
    obs, tgt = be.pose(OBSERVER), be.pose(TARGET)
    print("observer world pos:", [round(x, 2) for x in obs])
    print("target   world pos:", [round(x, 2) for x in tgt], "(expected about", OFFSETS[TARGET], "+ hover)")
    want = (obs[0] + 20.0, obs[1], obs[2])
    be.place_target(want)
    be.sleep(1.0)
    got = be.pose(TARGET)
    err = math.dist(want, got)
    print("teleport target to", want, "-> read back", [round(x, 2) for x in got], "error m:", round(err, 2))
    print("RESULT:", "pose frame OK" if err < 2.0 else
          "MISMATCH: rerun with --pose-frame local, or fix OFFSETS to match settings.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="runs")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--pose-frame", choices=["world", "local"], default="world")
    a = ap.parse_args()
    be = MockBackend() if a.mock else AirSimBackend(a.pose_frame)
    try:
        if a.calibrate:
            calibrate(be)
            return
        with RunLogger(a.out, "clips", config=vars(a), seed=a.seed,
                       notes="scripted-target clips" + (" (mock)" if a.mock else "")) as log:
            labels, splits, bad = Counter(), Counter(), []
            t0 = time.perf_counter()
            for i in range(a.clips):
                r = run_clip(be, log, i, a.seed)
                labels[r["spec"]["label"]] += 1
                splits[r["spec"]["split"]] += 1
                if not r["qa"]["ok"]:
                    bad.append(i)
            secs = (time.perf_counter() - t0) / max(a.clips, 1)
            log.event("generation_summary", clips=a.clips, labels=dict(labels),
                      splits=dict(splits), qa_failed=bad, wall_seconds_per_clip=round(secs, 3))
        zp = log.bundle(max_mb=30)
        print("labels:", dict(labels), "splits:", dict(splits))
        print("QA failed clips:", bad, "| wall seconds per clip:", round(secs, 2))
        print("run folder:", log.dir)
        print("upload this file:", zp)
    finally:
        be.close()


if __name__ == "__main__":
    main()
