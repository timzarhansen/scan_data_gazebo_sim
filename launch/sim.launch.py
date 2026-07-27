"""Launch Gazebo Harmonic with a maze world and spawn the simple robot.

Usage:
    ros2 launch scan_data_gazebo_sim sim.launch.py world:=maze_small
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import (
    LaunchConfiguration, PathJoinSubstitution, PythonExpression
)
from launch.conditions import IfCondition
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = "scan_data_gazebo_sim"

    world_arg = DeclareLaunchArgument(
        "world",
        default_value="maze_small",
        description="Name of the maze world (without .sdf extension)",
    )

    bridge_arg = DeclareLaunchArgument(
        "use_ros_gz_bridge",
        default_value="true",
        description="Whether to start the ROS-Gazebo bridge",
    )

    # Point Gazebo to the model directory so model://simple_robot resolves
    gz_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=PathJoinSubstitution([FindPackageShare(pkg), "description"]),
    )



    # Append .sdf extension via PythonExpression substitution
    world_file = PythonExpression(["'", LaunchConfiguration("world"), "' + '.sdf'"])

    # Gazebo server
    gz_server = ExecuteProcess(
        cmd=[
            "gz", "sim", "-r", "-v", "3",
            PathJoinSubstitution([FindPackageShare(pkg), "worlds", world_file]),
        ],
        output="screen",
    )

    # Bridge: ROS 2 topics <-> Gazebo topics
    bridge = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist",
            "/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry",
            "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
        ],
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_ros_gz_bridge")),
    )

    return LaunchDescription([
        world_arg,
        bridge_arg,
        gz_resource_path,

        gz_server,
        bridge,
    ])
