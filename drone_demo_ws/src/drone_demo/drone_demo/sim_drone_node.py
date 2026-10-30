"""Nœud « sim_drone » : remplace le drone réel + la caméra pendant le développement.

Publie   /camera/image_raw  (sensor_msgs/Image)          -> comme la caméra du Pi 5
         /drone/pose        (geometry_msgs/PoseStamped)   -> même type que /mavros/local_position/pose
Écoute   /cmd_vel           (geometry_msgs/Twist, ENU)    -> même type que /mavros/setpoint_velocity/cmd_vel_unstamped
"""
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped, Twist
from rclpy.node import Node
from sensor_msgs.msg import Image

from .sim_core import SimDrone


class SimDroneNode(Node):
    def __init__(self):
        super().__init__("sim_drone")
        p = {
            "start_x": 5.0, "start_y": 4.0, "start_z": 4.0,
            "drift": 0.15, "marker_id": 0, "marker_size": 0.5, "fov_deg": 80.0,
            "physics_hz": 50.0, "camera_hz": 15.0, "cmd_timeout_s": 0.5,
        }
        for name, default in p.items():
            self.declare_parameter(name, default)
        g = lambda n: self.get_parameter(n).value  # noqa: E731

        self.sim = SimDrone(start=(g("start_x"), g("start_y"), g("start_z")),
                            marker_id=int(g("marker_id")), marker_size=g("marker_size"),
                            fov_deg=g("fov_deg"), drift=g("drift"))
        self.cmd_timeout = g("cmd_timeout_s")
        self.last_cmd_time = None
        self.bridge = CvBridge()

        self.create_subscription(Twist, "/cmd_vel", self.on_cmd, 10)
        self.img_pub = self.create_publisher(Image, "/camera/image_raw", 5)
        self.pose_pub = self.create_publisher(PoseStamped, "/drone/pose", 10)

        self.dt = 1.0 / g("physics_hz")
        self.create_timer(self.dt, self.physics_step)
        self.create_timer(1.0 / g("camera_hz"), self.publish_image)
        x, y, z = (float(v) for v in self.sim.pos)
        self.get_logger().info(f"Drone simulé au départ de x={x} m, y={y} m, z={z} m")

    def on_cmd(self, msg: Twist):
        self.sim.cmd[:] = (msg.linear.x, msg.linear.y, msg.linear.z)
        self.last_cmd_time = self.get_clock().now()

    def physics_step(self):
        # Sécurité : sans consigne récente, l'autopilote passe en stationnaire
        now = self.get_clock().now()
        if self.last_cmd_time is None or (now - self.last_cmd_time).nanoseconds * 1e-9 > self.cmd_timeout:
            self.sim.cmd[:] = 0.0
        was_landed = self.sim.landed
        self.sim.step(self.dt)
        if self.sim.landed and not was_landed:
            self.get_logger().info(f"Posé en x={self.sim.pos[0]:+.2f} m, y={self.sim.pos[1]:+.2f} m")

        msg = PoseStamped()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = map(float, self.sim.pos)
        msg.pose.orientation.w = 1.0
        self.pose_pub.publish(msg)

    def publish_image(self):
        msg = self.bridge.cv2_to_imgmsg(self.sim.render(), encoding="mono8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera"
        self.img_pub.publish(msg)


def main():
    rclpy.init()
    node = SimDroneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
