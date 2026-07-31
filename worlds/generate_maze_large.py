#!/usr/bin/env python3
"""
Generate maze_large.sdf — 50×40m industrial complex for LiDAR benchmarking.

5 zones + curved connectors + dead-end alcove.
Deterministic (seeded RNG). All model names unique.
All geometry is scaled by SCALE (default 0.5, pass a value to override).

Usage:
    python3 generate_maze_large.py > maze_large.sdf
    python3 generate_maze_large.py 0.6 > maze_large.sdf
"""

import random
import math
import sys

SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5   # uniform layout scale

W = 0.2            # wall thickness
H = 1.0            # wall height
COL = "0.3 0.3 0.3 1"   # wall colour
PCOL = "0.4 0.4 0.4 1"  # pillar colour

# ── helpers ──────────────────────────────────────────────────────────────

def _box(name, cx, cy, sx, sy, yaw_deg=0, mat=COL):
    """One static wall model as an SDF <model> block (scaled by SCALE)."""
    cx *= SCALE; cy *= SCALE; sx *= SCALE; sy *= SCALE
    yaw = yaw_deg * math.pi / 180.0
    return f"""    <model name="{name}">
      <static>true</static>
      <pose>{cx} {cy} {H/2} 0 0 {yaw}</pose>
      <link name="wall">
        <collision name="collision">
          <geometry><box><size>{sx} {sy} {H}</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>{sx} {sy} {H}</size></box></geometry>
          <material><ambient>{mat}</ambient><diffuse>{mat}</diffuse></material>
        </visual>
      </link>
    </model>"""

def horiz(name, cx, cy, L):
    return _box(name, cx, cy, L, W)

def vert(name, cx, cy, L):
    return _box(name, cx, cy, W, L)

def pillar(name, cx, cy, d=0.5):
    """One static pillar model as an SDF <model> block (scaled by SCALE)."""
    cx *= SCALE; cy *= SCALE; d *= SCALE
    return f"""    <model name="{name}">
      <static>true</static>
      <pose>{cx} {cy} {H/2} 0 0 0</pose>
      <link name="p">
        <collision name="c">
          <geometry><cylinder><radius>{d/2}</radius><length>{H}</length></cylinder></geometry>
        </collision>
        <visual name="v">
          <geometry><cylinder><radius>{d/2}</radius><length>{H}</length></cylinder></geometry>
          <material><ambient>{PCOL}</ambient><diffuse>{PCOL}</diffuse></material>
        </visual>
      </link>
    </model>"""


# ── all walls / pillars ──────────────────────────────────────────────────

walls = []
rand = random.Random(42)   # deterministic

def scatter_pillars(prefix, xmin, xmax, ymin, ymax, count,
                    exclude=(), dmin=0.35, dmax=0.6):
    """Place `count` pillars in a rect, skipping exclusion rects (x,y,w,h)."""
    for i in range(count):
        for _try in range(200):
            x = rand.uniform(xmin + 0.5, xmax - 0.5)
            y = rand.uniform(ymin + 0.5, ymax - 0.5)
            if any(ex[0] <= x <= ex[0] + ex[2] and ex[1] <= y <= ex[1] + ex[3]
                   for ex in exclude):
                continue
            break
        d = rand.uniform(dmin, dmax)
        walls.append(pillar(f"{prefix}_{i}", round(x, 1), round(y, 1),
                            round(d, 2)))


# ════════════════════════════════════════════════════════════════════════
#  OUTER BORDER  —  100 × 80 m, with a 10 m gap at the north centre
#  for the dead-end alcove
# ════════════════════════════════════════════════════════════════════════
walls += [
    horiz("border_top_l",   -27.5, 40, 45),   # X ∈ [-50, -5]
    horiz("border_top_r",    27.5, 40, 45),   # X ∈ [5, 50]
    horiz("border_bottom",     0, -40, 100),
    vert( "border_left",    -50,    0,  80),
    vert( "border_right",    50,    0,  80),
]

