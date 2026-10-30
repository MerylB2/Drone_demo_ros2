"""Génère le marqueur à imprimer pour tester avec une vraie webcam.

ros2 run drone_demo make_marker --id 0 --out station_marker.png
"""
import argparse

import cv2

from .aruco_utils import generate_marker, get_dictionary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, default=0)
    ap.add_argument("--px", type=int, default=800)
    ap.add_argument("--out", default="station_marker.png")
    a = ap.parse_args()
    img = generate_marker(get_dictionary(), a.id, a.px)
    b = a.px // 5  # marge blanche indispensable à la détection
    img = cv2.copyMakeBorder(img, b, b, b, b, cv2.BORDER_CONSTANT, value=255)
    cv2.imwrite(a.out, img)
    print(f"{a.out} écrit. Mesurez le carré NOIR une fois imprimé et reportez-le dans marker_size.")
