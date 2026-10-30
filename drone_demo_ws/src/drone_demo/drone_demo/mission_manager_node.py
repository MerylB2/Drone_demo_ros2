"""Nœud « mission_manager » : le pôle décision.

Écoute   /landing_target  (geometry_msgs/PointStamped)
         /drone/pose      (geometry_msgs/PoseStamped)  -> en vrai : /mavros/local_position/pose
Publie   /cmd_vel         (geometry_msgs/Twist, ENU)   -> en vrai : /mavros/setpoint_velocity/cmd_vel_unstamped
         /mission/state   (std_msgs/String)
"""
import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from rclpy.node import Node
from std_msgs.msg import String

from .mission_core import DEFAULTS, MissionLogic


class MissionManagerNode(Node):
    def __init__(self):
        super().__init__("mission_manager")
        for name, default in DEFAULTS.items():
            self.declare_parameter(name, float(default))
        self.declare_parameter("rate_hz", 10.0)
        self.logic = MissionLogic(**{n: self.get_parameter(n).value for n in DEFAULTS})
        self.altitude = None

        self.create_subscription(PointStamped, "/landing_target", self.on_target, 10)
        self.create_subscription(PoseStamped, "/drone/pose", self.on_pose, 10)
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.state_pub = self.create_publisher(String, "/mission/state", 10)
        self.create_timer(1.0 / self.get_parameter("rate_hz").value, self.tick)
        self.get_logger().info(f"Mission démarrée en état {self.logic.state}")

    def now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def on_target(self, msg: PointStamped):
        self.logic.on_detection(self.now(), msg.point.x, msg.point.y, msg.point.z)

    def on_pose(self, msg: PoseStamped):
        self.altitude = msg.pose.position.z

    def tick(self):
        if self.altitude is None:
            return  # pas encore de nouvelles de l'autopilote
        previous = self.logic.state
        vx, vy, vz = self.logic.update(self.now(), self.altitude)
        if self.logic.state != previous:
            self.get_logger().info(f"{previous} -> {self.logic.state} (altitude {self.altitude:.2f} m)")

        cmd = Twist()
        cmd.linear.x, cmd.linear.y, cmd.linear.z = float(vx), float(vy), float(vz)
        self.cmd_pub.publish(cmd)
        self.state_pub.publish(String(data=self.logic.state))


def main():
    rclpy.init()
    node = MissionManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
