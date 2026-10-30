"""Drone simulé très simplifié (mode quad, vu de dessus) + caméra verticale.

Aucune dépendance ROS : la même classe sert au nœud ROS et au test hors ligne.
Repère : x = est, y = nord, z = haut (ENU, comme MAVROS). La station est en (0, 0).
"""
import math

import cv2
import numpy as np

from .aruco_utils import generate_marker, get_dictionary


class SimDrone:
    def __init__(self, start=(4.0, 3.0, 6.0), marker_id=0, marker_size=0.5,
                 fov_deg=80.0, width=640, height=480, drift=0.15, gust=0.1, seed=0):
        self.pos = np.array(start, dtype=float)
        self.vel = np.zeros(3)
        self.cmd = np.zeros(3)
        # Dérive résiduelle : en mode GUIDED, l'autopilote compense déjà le vent avec le GPS,
        # il ne reste qu'une erreur de suivi de quelques dizaines de cm/s.
        self.drift = np.zeros(2)
        self.drift_max = drift
        self.gust = gust  # vitesse de variation de la dérive
        self.rng = np.random.default_rng(seed)
        self.w, self.h = width, height
        self.fx = (width / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
        self.landed = False

        # Station : marqueur noir de `marker_size` m entouré d'une marge blanche
        marker_px = 240
        border = marker_px // 5
        marker = generate_marker(get_dictionary(), marker_id, marker_px)
        self.pad = cv2.copyMakeBorder(marker, border, border, border, border,
                                      cv2.BORDER_CONSTANT, value=255)
        self.pad_m_per_px = marker_size / marker_px

    def step(self, dt: float):
        if self.landed:
            return
        tau = 0.4  # temps de réponse de l'autopilote
        self.vel += (self.cmd - self.vel) * min(dt / tau, 1.0)
        # Dérive : marche aléatoire bornée
        self.drift += self.rng.normal(0.0, self.gust, 2) * math.sqrt(dt)
        self.drift = np.clip(self.drift, -self.drift_max, self.drift_max)
        self.pos[:2] += (self.vel[:2] + self.drift) * dt
        self.pos[2] += self.vel[2] * dt
        if self.pos[2] <= 0.05:
            self.pos[2] = 0.0
            self.vel[:] = 0.0
            self.landed = True

    def render(self) -> np.ndarray:
        """Image mono8 vue par la caméra pointée vers le sol."""
        z = max(self.pos[2], 0.05)
        ppm = self.fx / z  # pixels par mètre au sol
        cx, cy = self.w / 2.0, self.h / 2.0
        img = np.full((self.h, self.w), 105, np.uint8)

        # Quadrillage d'un mètre (repère visuel du mouvement)
        half_w, half_h = cx / ppm, cy / ppm
        for gx in range(math.floor(self.pos[0] - half_w), math.ceil(self.pos[0] + half_w) + 1):
            u = int(round(cx + (gx - self.pos[0]) * ppm))
            cv2.line(img, (u, 0), (u, self.h - 1), 88, 1)
        for gy in range(math.floor(self.pos[1] - half_h), math.ceil(self.pos[1] + half_h) + 1):
            v = int(round(cy - (gy - self.pos[1]) * ppm))
            cv2.line(img, (0, v), (self.w - 1, v), 88, 1)

        # Projection de la station (warpAffine gère le zoom et le recadrage)
        scale = self.pad_m_per_px * ppm
        n = self.pad.shape[0]
        u0 = cx + (0.0 - self.pos[0]) * ppm - scale * n / 2.0
        v0 = cy + (self.pos[1] - 0.0) * ppm - scale * n / 2.0
        M = np.float32([[scale, 0, u0], [0, scale, v0]])
        warped = cv2.warpAffine(self.pad, M, (self.w, self.h), flags=cv2.INTER_NEAREST)
        mask = cv2.warpAffine(np.ones_like(self.pad), M, (self.w, self.h), flags=cv2.INTER_NEAREST)
        img[mask > 0] = warped[mask > 0]

        # Bruit capteur + léger flou
        noisy = img.astype(np.int16) + self.rng.normal(0, 6, img.shape).astype(np.int16)
        img = np.clip(noisy, 0, 255).astype(np.uint8)
        return cv2.GaussianBlur(img, (3, 3), 0)
