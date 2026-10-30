"""Machine à états d'atterrissage de précision, sans dépendance ROS.

SEARCH  -> monte pour élargir le champ de vision jusqu'à voir la station
ALIGN   -> se centre au-dessus de la station (régulateur PI)
DESCEND -> descend en restant centré ; s'arrête de descendre si l'écart grandit
LAND    -> dernier mètre « à l'aveugle » (la station sort du champ), comme le mode LAND
LANDED  -> moteurs coupés
"""
import math

DEFAULTS = {
    "kp_xy": 0.8,
    "ki_xy": 0.25,
    "max_wind_comp": 0.6,
    "max_xy_speed": 1.0,
    "search_altitude": 10.0,
    "climb_rate": 1.0,
    "align_tolerance": 0.15,
    "align_hold_s": 1.0,
    "descent_rate_fast": 0.7,
    "descent_rate_slow": 0.3,
    "slow_below": 3.0,
    "max_descent_error": 0.4,
    "land_commit_altitude": 0.9,
    "land_rate": 0.4,
    "target_timeout_s": 1.0,
    "fresh_s": 0.25,
}


class MissionLogic:
    def __init__(self, **params):
        self.p = dict(DEFAULTS)
        self.p.update(params)
        self.state = "SEARCH"
        self.last_det = None  # (t, dx, dy, z)
        self.integral = [0.0, 0.0]
        self.aligned_since = None
        self.last_t = None

    def on_detection(self, t, dx, dy, z):
        self.last_det = (t, dx, dy, z)

    def _target(self, t):
        if self.last_det and t - self.last_det[0] <= self.p["target_timeout_s"]:
            return self.last_det
        return None

    def _pi(self, dx, dy, dt):
        p = self.p
        # Anti-emballement : la compensation de vent ne dépasse pas max_wind_comp m/s
        lim = p["max_wind_comp"] / max(p["ki_xy"], 1e-6)
        self.integral[0] = max(-lim, min(lim, self.integral[0] + dx * dt))
        self.integral[1] = max(-lim, min(lim, self.integral[1] + dy * dt))
        vx = p["kp_xy"] * dx + p["ki_xy"] * self.integral[0]
        vy = p["kp_xy"] * dy + p["ki_xy"] * self.integral[1]
        n = math.hypot(vx, vy)
        if n > p["max_xy_speed"]:
            vx, vy = vx * p["max_xy_speed"] / n, vy * p["max_xy_speed"] / n
        return vx, vy

    def _wind_comp(self):
        return self.p["ki_xy"] * self.integral[0], self.p["ki_xy"] * self.integral[1]

    def _go(self, new_state):
        if new_state != self.state:
            self.state = new_state
            if new_state == "SEARCH":
                self.integral = [0.0, 0.0]
            self.aligned_since = None

    def update(self, t, altitude):
        """Retourne la consigne de vitesse (vx, vy, vz) en m/s, repère ENU."""
        p = self.p
        dt = 0.1 if self.last_t is None else max(1e-3, t - self.last_t)
        self.last_t = t
        tgt = self._target(t)
        alt = altitude if altitude is not None else 0.0

        if self.state == "LANDED":
            return 0.0, 0.0, 0.0

        if self.state == "LAND":
            if alt < 0.08:
                self._go("LANDED")
                return 0.0, 0.0, 0.0
            if tgt and t - tgt[0] <= p["fresh_s"]:  # station encore visible : on corrige
                return self._pi(tgt[1], tgt[2], dt) + (-p["land_rate"],)
            # Derniers centimètres sans vision : on garde la compensation de vent apprise
            return self._wind_comp() + (-p["land_rate"],)

        if self.state == "SEARCH":
            if tgt:
                self._go("ALIGN")
            else:
                vz = p["climb_rate"] if alt < p["search_altitude"] else 0.0
                return 0.0, 0.0, vz

        if tgt is None:
            last_err = math.hypot(self.last_det[1], self.last_det[2]) if self.last_det else 1e9
            if (self.state == "DESCEND" and alt < p["land_commit_altitude"] + 0.3
                    and last_err < p["align_tolerance"]):
                self._go("LAND")
                return self._wind_comp() + (-p["land_rate"],)
            # Sinon : remise de gaz, on remonte pour retrouver la station
            self._go("SEARCH")
            return 0.0, 0.0, p["climb_rate"]

        t_det, dx, dy, _ = tgt
        err = math.hypot(dx, dy)
        if t - t_det <= p["fresh_s"]:
            vx, vy = self._pi(dx, dy, dt)
        else:  # détection trop ancienne : on ne corrige pas sur une position périmée
            vx, vy = self._wind_comp()

        if self.state == "ALIGN":
            if err < p["align_tolerance"]:
                self.aligned_since = self.aligned_since or t
                if t - self.aligned_since >= p["align_hold_s"]:
                    self._go("DESCEND")
            else:
                self.aligned_since = None
            return vx, vy, 0.0

        # DESCEND
        if alt < p["land_commit_altitude"]:
            if err < p["align_tolerance"]:
                self._go("LAND")
                return self._wind_comp() + (-p["land_rate"],)
            return vx, vy, 0.0  # trop décalé pour s'engager : on se recentre d'abord
        if err > p["max_descent_error"]:
            vz = 0.0
        elif alt > p["slow_below"]:
            vz = -p["descent_rate_fast"]
        else:
            vz = -p["descent_rate_slow"]
        return vx, vy, vz
