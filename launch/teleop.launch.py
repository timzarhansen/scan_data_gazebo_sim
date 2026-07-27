"""Launch the gamepad teleoperation node.

Starts the joy driver (reads /dev/input/js0) and the teleop node
that translates joy messages to Twist commands.

Usage:
    ros2 launch scan_data_gazebo_sim teleop.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # Joystick driver: reads gamepad, publishes /joy
        Node(
            package="joy",
            executable="joy_node",
            name="joy_node",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "dev": "/dev/input/js0",
                "deadzone": 0.05,
            }],
        ),
        # Translates /joy → /cmd_vel
        Node(
            package="scan_data_gazebo_sim",
            executable="teleop_joy",
            name="teleop_joy",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "scale_angular": 0.5,  # full stick = 0.5 rad/s (~29°/s)
            }],
        ),
    ])
