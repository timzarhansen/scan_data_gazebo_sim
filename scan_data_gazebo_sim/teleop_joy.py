"""Gamepad teleoperation node for the simple robot.

Reads joy messages from /joy and publishes Twist to /cmd_vel.
Left stick:   forward/back (axis 1), strafe (axis 0) — though we use only linear.x
Right stick:  rotation (axis 2 or 3 depending on controller)
Left trigger:  slow speed modifier
Right trigger: turbo speed modifier

Default mapping is for a typical Logitech F710 / Xbox controller in DirectInput mode.
Override axis/button mappings via parameters.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
import math


class TeleopJoy(Node):

    def __init__(self):
        super().__init__("teleop_joy")

        # Declare parameters
        self.declare_parameter("axis_linear", 1)        # left stick vertical
        self.declare_parameter("axis_angular", 3)       # right stick horizontal (or 2)
        self.declare_parameter("axis_linear_sign", 1)   # -1 if inverted
        self.declare_parameter("axis_angular_sign", 1)
        self.declare_parameter("scale_linear", 0.5)
        self.declare_parameter("scale_angular", 1.0)
        self.declare_parameter("button_slow", 4)        # LB
        self.declare_parameter("button_turbo", 5)       # RB
        self.declare_parameter("slow_factor", 0.3)
        self.declare_parameter("turbo_factor", 2.0)
        self.declare_parameter("deadzone", 0.05)

        # Cache parameters
        self.axis_lin = self.get_parameter("axis_linear").value
        self.axis_ang = self.get_parameter("axis_angular").value
        self.sign_lin = self.get_parameter("axis_linear_sign").value
        self.sign_ang = self.get_parameter("axis_angular_sign").value
        self.scale_lin = self.get_parameter("scale_linear").value
        self.scale_ang = self.get_parameter("scale_angular").value
        self.btn_slow = self.get_parameter("button_slow").value
        self.btn_turbo = self.get_parameter("button_turbo").value
        self.slow_factor = self.get_parameter("slow_factor").value
        self.turbo_factor = self.get_parameter("turbo_factor").value
        self.deadzone = self.get_parameter("deadzone").value

        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.sub = self.create_subscription(Joy, "/joy", self.joy_cb, 10)

        self.get_logger().info("TeleopJoy ready. Left stick = drive, right stick = rotate.")

    def joy_cb(self, msg: Joy):
        twist = Twist()

        # Linear (forward/back)
        lin = msg.axes[self.axis_lin] if self.axis_lin < len(msg.axes) else 0.0
        lin = self._apply_deadzone(lin)

        # Angular (rotation)
        ang = msg.axes[self.axis_ang] if self.axis_ang < len(msg.axes) else 0.0
        ang = self._apply_deadzone(ang)

        # Speed modifiers
        speed_factor = 1.0
        if self.btn_slow < len(msg.buttons) and msg.buttons[self.btn_slow]:
            speed_factor = self.slow_factor
        if self.btn_turbo < len(msg.buttons) and msg.buttons[self.btn_turbo]:
            speed_factor = self.turbo_factor

        twist.linear.x = lin * self.scale_lin * speed_factor * self.sign_lin
        twist.angular.z = ang * self.scale_ang * speed_factor * self.sign_ang

        self.pub.publish(twist)

    def _apply_deadzone(self, value: float) -> float:
        if abs(value) < self.deadzone:
            return 0.0
        # Rescale so the edge of the deadzone maps to 0
        return (value - math.copysign(self.deadzone, value)) / (1.0 - self.deadzone)


def main(args=None):
    rclpy.init(args=args)
    node = TeleopJoy()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
