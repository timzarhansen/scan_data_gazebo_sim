from setuptools import find_packages, setup
from glob import glob
import os

package_name = "scan_data_gazebo_sim"

setup(
    name=package_name,
    version="0.1.0",
    description="Gazebo + ROS 2 simulation for 2D LiDAR scan-matching datasets with ground-truth poses.",
    license="MIT",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        (os.path.join("share", package_name, "description"), glob("description/*.sdf")),
        (os.path.join("share", package_name, "worlds"), glob("worlds/*.sdf")),
        (os.path.join("share", package_name), glob("resource/*")),
    ],
    install_requires=["setuptools", "numpy", "pyyaml"],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "recorder    = scan_data_gazebo_sim.recorder:main",
            "teleop_joy  = scan_data_gazebo_sim.teleop_joy:main",
            "ground_truth= scan_data_gazebo_sim.ground_truth:main",
            "validate    = scan_data_gazebo_sim.validation:main",
        ],
    },
)
