"""Validation and visualisation tools for recorded datasets.

Commands:
    plot-scan       Plot a single scan as a top-down point cloud.
    plot-trajectory Plot the robot trajectory from poses.csv.
    overlay-scans   Overlay two consecutive scans using ground-truth transform.

Usage:
    ros2 run scan_data_gazebo_sim validate plot-scan <npy_file>
    ros2 run scan_data_gazebo_sim validate plot-trajectory <poses_csv>
    ros2 run scan_data_gazebo_sim validate overlay-scans <dataset_dir> [id0]
"""

import numpy as np
import math
import os
import sys
import argparse

# matplotlib is imported lazily so `ros2 run` doesn't fail without it
# for non-plotting commands


def _ensure_matplotlib():
    """Import matplotlib with a non-interactive backend."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


# ──────────────────────────────────────────────────────────────


def _load_scan(npy_path: str) -> np.ndarray:
    """Load a .npy scan file and return (angles, ranges)."""
    ranges = np.load(npy_path).astype(np.float64)
    # If no angle info, assume 360° equally spaced, starting at 0
    n = len(ranges)
    angles = np.linspace(-math.pi, math.pi, n, endpoint=False)
    return angles, ranges


def _scan_to_points(angles: np.ndarray, ranges: np.ndarray):
    """Convert polar scan to (x, y) points, filtering invalid ranges."""
    valid = np.isfinite(ranges) & (ranges > 0)
    x = ranges[valid] * np.cos(angles[valid])
    y = ranges[valid] * np.sin(angles[valid])
    return x, y


# ──────────────────────────────────────────────────────────────


def cmd_plot_scan(args):
    """Plot a single .npy scan as a top-down point cloud."""
    plt = _ensure_matplotlib()

    angles, ranges = _load_scan(args.npy_file)
    x, y = _scan_to_points(angles, ranges)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Polar
    ax1.plot(angles, ranges, "b-", linewidth=0.5)
    ax1.set_title("Range vs Angle")
    ax1.set_xlabel("Angle (rad)")
    ax1.set_ylabel("Range (m)")
    ax1.grid(True)

    # Cartesian
    ax2.scatter(x, y, s=1, c="blue")
    ax2.set_title("Top-down Point Cloud")
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("y (m)")
    ax2.set_aspect("equal")
    ax2.grid(True)

    plt.tight_layout()
    out_path = args.output or "scan_plot.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")


# ──────────────────────────────────────────────────────────────


def cmd_plot_trajectory(args):
    """Plot robot path from poses.csv."""
    plt = _ensure_matplotlib()

    data = np.loadtxt(
        args.poses_csv,
        delimiter=",",
        skiprows=1,
        usecols=(2, 3),  # x, y columns
    )
    x = data[:, 0]
    y = data[:, 1]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(x, y, "b-", linewidth=1, label="trajectory")
    ax.scatter(x[0], y[0], c="green", s=80, label="start", zorder=5)
    ax.scatter(x[-1], y[-1], c="red", s=80, label="end", zorder=5)
    ax.set_title("Robot Trajectory")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    ax.grid(True)
    ax.legend()

    out_path = args.output or "trajectory.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")


# ──────────────────────────────────────────────────────────────


def cmd_overlay_scans(args):
    """Overlay two consecutive scans using ground-truth transform."""
    plt = _ensure_matplotlib()

    dataset_dir = args.dataset_dir
    id0 = args.id0 if args.id0 is not None else 0
    id1 = id0 + 1

    # Load scans
    scan0_path = os.path.join(dataset_dir, "scans", f"{id0:06d}.npy")
    scan1_path = os.path.join(dataset_dir, "scans", f"{id1:06d}.npy")

    if not os.path.exists(scan0_path) or not os.path.exists(scan1_path):
        print(f"Error: scans {id0} or {id1} not found in {dataset_dir}")
        sys.exit(1)

    angles0, ranges0 = _load_scan(scan0_path)
    angles1, ranges1 = _load_scan(scan1_path)
    x0, y0 = _scan_to_points(angles0, ranges0)
    x1_raw, y1_raw = _scan_to_points(angles1, ranges1)

    # Load ground-truth transform from transforms.csv
    transforms_path = os.path.join(dataset_dir, "transforms.csv")
    gt_dx, gt_dy, gt_dtheta = 0.0, 0.0, 0.0
    if os.path.exists(transforms_path):
        rows = np.loadtxt(
            transforms_path, delimiter=",", skiprows=1,
        )
        if rows.ndim == 1:
            rows = rows.reshape(1, -1)
        # Find the row for (id0, id1)
        for row in rows:
            if int(row[0]) == id0 and int(row[1]) == id1:
                gt_dx, gt_dy, gt_dtheta = row[2], row[3], row[4]
                break

    # Ground-truth yaw of scan id1 (needed for the exact frame transform)
    gt_yaw1 = 0.0
    poses_path = os.path.join(dataset_dir, "poses.csv")
    if os.path.exists(poses_path):
        pose_rows = np.loadtxt(poses_path, delimiter=",", skiprows=1)
        if pose_rows.ndim == 1:
            pose_rows = pose_rows.reshape(1, -1)
        for row in pose_rows:
            if int(row[0]) == id1:
                gt_yaw1 = row[4]
                break

    # Exact frame transform: express scan0 in the frame of scan1
    #   p' = R(-dtheta) p - R(yaw1)^T (dx, dy)
    cos_t = math.cos(gt_dtheta)
    sin_t = math.sin(gt_dtheta)
    cos_y1, sin_y1 = math.cos(gt_yaw1), math.sin(gt_yaw1)
    x0_trans = cos_t * x0 + sin_t * y0 - (cos_y1 * gt_dx + sin_y1 * gt_dy)
    y0_trans = -sin_t * x0 + cos_t * y0 + (sin_y1 * gt_dx - cos_y1 * gt_dy)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(x0_trans, y0_trans, s=1, c="blue", label=f"scan {id0} (transformed)")
    ax.scatter(x1_raw, y1_raw, s=1, c="red", label=f"scan {id1} (raw)")
    ax.set_title(
        f"Overlay: scan {id0} → GT transform → scan {id1}\n"
        f"dx={gt_dx:.4f}  dy={gt_dy:.4f}  dtheta={gt_dtheta:.4f} rad"
    )
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_aspect("equal")
    ax.grid(True)
    ax.legend()

    out_path = args.output or f"overlay_{id0}_{id1}.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")


# ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Validation tools for scan_data_gazebo_sim datasets."
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output image path (default: auto-named in current dir)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # plot-scan
    p_scan = subparsers.add_parser(
        "plot-scan", help="Plot a single .npy scan as point cloud."
    )
    p_scan.add_argument("npy_file", help="Path to scan .npy file")

    # plot-trajectory
    p_traj = subparsers.add_parser(
        "plot-trajectory", help="Plot robot trajectory from poses.csv."
    )
    p_traj.add_argument("poses_csv", help="Path to poses.csv")

    # overlay-scans
    p_over = subparsers.add_parser(
        "overlay-scans",
        help="Overlay two consecutive scans using ground-truth transform.",
    )
    p_over.add_argument("dataset_dir", help="Dataset directory (containing scans/ and transforms.csv)")
    p_over.add_argument("id0", type=int, nargs="?", default=None, help="First scan ID (default: 0)")

    parsed = parser.parse_args()

    # Route to handler
    if parsed.command == "plot-scan":
        cmd_plot_scan(parsed)
    elif parsed.command == "plot-trajectory":
        cmd_plot_trajectory(parsed)
    elif parsed.command == "overlay-scans":
        cmd_overlay_scans(parsed)


if __name__ == "__main__":
    main()
