"""Launch the ground-truth pose publisher.

Usage:
    ros2 launch scan_data_gazebo_sim ground_truth.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="scan_data_gazebo_sim",
            executable="ground_truth",
            name="ground_truth_publisher",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
    ])
