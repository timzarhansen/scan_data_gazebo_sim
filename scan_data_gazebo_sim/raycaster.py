"""CPU raycaster: publishes /scan from /odom + maze wall geometry.

Reads the maze world SDF to extract wall positions, subscribes to the
robot's odometry, and performs CPU ray-wall intersection tests at the
configured rate. Outputs sensor_msgs/LaserScan.

No GPU or Gazebo Sensors plugin required.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseStamped
import numpy as np
import math
import os
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory


class WallAABB:
    """An axis-aligned bounding box in 2D representing a wall segment."""

    __slots__ = ("xmin", "xmax", "ymin", "ymax")

    def __init__(self, xmin, xmax, ymin, ymax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax


def _parse_walls_from_sdf(sdf_path):
    """Parse a Gazebo SDF world file and return a list of WallAABB objects.

    Extracts all <model> elements that contain a <box> geometry for collision.
    The AABB is computed in world coordinates accounting for model <pose>.
    """
    tree = ET.parse(sdf_path)
    root = tree.getroot()
    ns = {"sdf": "http://sdformat.org/schemas/sdf"}  # may or may not be used

    walls = []

    for model in root.iter("model"):
        # Only static models with a box collision are considered walls
        static_el = model.find("static")
        if static_el is None or static_el.text != "true":
            continue

        # Model pose
        pose_str = model.findtext("pose", "0 0 0 0 0 0")
        pose_parts = list(map(float, pose_str.split()))
        px, py, pz, proll, ppitch, pyaw = pose_parts

        for link in model.iter("link"):
            for collision in link.iter("collision"):
                box = collision.find(".//box")
                if box is None:
                    continue
                size_str = box.findtext("size", "1 1 1")
                sx, sy, sz = map(float, size_str.split())

                # Compute world-space AABB of this box
                # Half-extents in local frame
                hx, hy = sx / 2.0, sy / 2.0

                # Local corners of the rectangle (top-down, 2D)
                corners_local = np.array([
                    [-hx, -hy],
                    [ hx, -hy],
                    [ hx,  hy],
                    [-hx,  hy],
                ])

                # Rotate by yaw
                cos_y = math.cos(pyaw)
                sin_y = math.sin(pyaw)
                rot = np.array([[cos_y, -sin_y], [sin_y, cos_y]])
                corners_world = corners_local @ rot.T + np.array([px, py])

                # Axis-aligned bounding box in world coords
                xmin = float(np.min(corners_world[:, 0]))
                xmax = float(np.max(corners_world[:, 0]))
                ymin = float(np.min(corners_world[:, 1]))
                ymax = float(np.max(corners_world[:, 1]))

                walls.append(WallAABB(xmin, xmax, ymin, ymax))

    return walls


def _ray_aabb_intersection(ox, oy, dx, dy, wall):
    """Ray-AABB intersection (2D slab method).

    Returns the distance t along the ray to the nearest positive intersection,
    or None if no intersection.
    """
    tmin = -1e100
    tmax = 1e100

    # X slab
    if abs(dx) < 1e-12:
        if ox < wall.xmin or ox > wall.xmax:
            return None
    else:
        t1 = (wall.xmin - ox) / dx
        t2 = (wall.xmax - ox) / dx
        if t1 > t2:
            t1, t2 = t2, t1
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)

    # Y slab
    if abs(dy) < 1e-12:
        if oy < wall.ymin or oy > wall.ymax:
            return None
    else:
        t1 = (wall.ymin - oy) / dy
        t2 = (wall.ymax - oy) / dy
        if t1 > t2:
            t1, t2 = t2, t1
        tmin = max(tmin, t1)
        tmax = min(tmax, t2)

    if tmax < 0 or tmin > tmax:
        return None

    # Only return positive distance
    if tmin < 0:
        tmin = tmax

    return tmin if tmin > 0 else None


class Raycaster(Node):

    def __init__(self):
        super().__init__("raycaster")

        # --- Parameters ---
        self.declare_parameter("world", "maze_small")
        self.declare_parameter("num_beams", 720)
        self.declare_parameter("update_rate", 10.0)
        self.declare_parameter("range_min", 0.1)
        self.declare_parameter("range_max", 30.0)
        self.declare_parameter("noise_std", 0.0)  # Gaussian noise (metres)
        self.declare_parameter("angle_offset", 0.0)

        world_name = self.get_parameter("world").value
        num_beams = self.get_parameter("num_beams").value
        rate = self.get_parameter("update_rate").value
        self._range_min = self.get_parameter("range_min").value
        self._range_max = self.get_parameter("range_max").value
        noise_std = self.get_parameter("noise_std").value
        angle_offset = self.get_parameter("angle_offset").value

        # --- Load walls from world SDF ---
        pkg_dir = get_package_share_directory("scan_data_gazebo_sim")
        sdf_path = os.path.join(pkg_dir, "worlds", f"{world_name}.sdf")

        if not os.path.exists(sdf_path):
            self.get_logger().error(f"World file not found: {sdf_path}")
            self._walls = []
        else:
            self._walls = _parse_walls_from_sdf(sdf_path)
            self.get_logger().info(
                f"Loaded {len(self._walls)} walls from {world_name}"
            )

        # --- Scan config ---
        self._angle_min = -math.pi + angle_offset
        self._angle_max = math.pi + angle_offset
        self._angle_inc = 2.0 * math.pi / num_beams
        self._num_beams = num_beams

        # Precompute ray direction cos/sin for each beam
        self._angles = np.linspace(
            self._angle_min, self._angle_max, num_beams, endpoint=False
        )
        self._cos_a = np.cos(self._angles)
        self._sin_a = np.sin(self._angles)
        self._noise_std = noise_std

        # --- Robot pose ---
        self._rx = 0.0
        self._ry = 0.0
        self._ryaw = 0.0
        self._pose_received = False

        # --- Subscriptions ---
        self._odom_sub = self.create_subscription(
            Odometry, "/odom", self._odom_cb, 10
        )

        # --- Publisher ---
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)

        # --- Timer ---
        period = 1.0 / rate
        self._timer = self.create_timer(period, self._publish_scan)

        self.get_logger().info(
            f"Raycaster: {num_beams} beams @ {rate} Hz, "
            f"range [{self._range_min}, {self._range_max}]"
        )

    # ----------------------------------------------------------------
    def _odom_cb(self, msg: Odometry):
        self._rx = msg.pose.pose.position.x
        self._ry = msg.pose.pose.position.y
        # Extract yaw from quaternion
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self._ryaw = math.atan2(siny_cosp, cosy_cosp)
        self._pose_received = True

    # ----------------------------------------------------------------
    def _publish_scan(self):
        if not self._pose_received:
            return

        ranges = np.full(self._num_beams, float("inf"), dtype=np.float32)
        now = self.get_clock().now()
        stamp = now.to_msg()

        # For each beam, cast ray against all walls
        for i in range(self._num_beams):
            dx = self._cos_a[i]
            dy = self._sin_a[i]
            best_t = float("inf")

            for wall in self._walls:
                t = _ray_aabb_intersection(
                    self._rx, self._ry, dx, dy, wall
                )
                if t is not None and t < best_t:
                    best_t = t

            if math.isfinite(best_t):
                r = best_t
                if r < self._range_min:
                    r = 0.0  # too close — treat as zero
                elif r > self._range_max:
                    r = float("inf")
                else:
                    # Add noise
                    if self._noise_std > 0:
                        r += np.random.normal(0.0, self._noise_std)
                        r = max(self._range_min, min(r, self._range_max))
                ranges[i] = r

        # Build LaserScan message
        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = "laser"
        scan.angle_min = self._angle_min
        scan.angle_max = self._angle_max
        scan.angle_increment = self._angle_inc
        scan.time_increment = 0.0  # all beams at once (instant scan)
        scan.scan_time = 0.0
        scan.range_min = float(self._range_min)
        scan.range_max = float(self._range_max)
        scan.ranges = ranges.tolist()
        scan.intensities = []

        self._scan_pub.publish(scan)

    # ----------------------------------------------------------------


def main(args=None):
    rclpy.init(args=args)
    node = Raycaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
