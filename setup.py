from setuptools import find_packages, setup
from glob import glob, iglob
import os

package_name = "scan_data_gazebo_sim"


def _recursive_data_files(install_dir, glob_pattern):
    """Recursively collect files matching glob_pattern inside install_dir.

    The destination preserves the subdirectory structure relative to install_dir.
    Files from ``description/simple_robot/*`` land in
    ``share/<pkg>/description/simple_robot/``.
    """
    result = []
    for path in iglob(glob_pattern, recursive=True):
        if os.path.isfile(path):
            # os.path.dirname preserves the full subtree (e.g. "description/simple_robot")
            dest = os.path.join("share", package_name, os.path.dirname(path))
            result.append((dest, [path]))
    return result


setup(
    name=package_name,
    version="0.1.0",
    description="Gazebo + ROS 2 simulation for 2D LiDAR scan-matching datasets with ground-truth poses.",
    license="MIT",
    packages=find_packages(exclude=["test"]),
    data_files=(
        [(os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
         (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
         (os.path.join("share", package_name, "worlds"), glob("worlds/*.sdf")),
         (os.path.join("share", package_name), glob("resource/*"))]
        + _recursive_data_files("description", "description/**/*")
    ),
    install_requires=["setuptools", "numpy", "pyyaml"],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "recorder    = scan_data_gazebo_sim.recorder:main",
            "teleop_joy  = scan_data_gazebo_sim.teleop_joy:main",
            "ground_truth= scan_data_gazebo_sim.ground_truth:main",
            "validate    = scan_data_gazebo_sim.validation:main",
            "raycaster   = scan_data_gazebo_sim.raycaster:main",
        ],
    },
)
