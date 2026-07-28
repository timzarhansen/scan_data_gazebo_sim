"""Standalone RViz visualization for a running simulation.

Start this in a separate terminal to visualize an already-running sim — no
need to restart Gazebo. Broadcasts odom -> chassis TF from /odom, a static
chassis -> laser transform, and opens RViz with /scan loaded.

Usage:
    ros2 launch scan_data_gazebo_sim viz.launch.py
"""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node


def generate_launch_description():
    pkg = "scan_data_gazebo_sim"

    # odom -> chassis TF from /odom (robot pose in the world frame)
    tf_broadcaster = Node(
        package="scan_data_gazebo_sim",
        executable="tf_broadcaster",
        name="odom_tf_broadcaster",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # chassis -> laser static TF (matches laser link pose in model.sdf)
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_tf_chassis_laser",
        arguments=["0", "0", "0.12", "0", "0", "0", "chassis", "laser"],
    )

    # RViz with the scan-viz config
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", PathJoinSubstitution(
            [FindPackageShare(pkg), "config", "scan_viz.rviz"])],
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription([tf_broadcaster, static_tf, rviz])
