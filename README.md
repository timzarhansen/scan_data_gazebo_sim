# scan_data_gazebo_sim

**Gazebo Harmonic + ROS 2 Jazzy** simulation for generating 2D LiDAR scan-matching datasets with ground-truth poses.

Drive a simple differential-drive robot through maze worlds using a gamepad. A standalone recorder subscribes to `/scan` and `/ground_truth_pose`, saves synchronised pairs to disk as NumPy arrays + CSV with relative transforms between consecutive scans.

## Quick Start (3-terminal workflow)

```bash
# Terminal 1 — Simulation + robot
ros2 launch scan_data_gazebo_sim sim.launch.py

# Terminal 2 — Gamepad teleop
ros2 launch scan_data_gazebo_sim teleop.launch.py

# Terminal 3 — Recorder (start any time, Ctrl+C to finish)
ros2 launch scan_data_gazebo_sim record.launch.py
```

Drive the robot through the maze. When you're done, Ctrl+C the recorder. The dataset is saved in `datasets/YYYYMMDD_HHMMSS/`.

## Dependencies

- **ROS 2 Jazzy**
- **Gazebo Harmonic** (`gz-harmonic`)
- **ros_gz_bridge** (`ros-jazzy-ros-gz-bridge`, `ros-jazzy-ros-gz-interfaces`)
- Python packages: `numpy`, `PyYAML`, `matplotlib` (for validation scripts)

```bash
sudo apt-get install gz-harmonic
sudo apt-get install ros-jazzy-ros-gz-bridge ros-jazzy-ros-gz-interfaces
pip install numpy PyYAML matplotlib
```

## Package Structure

```
scan_data_gazebo_sim/
├── config/params.yaml           # All configurable parameters
├── description/
│   └── simple_robot.sdf         # Differential-drive robot + 360° LiDAR
├── launch/
│   ├── sim.launch.py            # Gazebo + bridge
│   ├── teleop.launch.py         # Gamepad teleop
│   ├── record.launch.py         # Dataset recorder
│   └── ground_truth.launch.py   # Ground-truth pose publisher
├── scan_data_gazebo_sim/
│   ├── recorder.py              # Standalone dataset recorder node
│   ├── teleop_joy.py            # Gamepad teleoperation node
│   ├── ground_truth.py          # Ground-truth pose publisher
│   └── validation.py            # Plotting & validation tools
├── worlds/
│   ├── maze_small.sdf           # Simple 2-wall maze
│   ├── maze_01.sdf              # Corridor with two turns
│   ├── maze_02.sdf              # Spiral-like labyrinth
│   └── maze_03.sdf              # Large maze with rooms
├── package.xml
└── setup.py
```

## Robot

A minimal differential-drive robot with:
- Circular chassis (20 cm radius)
- Two driven wheels
- One passive caster
- 360° LiDAR mounted at the center (720 beams, 10 Hz, 30 m range)
- **No cameras, IMU, or other sensors**

The SDF model is in `description/simple_robot.sdf`.

## Mazes

| World | Description |
|-------|-------------|
| `maze_small` | Simple rectangular border with two inner walls |
| `maze_01` | Corridor with two turns |
| `maze_02` | Spiral-like labyrinth with concentric rings |
| `maze_03` | Large irregular maze with rooms |

Switch worlds:
```bash
ros2 launch scan_data_gazebo_sim sim.launch.py world:=maze_02
```

## Dataset Format

Each recording session produces a timestamped directory:

```
datasets/YYYYMMDD_HHMMSS/
├── metadata.yaml        # Recording configuration & statistics
├── poses.csv            # (id, time_sec, x, y, yaw) for each scan
├── transforms.csv       # (id0, id1, dx, dy, dtheta) between consecutive scans
└── scans/
    ├── 000000.npy       # 720-element float32 range array
    ├── 000001.npy
    └── ...
```

### poses.csv

```
id,time_sec,x,y,yaw
0,12.345,1.25,3.14,0.82
1,12.445,1.28,3.17,0.85
...
```

### transforms.csv (computed on recorder shutdown)

```
id0,id1,dx,dy,dtheta
0,1,0.03,0.03,0.03
1,2,0.02,0.04,0.01
...
```

## Gamepad Controls

Default mapping (Logitech F710 / Xbox controller in DirectInput mode):

| Control | Action |
|---------|--------|
| Left stick (up/down) | Forward / backward |
| Right stick (left/right) | Rotate |
| LB (button 4) | Slow speed (30%) |
| RB (button 5) | Turbo (2×) |

Override axes/buttons in `config/params.yaml` or pass as ROS parameters:
```bash
ros2 run scan_data_gazebo_sim teleop_joy --ros-args -p axis_angular:=2
```

## Validation

Plot a single scan:
```bash
ros2 run scan_data_gazebo_sim validate plot-scan datasets/.../scans/000000.npy
```

Plot robot trajectory:
```bash
ros2 run scan_data_gazebo_sim validate plot-trajectory datasets/.../poses.csv
```

Overlay two consecutive scans using ground-truth transform (sanity check):
```bash
ros2 run scan_data_gazebo_sim validate overlay-scans datasets/YYYYMMDD_HHMMSS/ 0
```

All validation commands save a PNG to the current directory.

## Recording Workflow

1. **Launch simulation** — starts Gazebo with the robot in a maze
2. **Launch teleop** — connect your gamepad
3. **Start recorder** in a separate terminal — it immediately begins waiting for data
4. **Drive** — the recorder captures every synchronized scan+pose pair
5. **Stop recorder** (Ctrl+C) — saves metadata, computes relative transforms, exits

The recorder only captures data while it's running — start it when you're ready, stop it when done.

## Adding a New Maze

1. Create `worlds/my_maze.sdf` (use one of the existing files as a template)
2. Launch with:
```bash
ros2 launch scan_data_gazebo_sim sim.launch.py world:=my_maze
```

## License

MIT
