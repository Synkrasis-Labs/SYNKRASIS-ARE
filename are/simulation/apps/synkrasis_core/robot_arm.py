# Copyright (c) Meta Platforms
# and Synkrasis Labs. All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file
# in the root directory of this source tree.

from dataclasses import dataclass

from are.simulation.apps.core_app import COREApp
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import type_check


@dataclass
class Pose:
    x: float
    y: float
    z: float
    yaw: float = 0.0


@dataclass
class WorkspaceBounds:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float


@dataclass
class XYRect:
    xmin: float
    xmax: float
    ymin: float
    ymax: float


@dataclass
class Station:
    name: str
    pose: Pose


@dataclass
class Object3D:
    name: str
    weight: float  # kg
    pose: Pose  # yaw is unused for objects; included for uniformity


@dataclass
class RoboticArmState:
    # Kinematics / pose
    pose: Pose
    home_pose: Pose

    # Gripper/load
    gripper_closed: bool
    holding_object: str | None
    current_load: float
    load_capacity: float  # kg

    # Safety
    safety_mode: bool

    # Workspace and exclusions
    workspace_bounds: WorkspaceBounds
    no_go_xy: list[XYRect]

    # Tolerances
    pick_tolerance_xy: float
    pick_tolerance_z: float
    place_tolerance_xy: float
    place_tolerance_z: float

    # Stations & objects
    stations: dict[str, Station]
    objects: dict[str, Object3D]

    def __post_init__(self):
        b = self.workspace_bounds
        assert b.xmin <= b.xmax and b.ymin <= b.ymax and b.zmin <= b.zmax, (
            "Invalid workspace bounds"
        )
        assert self.load_capacity >= 0.0, "Negative load capacity"
        assert 0.0 <= self.current_load <= self.load_capacity, "Invalid current load"
        for r in self.no_go_xy:
            assert r.xmin <= r.xmax and r.ymin <= r.ymax, "Invalid no-go rect"
        for o in self.objects.values():
            assert o.weight >= 0.0, f"Negative object weight: {o.name}"


init_state = RoboticArmState(
    pose=Pose(x=0.50, y=0.00, z=0.40, yaw=0.0),
    home_pose=Pose(x=0.50, y=0.00, z=0.40, yaw=0.0),
    gripper_closed=False,
    holding_object=None,
    current_load=0.0,
    load_capacity=5.0,
    safety_mode=True,
    workspace_bounds=WorkspaceBounds(
        xmin=0.10, xmax=1.20, ymin=-0.50, ymax=0.50, zmin=0.05, zmax=0.60
    ),
    no_go_xy=[
        XYRect(xmin=0.70, xmax=0.85, ymin=-0.10, ymax=0.10),  # column/human zone
    ],
    pick_tolerance_xy=0.02,
    pick_tolerance_z=0.01,
    place_tolerance_xy=0.02,
    place_tolerance_z=0.01,
    stations={
        "assembly_table": Station("assembly_table", Pose(0.95, 0.20, 0.10, 0.0)),
        "quality_control": Station("quality_control", Pose(1.05, -0.20, 0.10, 0.0)),
        "packaging_area": Station("packaging_area", Pose(0.80, 0.35, 0.10, 0.0)),
    },
    objects={
        "box_small": Object3D("box_small", 2.0, Pose(0.30, 0.35, 0.12, 0.0)),
        "box_large": Object3D("box_large", 4.0, Pose(0.28, -0.30, 0.15, 0.0)),
        "gear_A": Object3D("gear_A", 1.0, Pose(0.60, 0.10, 0.11, 0.0)),
        "panel_X": Object3D("panel_X", 3.0, Pose(0.90, -0.10, 0.14, 0.0)),
    },
)


# -----------------------------
# App
# -----------------------------


