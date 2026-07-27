"""Launch the dataset recorder node (standalone — run in separate terminal).

Usage:
    ros2 launch scan_data_gazebo_sim record.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="scan_data_gazebo_sim",
            executable="recorder",
            name="dataset_recorder",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
    ])
