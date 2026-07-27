"""Launch the gamepad teleoperation node.

Usage:
    ros2 launch scan_data_gazebo_sim teleop.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="scan_data_gazebo_sim",
            executable="teleop_joy",
            name="teleop_joy",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
    ])