class RobotArmApp(COREApp[RoboticArmState]):
    """
    METΑ ARE-compatible app for a fixed-base industrial robotic arm.
    Tools mirror your original API (names, preconditions, failure texts).
    """

    init_state = init_state

    # ---------- Helpers ----------
    def _within_bounds(self, x: float, y: float, z: float) -> bool:
        b = self.state.workspace_bounds
        return b.xmin <= x <= b.xmax and b.ymin <= y <= b.ymax and b.zmin <= z <= b.zmax

    def _in_no_go_zone(self, x: float, y: float) -> bool:
        for rect in self.state.no_go_xy:
            if rect.xmin <= x <= rect.xmax and rect.ymin <= y <= rect.ymax:
                return True
        return False

    def _dist_xy(self, a: Pose | dict[str, float], b: Pose | dict[str, float]) -> float:
        if isinstance(a, dict):
            ax, ay = a["x"], a["y"]
        else:
            ax, ay = a.x, a.y
        if isinstance(b, dict):
            bx, by = b["x"], b["y"]
        else:
            bx, by = b.x, b.y
        dx, dy = ax - bx, ay - by
        return (dx * dx + dy * dy) ** 0.5

    # ---------- Tools ----------
    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unlock_safety_mode(self) -> str:
        self.state.safety_mode = False
        return "Safety mode unlocked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def lock_safety_mode(self) -> str:
        self.state.safety_mode = True
        return "Safety mode locked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_to(
        self,
        x: float,
        y: float,
        z: float,
        yaw: float | None = None,
        speed: float | None = None,
    ) -> str:
        if self.state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before moving."

        if not self._within_bounds(x, y, z):
            return "ERROR: Target pose out of workspace bounds."

        if self._in_no_go_zone(x, y):
            return "ERROR: Target pose lies within a no-go zone."

        self.state.pose.x = x
        self.state.pose.y = y
        self.state.pose.z = z
        if yaw is not None:
            self.state.pose.yaw = yaw
        # speed accepted, ignored in this simulation
        p = self.state.pose
        return f"Moved to (x={p.x:.2f}, y={p.y:.2f}, z={p.z:.2f}, yaw={p.yaw:.2f})."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_home(self) -> str:
        if self.state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before moving."
        h = self.state.home_pose
        return self.move_to(h.x, h.y, h.z, h.yaw)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def open_gripper(self) -> str:
        self.state.gripper_closed = False
        return "Gripper opened."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def close_gripper(self) -> str:
        self.state.gripper_closed = True
        return "Gripper closed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def pick(self, object_name: str) -> str:
        s = self.state
        if s.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before picking."
        if s.holding_object is not None:
            return "ERROR: Already holding an object."
        obj = s.objects.get(object_name)
        if obj is None:
            return "ERROR: Unknown object name."
        if s.gripper_closed:
            return "ERROR: Gripper must be open before pick."

        pose = s.pose
        target = obj.pose
        if (self._dist_xy(pose, target) > s.pick_tolerance_xy) or (
            abs(pose.z - target.z) > s.pick_tolerance_z
        ):
            return "ERROR: Pose not aligned for pick (tolerance exceeded)."
        if obj.weight > s.load_capacity:
            return "ERROR: Object too heavy for gripper."

        s.holding_object = obj.name
        s.current_load = obj.weight
        s.gripper_closed = True
        return f"Picked '{obj.name}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def place(self) -> str:
        s = self.state
        if s.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before placing."
        if s.holding_object is None:
            return "ERROR: No object to place."

        p = s.pose
        if not self._within_bounds(p.x, p.y, p.z):
            return "ERROR: Cannot place outside workspace bounds."
        if self._in_no_go_zone(p.x, p.y):
            return "ERROR: Cannot place in a no-go zone."

        # Update object pose and clear load/state
        obj_name = s.holding_object
        s.objects[obj_name].pose = Pose(p.x, p.y, p.z, 0.0)
        s.holding_object = None
        s.current_load = 0.0
        s.gripper_closed = False
        return f"Placed '{obj_name}' at (x={p.x:.2f}, y={p.y:.2f}, z={p.z:.2f})."

    # -------- READ-ONLY TOOLS --------

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def sense_pose(self) -> dict[str, float]:
        p = self.state.pose
        return {"x": p.x, "y": p.y, "z": p.z, "yaw": p.yaw}

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def sense_gripper(self) -> str:
        return "closed" if self.state.gripper_closed else "open"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_objects(self) -> dict[str, dict]:
        return {
            name: {
                "weight": o.weight,
                "pose": {"x": o.pose.x, "y": o.pose.y, "z": o.pose.z},
            }
            for name, o in self.state.objects.items()
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_object_pose(self, object_name: str) -> dict:
        o = self.state.objects.get(object_name)
        if o is None:
            return {"error": "Unknown object name."}
        return {"x": o.pose.x, "y": o.pose.y, "z": o.pose.z}

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_station_pose(self, station_name: str) -> dict:
        st = self.state.stations.get(station_name)
        if st is None:
            return {"error": "Unknown station name."}
        return {"x": st.pose.x, "y": st.pose.y, "z": st.pose.z, "yaw": st.pose.yaw}
