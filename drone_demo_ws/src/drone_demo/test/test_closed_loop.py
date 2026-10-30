"""Test boucle fermée SANS ROS : simulateur + vision + mission.

Lancer :  python3 -m pytest test/  (depuis le dossier du package)
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from drone_demo.aruco_utils import MarkerDetector  # noqa: E402
from drone_demo.mission_core import MissionLogic  # noqa: E402
from drone_demo.sim_core import SimDrone  # noqa: E402


def run(start=(5.0, 4.0, 4.0), drift=0.15, seed=0, duration=150.0, verbose=False):
    sim = SimDrone(start=start, drift=drift, seed=seed)
    det = MarkerDetector()
    mission = MissionLogic()
    dt, t = 0.02, 0.0
    states = [mission.state]
    for k in range(int(duration / dt)):
        t = k * dt
        if k % 3 == 0:  # caméra ~15 Hz
            d = det.detect(sim.render())
            if d:
                mission.on_detection(t, d["dx"], d["dy"], d["z"])
        if k % 5 == 0:  # mission 10 Hz
            sim.cmd[:] = mission.update(t, sim.pos[2])
            if mission.state != states[-1]:
                states.append(mission.state)
                if verbose:
                    print(f"t={t:6.1f}s  {mission.state:8s} pos=({sim.pos[0]:+.2f}, {sim.pos[1]:+.2f}, {sim.pos[2]:.2f})")
        sim.step(dt)
        if mission.state == "LANDED":
            break
    return sim, states, t


def test_precision_landing():
    sim, states, _ = run()
    assert states[0] == "SEARCH" and states[-1] == "LANDED"
    assert sim.landed
    assert math.hypot(sim.pos[0], sim.pos[1]) < 0.3


if __name__ == "__main__":
    for seed in range(5):
        sim, states, t = run(seed=seed, verbose=(seed == 0))
        print(f"seed {seed}: {' -> '.join(states)} en {t:.1f}s, erreur finale "
              f"{math.hypot(sim.pos[0], sim.pos[1]) * 100:.0f} cm")