# ════════════════════════════════════════════════════════════════════════
#  DEAD-END ALCOVE  — attached to the north border, opening south into
#  the warehouse.  interior X ∈ [-5, 5], Y ∈ [40, 48]; 6 m wide opening
#  at Y=40.  Robot drives in, must reverse out (loop closure).
# ════════════════════════════════════════════════════════════════════════
walls += [
    vert( "alcove_left",  -5, 44, 8),   # Y ∈ [40, 48]
    vert( "alcove_right",  5, 44, 8),
    horiz("alcove_back",   0, 48, 10),  # X ∈ [-5, 5]
]

# ════════════════════════════════════════════════════════════════════════
#  CENTRAL PLAZA  — 36 × 24 m open space with 12 pillars
#    walls: X ∈ [-18, 18], Y ∈ [-12, 12]
#    top/bottom gaps (4 m) connect to curved corridors
#    left/right gaps (4 m) connect to narrow corridors
# ════════════════════════════════════════════════════════════════════════
walls += [
    # Top wall (Y=12), gap at X ∈ [-2, 2]
    horiz("plaza_top_l",  -10,  12, 16),
    horiz("plaza_top_r",   10,  12, 16),
    # Bottom wall (Y=-12), gap at X ∈ [-2, 2]
    horiz("plaza_bot_l",  -10, -12, 16),
    horiz("plaza_bot_r",   10, -12, 16),
    # Left wall (X=-18), gap at Y ∈ [-2, 2]
    vert( "plaza_left_t", -18,   7, 10),   # Y ∈ [2, 12]
    vert( "plaza_left_b", -18,  -7, 10),   # Y ∈ [-12, -2]
    # Right wall (X=18), gap at Y ∈ [-2, 2]
    vert( "plaza_right_t", 18,   7, 10),
    vert( "plaza_right_b", 18,  -7, 10),
]

# Plaza pillars — keep a clear 4×4 m centre aisle
scatter_pillars("plaza_p", -16, 16, -10, 10, 12,
                exclude=[(-2, -2, 4, 4)])

# ════════════════════════════════════════════════════════════════════════
#  NARROW CORRIDORS  (×2)  — 24 m long, 2 m wide, flanking the plaza
#    Left:  X ∈ [-44, -20], walls at X=-44 and X=-18 (plaza wall)
#    Right: X ∈ [20, 44],   walls at X=20 (plaza wall) and X=44
#    Top/bottom caps have gaps for entry/exit
# ════════════════════════════════════════════════════════════════════════
walls += [
    # Left corridor
    vert( "corr_l_out",  -44,   0, 24),
    horiz("corr_l_top_l", -38,  12,  8),   # X ∈ [-42, -34]
    horiz("corr_l_top_r", -27,  12,  6),   # X ∈ [-30, -24]
    horiz("corr_l_bot_l", -38, -12,  8),   # X ∈ [-42, -34]
    horiz("corr_l_bot_r", -27, -12,  6),   # X ∈ [-30, -24]
    # Right corridor
    vert( "corr_r_out",   44,   0, 24),
    horiz("corr_r_top_l",  27,  12,  6),   # X ∈ [24, 30]
    horiz("corr_r_top_r",  38,  12,  8),   # X ∈ [34, 42]
    horiz("corr_r_bot_l",  27, -12,  6),
    horiz("corr_r_bot_r",  38, -12,  8),
]

# ════════════════════════════════════════════════════════════════════════
#  PILLAR FORESTS  (×2)  — top-left & top-right corners
# ════════════════════════════════════════════════════════════════════════
scatter_pillars("pf_left",  -46, -28, 26, 38, 10)
scatter_pillars("pf_right",  28,  46, 26, 38, 10,
                exclude=[(28, 28, 8, 8)])   # keep room_b clear

# ════════════════════════════════════════════════════════════════════════
#  ROOMS  — 8×8 enclosures with 2 m door + interior pillar
# ════════════════════════════════════════════════════════════════════════
rooms = [
    ("room_a", -21,  32, "bottom"),
    ("room_b",  32,  32, "bottom"),
    ("room_c",  -5.5, -24, "top"),
]

