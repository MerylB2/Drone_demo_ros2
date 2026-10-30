"""Nœud « aruco_detector » : le pôle vision.

Écoute   /camera/image_raw  (sensor_msgs/Image, simulée OU vraie caméra)
Publie   /landing_target    (geometry_msgs/PointStamped) x, y = décalage de la station en m (ENU), z = altitude estimée
         /camera/debug      (sensor_msgs/Image) image annotée, à regarder avec rqt_image_view
"""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.node import Node
from sensor_msgs.msg import Image

from .aruco_utils import MarkerDetector


class ArucoDetectorNode(Node):
    def __init__(self):
        super().__init__("aruco_detector")
        for name, default in {"marker_id": 0, "marker_size": 0.5, "fov_deg": 80.0,
                              "dictionary": "DICT_4X4_50"}.items():
            self.declare_parameter(name, default)
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        self.detector = MarkerDetector(int(g("marker_id")), g("marker_size"), g("fov_deg"), g("dictionary"))
        self.bridge = CvBridge()

        self.create_subscription(Image, "/camera/image_raw", self.on_image, 5)
        self.target_pub = self.create_publisher(PointStamped, "/landing_target", 10)
        self.debug_pub = self.create_publisher(Image, "/camera/debug", 5)
        self.get_logger().info(f"Recherche du marqueur {g('marker_id')} ({g('marker_size')} m)")

    def on_image(self, msg: Image):
        gray = self.bridge.imgmsg_to_cv2(msg, desired_encoding="mono8")
        det = self.detector.detect(gray)

        dbg = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        h, w = gray.shape
        cv2.drawMarker(dbg, (w // 2, h // 2), (255, 200, 0), cv2.MARKER_CROSS, 30, 2)

        if det:
            out = PointStamped()
            out.header = msg.header
            out.point.x, out.point.y, out.point.z = float(det["dx"]), float(det["dy"]), float(det["z"])
            self.target_pub.publish(out)
            cv2.polylines(dbg, [det["corners"].astype(np.int32)], True, (0, 255, 0), 2)
            u, v = map(int, det["center_px"])
            cv2.line(dbg, (w // 2, h // 2), (u, v), (0, 255, 0), 1)
            txt = f"dx={det['dx']:+.2f} dy={det['dy']:+.2f} z={det['z']:.1f} m"
            cv2.putText(dbg, txt, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(dbg, "station non vue", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        dbg_msg = self.bridge.cv2_to_imgmsg(dbg, encoding="bgr8")
        dbg_msg.header = msg.header
        self.debug_pub.publish(dbg_msg)


def main():
    rclpy.init()
    node = ArucoDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
