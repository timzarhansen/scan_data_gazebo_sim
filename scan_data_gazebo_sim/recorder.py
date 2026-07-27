"""Standalone dataset recorder for 2D LiDAR scan-matching data.

Usage (separate terminal, started at any time):
    ros2 run scan_data_gazebo_sim recorder

Behaviour:
- Subscribes to /scan and /ground_truth_pose
- Synchronises messages by closest timestamp (max 10 ms tolerance)
- Saves synchronised pairs to a timestamped dataset directory
- On Ctrl+C: finalises metadata, computes relative transforms, exits

Output structure:
    datasets/YYYYMMDD_HHMMSS/
    ├── metadata.yaml
    ├── poses.csv         (id, time_sec, x, y, yaw)
    ├── transforms.csv    (id0, id1, dx, dy, dtheta)
    └── scans/
        ├── 000000.npy
        ├── 000001.npy
        └── ...
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseStamped
import numpy as np
import os
import math
import signal
import sys
from datetime import datetime
import yaml


def euler_from_quaternion(q):
    """Convert a quaternion to (roll, pitch, yaw)."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return yaw


def normalize_angle(theta):
    """Normalise angle to [-pi, pi]."""
    while theta > math.pi:
        theta -= 2.0 * math.pi
    while theta < -math.pi:
        theta += 2.0 * math.pi
    return theta


class DatasetRecorder(Node):

    def __init__(self):
        super().__init__("dataset_recorder")

        # --- Parameters ---
        self.declare_parameter("output_base", "datasets")
        self.declare_parameter("world_name", "maze_small")
        self.declare_parameter("robot_name", "simple_robot")
        self.declare_parameter("sync_tolerance_sec", 0.01)  # 10 ms

        self.output_base = self.get_parameter("output_base").value
        self.world_name = self.get_parameter("world_name").value
        self.robot_name = self.get_parameter("robot_name").value
        self.sync_tolerance = self.get_parameter("sync_tolerance_sec").value

        # --- State ---
        self._latest_scan = None       # (timestamp, msg)
        self._latest_pose = None       # (timestamp, msg)
        self._sample_id = 0
        self._poses = []               # list of dicts for CSV
        self._metadata = None          # set on first scan
        self._start_time = self.get_clock().now().nanoseconds / 1e9
        self._running = True

        # --- Subscriptions ---
        self._scan_sub = self.create_subscription(
            LaserScan, "/scan", self._scan_cb, 10
        )
        self._pose_sub = self.create_subscription(
            PoseStamped, "/ground_truth_pose", self._pose_cb, 10
        )

        # --- Create output directory ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._out_dir = os.path.join(
            self.output_base, timestamp
        )
        self._scans_dir = os.path.join(self._out_dir, "scans")
        os.makedirs(self._scans_dir, exist_ok=True)

        # --- Open poses CSV ---
        self._poses_path = os.path.join(self._out_dir, "poses.csv")
        self._poses_file = open(self._poses_path, "w")
        self._poses_file.write("id,time_sec,x,y,yaw\n")
        self._poses_file.flush()

        self.get_logger().info(
            f"Recorder started → {self._out_dir}\n"
            f"  Waiting for /scan and /ground_truth_pose..."
        )

        # --- Graceful shutdown ---
        signal.signal(signal.SIGINT, self._signal_handler)

    # ----------------------------------------------------------------
    def _scan_cb(self, msg: LaserScan):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self._latest_scan = (t, msg)
        self._try_sync()

    def _pose_cb(self, msg: PoseStamped):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self._latest_pose = (t, msg)
        self._try_sync()

    def _try_sync(self):
        """If we have both a scan and a pose within tolerance, save."""
        if self._latest_scan is None or self._latest_pose is None:
            return

        t_scan, scan = self._latest_scan
        t_pose, pose = self._latest_pose
        dt = abs(t_scan - t_pose)

        if dt > self.sync_tolerance:
            return  # wait for closer pair

        # --- Save scan ---
        ranges = np.array(scan.ranges, dtype=np.float32)
        scan_path = os.path.join(
            self._scans_dir, f"{self._sample_id:06d}.npy"
        )
        np.save(scan_path, ranges)

        # --- Save pose ---
        yaw = euler_from_quaternion(pose.pose.orientation)
        row = {
            "id": self._sample_id,
            "time_sec": t_scan,
            "x": pose.pose.position.x,
            "y": pose.pose.position.y,
            "yaw": yaw,
        }
        self._poses.append(row)
        self._poses_file.write(
            f"{row['id']},{row['time_sec']:.9f},{row['x']:.6f},"
            f"{row['y']:.6f},{row['yaw']:.6f}\n"
        )
        self._poses_file.flush()

        # --- Store metadata from first scan ---
        if self._metadata is None:
            self._metadata = {
                "world_name": self.world_name,
                "robot_name": self.robot_name,
                "creation_date": datetime.now().isoformat(),
                "num_beams": len(ranges),
                "angle_min_rad": scan.angle_min,
                "angle_max_rad": scan.angle_max,
                "angle_increment_rad": scan.angle_increment,
                "range_max_m": scan.range_max,
                "range_min_m": scan.range_min,
                "scan_update_rate_hz": 1.0 / scan.scan_time if scan.scan_time > 0 else 0,
                "sync_tolerance_sec": self.sync_tolerance,
            }

        self.get_logger().info(
            f"  [{self._sample_id:06d}] t={t_scan:.3f}  "
            f"pos=({row['x']:.3f}, {row['y']:.3f}, {row['yaw']:.3f})"
        )

        self._sample_id += 1
        # Clear buffers to avoid re-processing the same pair
        self._latest_scan = None
        self._latest_pose = None

    # ----------------------------------------------------------------
    def _signal_handler(self, signum, frame):
        self.get_logger().info("\nShutting down — finalising dataset...")
        self._running = False

    def shutdown(self):
        """Called from main loop exit — finalise dataset."""
        self._poses_file.close()

        if self._metadata is None:
            self.get_logger().warn("No data recorded — nothing to save.")
            return

        n = len(self._poses)

        # --- Compute transforms ---
        transforms_path = os.path.join(self._out_dir, "transforms.csv")
        with open(transforms_path, "w") as f:
            f.write("id0,id1,dx,dy,dtheta\n")
            for i in range(1, n):
                p0 = self._poses[i - 1]
                p1 = self._poses[i]
                dx = p1["x"] - p0["x"]
                dy = p1["y"] - p0["y"]
                dtheta = normalize_angle(p1["yaw"] - p0["yaw"])
                f.write(f"{p0['id']},{p1['id']},{dx:.9f},{dy:.9f},{dtheta:.9f}\n")

        # --- Write metadata ---
        end_time = self.get_clock().now().nanoseconds / 1e9
        self._metadata["num_scans"] = n
        self._metadata["num_transforms"] = n - 1
        self._metadata["duration_sec"] = round(end_time - self._start_time, 3)

        meta_path = os.path.join(self._out_dir, "metadata.yaml")
        with open(meta_path, "w") as f:
            yaml.dump(self._metadata, f, default_flow_style=False)

        self.get_logger().info(
            f"Dataset saved: {self._out_dir}\n"
            f"  Scans:       {n}\n"
            f"  Transforms:  {n - 1}\n"
            f"  Duration:    {self._metadata['duration_sec']} s\n"
            f"  Metadata:    {meta_path}\n"
            f"  Poses:       {self._poses_path}\n"
            f"  Transforms:  {transforms_path}"
        )

    def is_running(self):
        return self._running


def main(args=None):
    rclpy.init(args=args)
    node = DatasetRecorder()

    try:
        while node.is_running() and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
