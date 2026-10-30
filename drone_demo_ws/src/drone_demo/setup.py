from glob import glob

from setuptools import setup

package_name = "drone_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Equipe UAV Challenge",
    maintainer_email="equipe@example.com",
    description="Démo ROS 2 : atterrissage de précision sur station ArUco",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "sim_drone = drone_demo.sim_drone_node:main",
            "aruco_detector = drone_demo.aruco_detector_node:main",
            "mission_manager = drone_demo.mission_manager_node:main",
            "make_marker = drone_demo.make_marker:main",
        ],
    },
)