for rname, cx, cy, door in rooms:
    half = 4
    gap = 2.0
    seg = half - gap/2    # 3 m wall length beside door
    off = half/2 + gap/4  # 2.5 m — centre of each wall segment

    # Bottom wall (Y = cy - half)
    if door == "bottom":
        walls.append( horiz(f"{rname}_bot_l", cx - off, cy - half, seg) )
        walls.append( horiz(f"{rname}_bot_r", cx + off, cy - half, seg) )
    else:
        walls.append( horiz(f"{rname}_bot",   cx,       cy - half, half*2) )

    # Top wall
    if door == "top":
        walls.append( horiz(f"{rname}_top_l", cx - off, cy + half, seg) )
        walls.append( horiz(f"{rname}_top_r", cx + off, cy + half, seg) )
    else:
        walls.append( horiz(f"{rname}_top",   cx,       cy + half, half*2) )

    # Left wall
    if door == "left":
        walls.append( vert(f"{rname}_left_t", cx - half, cy + off, seg) )
        walls.append( vert(f"{rname}_left_b", cx - half, cy - off, seg) )
    else:
        walls.append( vert(f"{rname}_left",   cx - half, cy,       half*2) )

    # Right wall
    if door == "right":
        walls.append( vert(f"{rname}_right_t", cx + half, cy + off, seg) )
        walls.append( vert(f"{rname}_right_b", cx + half, cy - off, seg) )
    else:
        walls.append( vert(f"{rname}_right",  cx + half, cy,       half*2) )

    # Interior pillar
    rand2 = random.Random(rname)
    px = cx + rand2.uniform(-2, 2)
    py = cy + rand2.uniform(-2, 2)
    walls.append(pillar(f"{rname}_pillar", round(px, 1), round(py, 1), 0.5))

# ════════════════════════════════════════════════════════════════════════
#  WAREHOUSE  — north-central, 5 parallel shelves
#    Bounding box: X ∈ [-10, 20], Y ∈ [24, 38]
#    Open at the top (Y=38) toward the border strip + alcove
# ════════════════════════════════════════════════════════════════════════
wh_l, wh_r = -10, 20
wh_b, wh_t = 24, 38
walls += [
    vert("warehouse_left",  wh_l, (wh_b+wh_t)/2, wh_t-wh_b),
    vert("warehouse_right", wh_r, (wh_b+wh_t)/2, wh_t-wh_b),
]
# Shelves (horizontal, irregular gaps between them)
for i, y in enumerate([25, 27.5, 30.5, 33.5, 36]):
    walls.append( horiz(f"shelf_{i}", (wh_l+wh_r)/2, y, wh_r-wh_l-3) )

# ════════════════════════════════════════════════════════════════════════
#  THE GRID  (×2)  — 3×3 solid 8 m blocks, 3 m corridors between them
#    bottom-left (-31, -25) & bottom-right (31, -25)
#    Entries from the north via the vertical corridors (no top cap walls)
# ════════════════════════════════════════════════════════════════════════
def solid_block(name, cx, cy, s=8):
    return _box(name, cx, cy, s, s, 0, COL)

def make_grid_blocks(name_prefix, ox, oy):
    pitch = 11  # block + corridor
    blocks = []
    for row in range(3):
        for col in range(3):
            x = ox - pitch + col * pitch
            y = oy - pitch + row * pitch
            blocks.append(solid_block(f"{name_prefix}_{row}_{col}", x, y))
    return blocks

for grid_name, gx in [("grid_l", -31), ("grid_r", 31)]:
    walls.extend(make_grid_blocks(grid_name, gx, -25))

# ════════════════════════════════════════════════════════════════════════
#  CURVED CORRIDORS  — angled wall segments:
#    upper: S-curve from the left side to the right (Y ≈ 14 → 21)
#    lower: gentle arc below the plaza (Y ≈ -14 → -18)
# ════════════════════════════════════════════════════════════════════════
def curve_seg(name, x1, y1, x2, y2):
    dx = x2 - x1; dy = y2 - y1
    length = math.hypot(dx, dy)
    cx = (x1 + x2)/2; cy = (y1 + y2)/2
    yaw = math.degrees(math.atan2(dy, dx))
    return _box(name, cx, cy, length, W, yaw)

