"""Lance toute la chaîne : drone simulé + vision + mission.

ros2 launch drone_demo demo.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params = os.path.join(get_package_share_directory("drone_demo"), "config", "params.yaml")
    return LaunchDescription([
        Node(package="drone_demo", executable="sim_drone", parameters=[params], output="screen"),
        Node(package="drone_demo", executable="aruco_detector", parameters=[params], output="screen"),
        Node(package="drone_demo", executable="mission_manager", parameters=[params], output="screen"),
    ])
