"""First thing to run: connect to AirSim, fly a small square, log frames + state.

Windows, AirSim already running (AirSimNH.exe):
    python airsim_smoke_test.py --seconds 40
No AirSim? Test only the logging pipeline with synthetic frames:
    python airsim_smoke_test.py --mock --seconds 10

NOTE: the live-AirSim branch has not been run against a real AirSim in this
repo yet. Treat the first run as the test, and read any error literally.
"""
from __future__ import annotations

import argparse
import random
import time

from sentinel_logger import RunLogger

DEADLINE_MS = 1000.0  # placeholder advisory deadline for pipeline tests only


def stub_vlm(rng: random.Random) -> tuple[str, list[str], float]:
    """Placeholder 'model' used ONLY to test logging and analysis. Not evidence."""
    classes = ["NO_TARGET", "APPROACH", "LOITER", "PASS_BY", "RETREAT"]
    out = rng.choice(classes)
    pset = rng.sample(classes, rng.choice([1, 1, 2, 3]))
    return out, pset, rng.uniform(50, 1500)


def run_mock(log: RunLogger, seconds: int, rng: random.Random) -> None:
    import numpy as np
    for t in range(seconds):
        img = (np.random.default_rng(t).random((120, 160, 3)) * 255).astype("uint8")
        ref = log.frame("front", img)
        log.state(x=float(t), y=0.0, z=-5.0, vx=1.0, vy=0.0, vz=0.0, collided=False, mock=True)
        out, pset, ms = stub_vlm(rng)
        log.scenario(f"mock-{t}", label=rng.choice(["NO_TARGET", "APPROACH"]))
        log.vlm_call(ref, "stub prompt", out, ms, DEADLINE_MS, prediction_set=pset,
                     label=None, model="stub", stub=True)


def run_airsim(log: RunLogger, seconds: int) -> None:
    import airsim  # pip install airsim (see setup notes)

    client = airsim.MultirotorClient()
    client.confirmConnection()
    client.enableApiControl(True)
    client.armDisarm(True)
    client.takeoffAsync().join()
    waypoints = [(10, 0, -5), (10, 10, -5), (0, 10, -5), (0, 0, -5)]
    leg = max(seconds // len(waypoints), 1)
    try:
        for (x, y, z) in waypoints:
            client.moveToPositionAsync(x, y, z, 3)  # new command replaces the old one
            for _ in range(leg):
                time.sleep(1.0)
                with log.timer("airsim_get_images"):
                    resp = client.simGetImages(
                        [airsim.ImageRequest("0", airsim.ImageType.Scene, False, True)])
                if resp and resp[0].image_data_uint8:
                    log.frame("front", bytes(resp[0].image_data_uint8))
                s = client.getMultirotorState()
                p, v = s.kinematics_estimated.position, s.kinematics_estimated.linear_velocity
                log.state(x=p.x_val, y=p.y_val, z=p.z_val, vx=v.x_val, vy=v.y_val, vz=v.z_val,
                          collided=client.simGetCollisionInfo().has_collided)
    finally:
        client.landAsync().join()
        client.armDisarm(False)
        client.enableApiControl(False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=40)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="runs")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    with RunLogger(a.out, "smoke", config=vars(a), seed=a.seed,
                   notes="AirSimNH smoke test" + (" (mock)" if a.mock else "")) as log:
        (run_mock(log, a.seconds, rng) if a.mock else run_airsim(log, a.seconds))
    zip_path = log.bundle(max_mb=30)
    print("run folder:", log.dir)
    print("upload this file:", zip_path)