# Upper curve (left half) — from the left side toward the centre
pts_upper_l = [
    (-30, 14), (-24, 15), (-18, 17), (-12, 18),
    (-6, 19),  (0, 20),
]
for i in range(len(pts_upper_l) - 1):
    walls.append(curve_seg(f"curve_ul_{i}",
                           *pts_upper_l[i], *pts_upper_l[i+1]))

# Upper curve (right half) — from the centre toward the right
pts_upper_r = [
    (0, 19),  (6, 20), (12, 21), (18, 21),
    (24, 20), (30, 18), (36, 16), (42, 14),
]
for i in range(len(pts_upper_r) - 1):
    walls.append(curve_seg(f"curve_ur_{i}",
                           *pts_upper_r[i], *pts_upper_r[i+1]))

# Lower curve — below the plaza, guiding toward the grids
pts_lower = [
    (-22, -14), (-16, -16), (-10, -17), (-4, -17),
    (2, -17),  (8, -18),   (14, -18),  (20, -17),
]
for i in range(len(pts_lower) - 1):
    walls.append(curve_seg(f"curve_lo_{i}",
                           *pts_lower[i], *pts_lower[i+1]))

# ════════════════════════════════════════════════════════════════════════
#  EXTRA PILLARS  — scattered in remaining open areas (avoid all zones)
# ════════════════════════════════════════════════════════════════════════
exclusions = [
    # plaza
    (-18, -12, 36, 24),
    # left grid
    (-46, -40, 30, 30),
    # right grid
    (16, -40, 30, 30),
    # warehouse
    (-10, 24, 30, 14),
    # rooms A/B/C (8×8)
    (-25, 28, 8, 8), (28, 28, 8, 8), (-9.5, -28, 8, 8),
    # pillar forests
    (-46, 26, 18, 12), (28, 26, 18, 12),
]
scatter_pillars("extra", -46, 46, -36, 36, 10, exclude=exclusions)

# ────────────────────────────────────────────────────────────────────
#  SDF TEMPLATE
# ────────────────────────────────────────────────────────────────────

PLUGINS = """    <plugin
      filename="gz-sim-physics-system"
      name="gz::sim::systems::Physics">
    </plugin>
    <plugin
      filename="gz-sim-sensors-system"
      name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin
      filename="gz-sim-scene-broadcaster-system"
      name="gz::sim::systems::SceneBroadcaster">
    </plugin>
    <plugin
      filename="gz-sim-user-commands-system"
      name="gz::sim::systems::UserCommands">
    </plugin>"""

print(f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="maze_large">
    <physics name="default" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

{PLUGINS}

    <scene>
      <ambient>0.4 0.4 0.4 1</ambient>
      <background>0.7 0.7 0.7 1</background>
      <shadows>false</shadows>
    </scene>

    <light name="sun" type="directional">
      <pose>0 0 20 0 0 0</pose>
      <diffuse>0.7 0.7 0.7 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
    </light>

    <!-- Ground plane -->
    <model name="ground">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>{150*SCALE:.0f} {120*SCALE:.0f}</size>
            </plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>{150*SCALE:.0f} {120*SCALE:.0f}</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.5 0.5 0.5 1</ambient>
            <diffuse>0.5 0.5 0.5 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <!-- ================================================================ -->
    <!--  STRUCTURES                                                       -->
    <!-- ================================================================ -->""")

for w in walls:
    print()
    print(w)

print("""
    <!-- ================================================================ -->
    <!--  ROBOT                                                           -->
    <!-- ================================================================ -->""")

print(f"""
    <include>
      <uri>model://simple_robot</uri>
      <pose>{(-30*SCALE):.1f} 0 0.05 0 0 0</pose>
    </include>
  </world>
</sdf>""")
