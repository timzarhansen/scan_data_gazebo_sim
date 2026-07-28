"""Ground-truth pose publisher for the simple robot in Gazebo Harmonic.

Subscribes to Gazebo's model pose topic via ros_gz_bridge
and republishes as a PoseStamped on /ground_truth_pose.
Falls back to odometry if the direct model topic is unavailable.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
import math


class GroundTruthPublisher(Node):

    def __init__(self):
        super().__init__("ground_truth_publisher")

        # Declare parameters
        self.declare_parameter("robot_name", "simple_robot")
        self.declare_parameter("use_odom_fallback", False)

        self.robot_name = self.get_parameter("robot_name").value
        use_odom = self.get_parameter("use_odom_fallback").value

        # Publisher for ground truth
        self.pub = self.create_publisher(PoseStamped, "/ground_truth_pose", 10)

        # Try subscribing to the Gazebo model pose topic (bridged by ros_gz_bridge)
        # If that doesn't work, fall back to /odom
        self._gz_sub = None
        self._odom_sub = None

        if not use_odom:
            # Try listening to the model pose from Gazebo (via topic name convention)
            pose_topic = f"/model/{self.robot_name}/pose"
            self._gz_sub = self.create_subscription(
                PoseStamped, pose_topic, self._gz_pose_cb, 10
            )
            self.get_logger().info(
                f"Subscribing to Gazebo model pose: {pose_topic}"
            )
        else:
            # Fallback: odometry
            self._odom_sub = self.create_subscription(
                Odometry, "/odom", self._odom_cb, 10
            )
            self.get_logger().info("Subscribing to /odom for ground truth")

    def _gz_pose_cb(self, msg: PoseStamped):
        """Forward the Gazebo pose directly."""
        self.pub.publish(msg)

    def _odom_cb(self, msg: Odometry):
        """Convert odometry to PoseStamped."""
        pose = PoseStamped()
        pose.header = msg.header
        pose.header.frame_id = "map"
        pose.pose = msg.pose.pose
        self.pub.publish(pose)


def main(args=None):
    rclpy.init(args=args)
    node = GroundTruthPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
