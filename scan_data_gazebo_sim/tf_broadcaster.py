"""TF broadcaster: publishes the odom -> chassis transform from /odom.

Lets RViz render /scan (frame 'laser') in a world-fixed frame so the robot
driving through the maze is visible. The chassis -> laser static transform is
published separately by a static_transform_publisher in the launch file
(0, 0, 0.12 — matches the laser link pose in model.sdf).
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros


class OdomTfBroadcaster(Node):
    def __init__(self):
        super().__init__("odom_tf_broadcaster")

        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("parent_frame", "odom")
        self.declare_parameter("child_frame", "chassis")

        odom_topic = self.get_parameter("odom_topic").value
        self._parent = self.get_parameter("parent_frame").value
        self._child = self.get_parameter("child_frame").value

        self._msg_count = 0

        self._br = tf2_ros.TransformBroadcaster(self)
        # ros_gz_bridge publishes /odom with BEST_EFFORT QoS (gz-transport
        # default). A reliable subscription would silently receive nothing
        # (QoS incompatibility) -> no TF at all. Best-effort subscribes to
        # both best-effort and reliable publishers, so it always works.
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Odometry, odom_topic, self._odom_cb, qos)
        self.get_logger().info(
            f"Broadcasting TF '{self._parent}' -> '{self._child}' from "
            f"'{odom_topic}' (best-effort QoS)"
        )

    def _odom_cb(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = self._parent
        t.child_frame_id = self._child
        t.transform.translation = msg.pose.pose.position
        t.transform.rotation = msg.pose.pose.orientation
        self._br.sendTransform(t)

        # Heartbeat: lets us see from the launch output that odom messages
        # are actually being received and TFs published.
        self._msg_count += 1
        if self._msg_count % 100 == 0:
            self.get_logger().info(
                f"published {self._msg_count} odom->chassis TFs"
            )


def main(args=None):
    rclpy.init(args=args)
    node = OdomTfBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
