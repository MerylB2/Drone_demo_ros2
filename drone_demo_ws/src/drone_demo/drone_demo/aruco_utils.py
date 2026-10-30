"""Outils ArUco sans dépendance ROS (compatibles OpenCV 4.6 d'Ubuntu 24.04 et OpenCV >= 4.7)."""
import math

import cv2
import numpy as np


def get_dictionary(name: str = "DICT_4X4_50"):
    dict_id = getattr(cv2.aruco, name)
    if hasattr(cv2.aruco, "getPredefinedDictionary"):
        return cv2.aruco.getPredefinedDictionary(dict_id)
    return cv2.aruco.Dictionary_get(dict_id)


def generate_marker(dictionary, marker_id: int, side_px: int) -> np.ndarray:
    if hasattr(cv2.aruco, "generateImageMarker"):
        return cv2.aruco.generateImageMarker(dictionary, marker_id, side_px)
    return cv2.aruco.drawMarker(dictionary, marker_id, side_px)


class MarkerDetector:
    """Détecte un marqueur et calcule sa position relative au drone (en mètres).

    Modèle sténopé simple, caméra pointée vers le sol :
      - side_px    : taille apparente du marqueur en pixels
      - altitude   = f * taille_reelle / side_px
      - dx, dy     = décalage horizontal de la cible (x = est / droite image, y = nord / haut image)
    """

    def __init__(self, marker_id=0, marker_size=0.5, fov_deg=80.0, dict_name="DICT_4X4_50"):
        self.marker_id = marker_id
        self.marker_size = marker_size
        self.fov = math.radians(fov_deg)
        dictionary = get_dictionary(dict_name)
        if hasattr(cv2.aruco, "ArucoDetector"):
            self._det = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
            self._detect = self._det.detectMarkers
        else:
            params = cv2.aruco.DetectorParameters_create()
            self._detect = lambda img: cv2.aruco.detectMarkers(img, dictionary, parameters=params)

    def detect(self, gray: np.ndarray):
        corners, ids, _ = self._detect(gray)
        if ids is None:
            return None
        for c, i in zip(corners, ids.flatten()):
            if int(i) != self.marker_id:
                continue
            pts = c.reshape(4, 2)
            side_px = float(np.mean([np.linalg.norm(pts[k] - pts[(k + 1) % 4]) for k in range(4)]))
            if side_px < 1.0:
                return None
            h, w = gray.shape[:2]
            fx = (w / 2.0) / math.tan(self.fov / 2.0)
            u, v = pts.mean(axis=0)
            m_per_px = self.marker_size / side_px
            return {
                "dx": (u - w / 2.0) * m_per_px,
                "dy": -(v - h / 2.0) * m_per_px,
                "z": fx * m_per_px,
                "corners": pts,
                "center_px": (float(u), float(v)),
            }
        return None
