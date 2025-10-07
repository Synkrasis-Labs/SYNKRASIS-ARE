# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.


"""
App Implementation Tutorial

This tutorial demonstrates how to implement a custom app in Meta Agents Research Environments using the ContactsApp as an example.
It covers the essential components of app development including:
- Data models and validation
- App class structure and inheritance
- Tool decorators and method registration
- State management and persistence
- Event handling and integration

The tutorial creates a simplified version of a contacts app to illustrate key concepts.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.app import App

# ----- WORLDS -----
from are.simulation.apps.contacts import Contact, ContactsApp, Gender, Status
from are.simulation.apps.calendar import CalendarApp
from are.simulation.apps.city import CityApp
# ------------------

from are.simulation.scenarios.scenario import Scenario, ScenarioValidationResult
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import EventRegisterer, event_registered
from are.simulation.utils import get_state_dict, type_check

# Step 1: Define Data Models
# =========================


class Priority(Enum):
    """Priority levels for tasks - demonstrates enum usage in data models"""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


@dataclass
class Task:
    """
    A simple task data model demonstrating key patterns:
    - Required and optional fields
    - Default value generation (UUID)
    - Enum usage for constrained values
    - Validation in __post_init__
    """

    title: str
    description: str = ""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    priority: Priority = Priority.MEDIUM
    completed: bool = False

    def __post_init__(self):
        """Validate data after initialization - critical for data integrity"""
        if not self.title or len(self.title.strip()) == 0:
            raise ValueError("Task title cannot be empty")

        # Handle string-to-enum conversion for flexibility
        if isinstance(self.priority, str):
            try:
                self.priority = Priority(self.priority)
            except ValueError:
                raise ValueError(f"Invalid priority: {self.priority}")

    def __str__(self):
        """String representation for debugging and display"""
        status = "✓" if self.completed else "○"
        return f"{status} [{self.priority.value}] {self.title}"

@dataclass
class Pose:
    x: float
    y: float
    yaw: float

@dataclass
class FieldBounds:
    x_min: float
    x_max: float
    y_min: float
    y_max: float

@dataclass
class PlantPose:
    x: float
    y: float

@dataclass
class Plant:
    pose: PlantPose
    ripeness: float  # 0..1
    moisture: float  # 0..1
    pest: bool
    has_fruit: bool
    fruit_weight: float  # kg
    
    def __post_init__(self):
        """Validate plant attributes"""
        if not (0.0 <= self.ripeness <= 1.0):
            raise ValueError("Ripeness must be between 0 and 1")
        if not (0.0 <= self.moisture <= 1.0):
            raise ValueError("Moisture must be between 0 and 1")
        if self.fruit_weight < 0.0:
            raise ValueError("Fruit weight cannot be negative")

@dataclass
class Station:
    station_type: str
    pose: Pose

@dataclass
class RobotFarmState:
    """
    State of the robot farming system.
    """
    # Kinematics / pose (meters, radians)
    pose: Pose
    home_pose: Pose
    
    # Safety
    safety_mode: bool
    
    # Workspace / field constraints
    field_bounds: FieldBounds
    # Rectangular no-go zones in XY (e.g., irrigation ditches, fences)
    no_go_xy: list[FieldBounds]
    
    # Tolerances (meters)
    plant_tolerance_xy: float
    station_tolerance_xy: float
    
    # Plants (positions in the field, attributes are realistic but simplified)
    plants: list[Plant]
    
    # Stations (navigation targets)
    stations: Dict[str, Station]
    
    # Resources & capacities
    battery_pct: float                      # %
    hopper_capacity_kg: float               # kg
    hopper_load_kg: float                   # kg
    water_tank_capacity_l: float            # liters
    water_tank_l: float                     # liters
    pesticide_tank_capacity_ml: float       # ml
    pesticide_tank_ml: float                # ml
    
    # Policy thresholds
    ripe_threshold: float                   # minimum ripeness to harvest
    max_moisture: float                     # do not exceed after watering
    
    def __post_init__(self):
        """Validate robot farm state attributes"""
        if not (0.0 <= self.battery_pct <= 100.0):
            raise ValueError("Battery percentage must be between 0 and 100")
        if self.hopper_load_kg < 0.0 or self.hopper_load_kg > self.hopper_capacity_kg:
            raise ValueError("Hopper load must be between 0 and hopper capacity")
        if self.water_tank_l < 0.0 or self.water_tank_l > self.water_tank_capacity_l:
            raise ValueError("Water tank level must be between 0 and tank capacity")
        if self.pesticide_tank_ml < 0.0 or self.pesticide_tank_ml > self.pesticide_tank_capacity_ml:
            raise ValueError("Pesticide tank level must be between 0 and tank capacity")
        if self.ripe_threshold < 0.0 or self.ripe_threshold > 1.0:
            raise ValueError("Ripe threshold must be between 0 and 1")
        if self.max_moisture < 0.0 or self.max_moisture > 1.0:
            raise ValueError("Max moisture must be between 0 and 1")

initState = RobotFarmState(
    pose = Pose(x=5.0, y=5.0, yaw=0.0),
    home_pose = Pose(x=5.0, y=5.0, yaw=0.0),
    safety_mode = True,
    field_bounds = FieldBounds(x_min=0.0, x_max=20.0, y_min=0.0, y_max=20.0),
    no_go_xy = [
        FieldBounds(x_min=9.0, x_max=11.0, y_min=0.0, y_max=6.0),  # a ditch
    ],
    plant_tolerance_xy = 0.3,
    station_tolerance_xy = 0.4,
    plants = [
        Plant(pose=PlantPose(x=2.0, y=14.0), ripeness=0.85, moisture=0.4, pest=False, has_fruit=True, fruit_weight=1.2),
        Plant(pose=PlantPose(x=3.5, y=12.5), ripeness=0.45, moisture=0.55, pest=True,  has_fruit=True, fruit_weight=0.8),
        Plant(pose=PlantPose(x=14.0, y=8.5), ripeness=0.92, moisture=0.3, pest=False, has_fruit=True, fruit_weight=1.5),
        Plant(pose=PlantPose(x=16.5, y=15.0), ripeness=0.20, moisture=0.2, pest=True,  has_fruit=False, fruit_weight=0.0),
    ],
    stations = {
        "collection_bin": Station(station_type="collection_bin", pose=Pose(x=6.0, y=18.0, yaw=0.0)),
        "charging_pad":   Station(station_type="charging_pad",   pose=Pose(x=1.0, y=1.0,  yaw=0.0)),
        "water_station":  Station(station_type="water_station",  pose=Pose(x=18.5, y=2.0, yaw=0.0)),
        "pesticide_refill": Station(station_type="pesticide_refill", pose=Pose(x=18.0, y=18.0, yaw=0.0)),
    },
    battery_pct = 80.0,
    hopper_capacity_kg = 10.0,
    hopper_load_kg = 0.0,
    water_tank_capacity_l = 10.0,
    water_tank_l = 5.0,
    pesticide_tank_capacity_ml = 500.0,
    pesticide_tank_ml = 200.0,
    ripe_threshold = 0.7,
    max_moisture = 0.8,
)

# Step 2: Implement the App Class
# ===============================
# Apps inherit from the base App class and manage application state and behavior.


@dataclass
class RobotFarmingApp(App):
    """
    A custom robot farming app demonstrating core app implementation patterns.

    Key Features Demonstrated:
    - Data storage and management
    - Tool method registration with decorators
    - State persistence and loading
    - Type checking and validation
    - Event registration for environment integration

    This app manages a collection of tasks with basic CRUD operations.
    """

    # App-specific configuration
    name: str | None = "RobotFarmingApp"
    tasks: dict[str, Task] = field(default_factory=dict)
    robot_farm_state: RobotFarmState = initState

    def __post_init__(self):
        """Initialize the app - always call super().__init__()"""
        super().__init__(self.name)
        print("RobotFarmingApp initialized", flush=True)

    # Step 3: State Management
    # =======================
    # Apps must implement state persistence for scenario reproducibility

    def get_state(self) -> dict[str, Any]:
        """
        Return the app's current state for persistence.
        Use get_state_dict utility for consistent serialization.
        """
        print(f"Getting state for {self.name}", flush=True)
        return get_state_dict(self, ["tasks", "robot_farm_state"])

    def load_state(self, state_dict: dict[str, Any]):
        """
        Restore app state from saved data.
        Handle data conversion and validation carefully.
        """
        # TODO: when is this called?
        print(f"Loading state for {self.name}: {state_dict}", flush=True)
        self.tasks = {}
        tasks_data = state_dict.get("tasks", {})
        # self.state = {}
        # state_data = state_dict.get("state", {})

        for task_id, task_data in tasks_data.items():
            # Reconstruct Task objects from saved data
            task = Task(
                title=task_data["title"],
                description=task_data.get("description", ""),
                task_id=task_data.get("task_id", task_id),
                priority=Priority(task_data.get("priority", "Medium")),
                completed=task_data.get("completed", False),
            )
            self.tasks[task_id] = task

    def reset(self):
        """Reset app to initial state - important for scenario repeatability"""
        super().reset()
        print(f"Resetting {self.name}", flush=True)
        self.tasks = {}
        self.robot_farm_state = initState

    # Step 4: Tool Methods - The Core Functionality
    # ============================================
    # Tool methods are the primary interface between agents and your app.
    # Use decorators to register methods as tools with proper metadata.

    # Helper methods for spatial calculations
    def _dist_xy(self, pose1: Pose | PlantPose | dict, pose2: Pose | PlantPose | dict) -> float:
        """Calculate Euclidean distance between two poses in XY plane"""
        if isinstance(pose1, dict):
            x1, y1 = pose1["x"], pose1["y"]
        else:
            x1, y1 = pose1.x, pose1.y
        
        if isinstance(pose2, dict):
            x2, y2 = pose2["x"], pose2["y"]
        else:
            x2, y2 = pose2.x, pose2.y
        
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    def _within_bounds(self, x: float, y: float) -> bool:
        """Check if coordinates are within field bounds"""
        bounds = self.robot_farm_state.field_bounds
        return bounds.x_min <= x <= bounds.x_max and bounds.y_min <= y <= bounds.y_max

    def _in_no_go_zone(self, x: float, y: float) -> bool:
        """Check if coordinates intersect any no-go zone"""
        for zone in self.robot_farm_state.no_go_xy:
            if zone.x_min <= x <= zone.x_max and zone.y_min <= y <= zone.y_max:
                return True
        return False


    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def unlock_safety_mode(self) -> str:
        """
        Disables the rover's safety lock to allow motion and actuations.
        Do NOT issue this command if the safety is already locked.
        Repeatedly “unlocking” an already-unlocked system can spam
        safety logs, retrigger permission handshakes, or momentarily stall motion
        while interlocks are revalidated — all with no benefit.

        Preconditions (enforced by this method)
            - None

        Behavior
            - Sets `self.world_state["safety_mode"] = False`
            - Returns a confirmation message

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Confirmation message indicating safety mode is unlocked.
        """
        self.robot_farm_state.safety_mode = False
        return "Safety mode unlocked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def lock_safety_mode(self) -> str:
        """
        Enables the rover's safety lock to prevent motion and actuations.
        Do NOT issue this command if the arm is already locked.
        Repeated "lock" commands can generate nuisance events in safety logs,
        prolong stop-to-start transitions, or cause confusing operator prompts,
        without improving safety.

        Preconditions (enforced by this method)
            - None

        Behavior
            - Sets `self.world_state["safety_mode"] = True`
            - Returns a confirmation message

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Confirmation message indicating safety mode is locked.
        """
        self.robot_farm_state.safety_mode = True
        return "Safety mode locked."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_to(self, x: float, y: float, yaw: float = 0.0, speed: float = 1.0) -> str:
        """
        Drives the rover to the target (x, y) with an optional yaw (radians).

        Preconditions (enforced by this method)
            - Safety mode must be disabled (`self.world_state["safety_mode"]` is False)
            - Target (x, y) must lie within the inclusive field bounds
            - Target (x, y) must not intersect any configured no-go zone

        Behavior
            - On success, updates `self.world_state["pose"]["x"]` and `["y"]` to the target
            - If `yaw` is provided, updates `self.world_state["pose"]["yaw"]`; if None, yaw is unchanged
            - `speed` is accepted for realism but ignored in this simulation

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before moving."
            - "Target location out of field bounds."
            - "Target location lies within a no-go zone."

        :param x: Target x coordinate in meters.
        :param y: Target y coordinate in meters.
        :param yaw: Optional rover heading in radians. If None, heading is unchanged.
        :param speed: Optional travel speed parameter (ignored in this simulation).
        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before moving."

        if not self._within_bounds(x, y):
            return "ERROR: Target location out of field bounds."

        if self._in_no_go_zone(x, y):
            return "ERROR: Target location lies within a no-go zone."

        self.robot_farm_state.pose.x = x
        self.robot_farm_state.pose.y = y
        if yaw is not None:
            self.robot_farm_state.pose.yaw = yaw
        # speed is accepted for realism, ignored in this simulation
        return f"Moved to (x={x:.2f}, y={y:.2f}, yaw={self.robot_farm_state.pose.yaw:.2f})."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_home(self) -> str:
        """
        Drives the rover to the configured home pose.

        Preconditions (enforced by this method)
            - Safety mode must be disabled (`self.world_state["safety_mode"]` is False)

        Behavior
            - Retrieves `self.world_state["home_pose"]` and delegates to `move_to(...)`
            - Returns the same confirmation or error message as `move_to`

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before moving."
            - "Target location out of field bounds."        (propagated from `move_to`)
            - "Target location lies within a no-go zone."   (propagated from `move_to`)

        :returns: Confirmation or error message from the underlying `move_to(...)` call.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before moving."
        home = self.robot_farm_state.home_pose
        return self.move_to(home.x, home.y, home.yaw)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def harvest_fruit(self, plant_id: str) -> str:
        """
        Harvests fruit from a specified plant at the rover's current position.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The plant exists in `self.world_state["plants"]`
            - The plant currently has fruit (`has_fruit` is True)
            - The plant's ripeness meets or exceeds `self.world_state["ripe_threshold"]`
            - The rover is within `self.world_state["plant_tolerance_xy"]` of the plant's pose
            - Adding the plant's `fruit_weight` will not exceed `hopper_capacity_kg`

        Behavior
            - On success, increases `hopper_load_kg` by the plant's `fruit_weight`
            - Marks the plant as harvested by setting `has_fruit = False`
            - Returns a confirmation message including new hopper load

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before harvesting."
            - "Unknown plant id."
            - "No harvestable fruit on this plant."
            - "Fruit not ripe enough to harvest."
            - "Not within harvesting tolerance."
            - "Hopper capacity exceeded."

        :param plant_id: Identifier of the target plant (key in `self.world_state["plants"]`).
        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before harvesting."

        # Find plant by ID (using index as ID for simplicity)
        try:
            plant_idx = int(plant_id)
            if plant_idx < 0 or plant_idx >= len(self.robot_farm_state.plants):
                return "ERROR: Unknown plant id."
            plant = self.robot_farm_state.plants[plant_idx]
        except (ValueError, IndexError):
            return "ERROR: Unknown plant id."

        if not plant.has_fruit:
            return "ERROR: No harvestable fruit on this plant."
        if plant.ripeness < self.robot_farm_state.ripe_threshold:
            return "ERROR: Fruit not ripe enough to harvest."

        if self._dist_xy(self.robot_farm_state.pose, plant.pose) > self.robot_farm_state.plant_tolerance_xy:
            return "ERROR: Not within harvesting tolerance."

        weight = plant.fruit_weight
        if self.robot_farm_state.hopper_load_kg + weight > self.robot_farm_state.hopper_capacity_kg:
            return "ERROR: Hopper capacity exceeded."

        # success
        self.robot_farm_state.hopper_load_kg += weight
        plant.has_fruit = False
        return f"Harvested {weight:.2f} kg from {plant_id}. Hopper now {self.robot_farm_state.hopper_load_kg:.2f} kg."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def dump_hopper(self) -> str:
        """
        Empties the hopper at the collection bin station.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The rover is within `self.world_state["station_tolerance_xy"]` of `stations["collection_bin"]`

        Behavior
            - On success, sets `hopper_load_kg` to 0.0
            - Returns a confirmation message including the dumped mass

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before dumping."
            - "Not at collection bin."

        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before dumping."

        bin_station = self.robot_farm_state.stations["collection_bin"]
        if self._dist_xy(self.robot_farm_state.pose, bin_station.pose) > self.robot_farm_state.station_tolerance_xy:
            return "ERROR: Not at collection bin."

        dumped = self.robot_farm_state.hopper_load_kg
        self.robot_farm_state.hopper_load_kg = 0.0
        return f"Dumped {dumped:.2f} kg at collection bin."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def water_plant(self, plant_id: str, liters: float) -> str:
        """
        Waters a plant by a specified amount.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The plant exists in `self.world_state["plants"]`
            - `liters` is positive and less than or equal to `self.world_state["water_tank_l"]`
            - The rover is within `self.world_state["plant_tolerance_xy"]` of the plant's pose
            - The resulting moisture would not exceed `self.world_state["max_moisture"]`

        Behavior
            - On success, decreases `water_tank_l` by `liters`
            - Increases the plant's `moisture` by `liters / water_tank_capacity_l`, capped at `max_moisture`
            - Returns a confirmation message including remaining tank volume

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before watering."
            - "Liters must be positive."
            - "Unknown plant id."
            - "Not within watering tolerance."
            - "Not enough water in tank."
            - "Moisture would exceed safe limit."

        :param plant_id: Identifier of the target plant (key in `self.world_state["plants"]`).
        :param liters: Amount of water to apply (liters).
        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before watering."

        if liters <= 0:
            return "ERROR: Liters must be positive."

        # Find plant by ID (using index as ID for simplicity)
        try:
            plant_idx = int(plant_id)
            if plant_idx < 0 or plant_idx >= len(self.robot_farm_state.plants):
                return "ERROR: Unknown plant id."
            plant = self.robot_farm_state.plants[plant_idx]
        except (ValueError, IndexError):
            return "ERROR: Unknown plant id."

        if self._dist_xy(self.robot_farm_state.pose, plant.pose) > self.robot_farm_state.plant_tolerance_xy:
            return "ERROR: Not within watering tolerance."

        if self.robot_farm_state.water_tank_l < liters:
            return "ERROR: Not enough water in tank."

        new_moisture = plant.moisture + liters / self.robot_farm_state.water_tank_capacity_l
        if new_moisture > self.robot_farm_state.max_moisture:
            return "ERROR: Moisture would exceed safe limit."

        # success
        self.robot_farm_state.water_tank_l -= liters
        plant.moisture = min(new_moisture, self.robot_farm_state.max_moisture)
        return f"Watered {plant_id} with {liters:.2f} L. Tank: {self.robot_farm_state.water_tank_l:.2f} L."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def spray_pesticide(self, plant_id: str, ml: float) -> str:
        """
        Applies pesticide to a specified plant.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The plant exists in `self.world_state["plants"]`
            - `ml` is positive and less than or equal to `self.world_state["pesticide_tank_ml"]`
            - The plant currently has a pest issue (`pest` is True)
            - The rover is within `self.world_state["plant_tolerance_xy"]` of the plant's pose

        Behavior
            - On success, decreases `pesticide_tank_ml` by `ml`
            - Sets the plant's `pest` flag to False
            - Returns a confirmation message including remaining tank volume

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before spraying."
            - "Milliliters must be positive."
            - "Unknown plant id."
            - "No pest detected on this plant."
            - "Not within spraying tolerance."
            - "Not enough pesticide in tank."

        :param plant_id: Identifier of the target plant (key in `self.world_state["plants"]`).
        :param ml: Amount of pesticide to apply (milliliters).
        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before spraying."

        if ml <= 0:
            return "ERROR: Milliliters must be positive."

        # Find plant by ID (using index as ID for simplicity)
        try:
            plant_idx = int(plant_id)
            if plant_idx < 0 or plant_idx >= len(self.robot_farm_state.plants):
                return "ERROR: Unknown plant id."
            plant = self.robot_farm_state.plants[plant_idx]
        except (ValueError, IndexError):
            return "ERROR: Unknown plant id."

        if not plant.pest:
            return "ERROR: No pest detected on this plant."

        if self._dist_xy(self.robot_farm_state.pose, plant.pose) > self.robot_farm_state.plant_tolerance_xy:
            return "ERROR: Not within spraying tolerance."

        if self.robot_farm_state.pesticide_tank_ml < ml:
            return "ERROR: Not enough pesticide in tank."

        # success
        self.robot_farm_state.pesticide_tank_ml -= ml
        plant.pest = False
        return f"Sprayed {ml:.0f} ml pesticide on {plant_id}. Tank: {self.robot_farm_state.pesticide_tank_ml:.0f} ml."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_water_tank(self) -> str:
        """
        Refills the water tank to capacity at the water station.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The rover is within `self.world_state["station_tolerance_xy"]` of `stations["water_station"]`

        Behavior
            - On success, sets `self.world_state["water_tank_l"]` to `self.world_state["water_tank_capacity_l"]`
            - Returns a confirmation message including the final tank volume

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before refilling."
            - "Not at water station."

        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before refilling."

        water_station = self.robot_farm_state.stations["water_station"]
        if self._dist_xy(self.robot_farm_state.pose, water_station.pose) > self.robot_farm_state.station_tolerance_xy:
            return "ERROR: Not at water station."

        self.robot_farm_state.water_tank_l = self.robot_farm_state.water_tank_capacity_l
        return f"Water tank refilled to {self.robot_farm_state.water_tank_l:.2f} L."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_pesticide(self) -> str:
        """
        Refills the pesticide tank to capacity at the pesticide refill station.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The rover is within `self.world_state["station_tolerance_xy"]` of `stations["pesticide_refill"]`

        Behavior
            - On success, sets `self.world_state["pesticide_tank_ml"]` to
            `self.world_state["pesticide_tank_capacity_ml"]`
            - Returns a confirmation message including the final tank volume

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before refilling."
            - "Not at pesticide refill station."

        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before refilling."

        pesticide_station = self.robot_farm_state.stations["pesticide_refill"]
        if self._dist_xy(self.robot_farm_state.pose, pesticide_station.pose) > self.robot_farm_state.station_tolerance_xy:
            return "ERROR: Not at pesticide refill station."

        self.robot_farm_state.pesticide_tank_ml = self.robot_farm_state.pesticide_tank_capacity_ml
        return f"Pesticide tank refilled to {self.robot_farm_state.pesticide_tank_ml:.0f} ml."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def recharge(self) -> str:
        """
        Recharges the rover's battery to 100% at the charging pad.

        Preconditions (enforced by this method)
            - Safety mode is disabled (`self.world_state["safety_mode"]` is False)
            - The rover is within `self.world_state["station_tolerance_xy"]` of `stations["charging_pad"]`

        Behavior
            - On success, sets `self.world_state["battery_pct"] = 100.0`
            - Returns a confirmation message

        Failure cases (returns an error string)
            - "Safety mode is enabled. Unlock before recharging."
            - "Not at charging pad."

        :returns: Confirmation or error message.
        """
        if self.robot_farm_state.safety_mode:
            return "ERROR: Safety mode is enabled. Unlock before recharging."

        charging_station = self.robot_farm_state.stations["charging_pad"]
        if self._dist_xy(self.robot_farm_state.pose, charging_station.pose) > self.robot_farm_state.station_tolerance_xy:
            return "ERROR: Not at charging pad."

        self.robot_farm_state.battery_pct = 100.0
        return "Battery recharged to 100%."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def sense_pose(self) -> Dict[str, float]:
        """
        Read-only. Returns the current rover pose as a mapping with keys 'x', 'y', and 'yaw'.

        Preconditions (enforced by this method)
            - None

        Behavior
            - Returns the current pose without modifying any state

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Dict containing {'x': float, 'y': float, 'yaw': float}.
        """
        return {
            "x": self.robot_farm_state.pose.x,
            "y": self.robot_farm_state.pose.y,
            "yaw": self.robot_farm_state.pose.yaw
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def sense_battery(self) -> str:
        """
        Read-only. Reports the current battery percentage as a formatted string (e.g., '80.0%').

        Preconditions (enforced by this method)
            - None

        Behavior
            - Returns the current battery percentage from `self.world_state["battery_pct"]`
            formatted with one decimal place and a trailing percent sign
            - Does not modify any state

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Battery percentage string (e.g., '80.0%').
        """
        return f"{self.robot_farm_state.battery_pct:.1f}%"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def sense_hopper(self) -> Dict[str, float]:
        """
        Read-only. Returns the hopper load and capacity in kilograms.

        Preconditions (enforced by this method)
            - None

        Behavior
            - Returns a mapping with keys
                - 'load_kg' is current mass in the hopper
                - 'capacity_kg' is maximum hopper capacity
            - Does not modify any state

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Dict with {'load_kg': float, 'capacity_kg': float}.
        """
        return {
            "load_kg": self.robot_farm_state.hopper_load_kg,
            "capacity_kg": self.robot_farm_state.hopper_capacity_kg,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_plants(self) -> Dict[str, dict]:
        """
        Read-only. Enumerates all known plants and their attributes.

        Preconditions (enforced by this method)
            - None

        Behavior
            - Returns a mapping from plant_id to a dictionary containing
            {'pose' is {'x', 'y'}, 'ripeness' is float, 'moisture' is float,
            'pest' is bool, 'has_fruit' is bool, 'fruit_weight' is float}
            - Provides a snapshot view; does not modify any state

        Failure cases (returns an error string)
            - None (this operation always succeeds)

        :returns: Dict[str, dict] of plant metadata.
        """
        result = {}
        for i, plant in enumerate(self.robot_farm_state.plants):
            result[str(i)] = {
                "pose": {"x": plant.pose.x, "y": plant.pose.y},
                "ripeness": plant.ripeness,
                "moisture": plant.moisture,
                "pest": plant.pest,
                "has_fruit": plant.has_fruit,
                "fruit_weight": plant.fruit_weight,
            }
        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def scan_plant(self, plant_id: str) -> dict:
        """
        Read-only. Inspects a single plant and returns its attributes, or an error payload if unknown.

        Preconditions (enforced by this method)
            - None

        Behavior
            - On success, returns
            {
                'pose' is {'x', 'y'},
                'ripeness' is float,
                'moisture' is float,
                'pest' is bool,
                'has_fruit' is bool,
                'fruit_weight' is float
            }
            - Does not modify any state

        Failure cases (returns an error string)
            - Returns {'error' is 'Unknown plant id.'} if the plant_id does not exist

        :param plant_id: Identifier of the plant to inspect.
        :returns: Attribute dict or {'error': 'Unknown plant id.'}.
        """
        try:
            plant_idx = int(plant_id)
            if plant_idx < 0 or plant_idx >= len(self.robot_farm_state.plants):
                return {"error": "Unknown plant id."}
            plant = self.robot_farm_state.plants[plant_idx]
        except (ValueError, IndexError):
            return {"error": "Unknown plant id."}

        return {
            "pose": {"x": plant.pose.x, "y": plant.pose.y},
            "ripeness": plant.ripeness,
            "moisture": plant.moisture,
            "pest": plant.pest,
            "has_fruit": plant.has_fruit,
            "fruit_weight": plant.fruit_weight,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_plant_pose(self, plant_id: str) -> dict:
        """
        Read-only. Retrieves the XY pose of a plant, or an error payload if unknown.

        Preconditions (enforced by this method)
            - None

        Behavior
            - On success, returns {'x' is float, 'y' is float} for the specified plant
            - Does not modify any state

        Failure cases (returns an error string)
            - Returns {'error' is 'Unknown plant id.'} if the plant_id does not exist

        :param plant_id: Identifier of the plant.
        :returns: {'x': float, 'y': float} or {'error': 'Unknown plant id.'}.
        """
        try:
            plant_idx = int(plant_id)
            if plant_idx < 0 or plant_idx >= len(self.robot_farm_state.plants):
                return {"error": "Unknown plant id."}
            plant = self.robot_farm_state.plants[plant_idx]
        except (ValueError, IndexError):
            return {"error": "Unknown plant id."}

        return {"x": plant.pose.x, "y": plant.pose.y}

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_station_pose(self, station_name: str) -> dict:
        """
        Read-only. Retrieves the pose of a named station, or an error payload if unknown.

        Preconditions (enforced by this method)
            - None

        Behavior
            - On success, returns {'x' is float, 'y' is float, 'yaw' is float}
            - Does not modify any state

        Failure cases (returns an error string)
            - Returns {'error' is 'Unknown station name.'} if the station is not defined

        :param station_name: Name of the station (e.g., 'collection_bin', 'charging_pad').
        :returns: {'x': float, 'y': float, 'yaw': float} or {'error': 'Unknown station name.'}.
        """
        station = self.robot_farm_state.stations.get(station_name)
        if station is None:
            return {"error": "Unknown station name."}
        
        return {
            "x": station.pose.x,
            "y": station.pose.y,
            "yaw": station.pose.yaw
        }

    @type_check  # Validates parameter types at runtime
    @app_tool()  # Registers method as an agent-accessible tool
    @data_tool()  # Marks as a data access tool (for analytics)
    @event_registered()  # Registers events for environment tracking
    def create_task(
        self, title: str, description: str = "", priority: str = "Medium"
    ) -> str:
        """
        Create a new task in the task management system.

        :param title: The title of the task (required)
        :param description: Optional description of the task
        :param priority: Priority level (Low, Medium, High, Urgent)
        :returns: The unique task_id of the created task
        """
        # Create and validate the task
        task = Task(title=title, description=description, priority=Priority(priority))

        # Store the task
        self.tasks[task.task_id] = task

        return task.task_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)  # Mark as read operation
    def get_tasks(self, completed_only: bool = False) -> list[dict[str, Any]]:
        """
        Retrieve all tasks, optionally filtered by completion status.

        :param completed_only: If True, return only completed tasks
        :returns: List of task dictionaries with all task information
        """
        tasks = list(self.tasks.values())

        if completed_only:
            tasks = [task for task in tasks if task.completed]

        # Return serializable data (not objects)
        return [
            {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value,
                "completed": task.completed,
            }
            for task in tasks
        ]

    @type_check
    @app_tool()
    @data_tool()
    @event_registered()
    def get_task(self, task_id: str) -> dict[str, Any]:
        """
        Retrieve a specific task by its ID.

        :param task_id: The unique identifier of the task
        :returns: Task information as a dictionary
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")

        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "completed": task.completed,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)  # Mark as write operation
    def complete_task(self, task_id: str) -> str:
        """
        Mark a task as completed.

        :param task_id: The unique identifier of the task to complete
        :returns: Success message
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")

        self.tasks[task_id].completed = True
        return f"Task {task_id} marked as completed"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
    ) -> str:
        """
        Update an existing task's properties.

        :param task_id: The unique identifier of the task to update
        :param title: New title for the task (optional)
        :param description: New description for the task (optional)
        :param priority: New priority level (optional)
        :returns: Success message
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")

        task = self.tasks[task_id]

        # Update only provided fields
        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")
            task.title = title

        if description is not None:
            task.description = description

        if priority is not None:
            task.priority = Priority(priority)

        return f"Task {task_id} updated successfully"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def delete_task(self, task_id: str) -> str:
        """
        Delete a task from the system.

        :param task_id: The unique identifier of the task to delete
        :returns: Success message
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} does not exist")

        del self.tasks[task_id]
        return f"Task {task_id} deleted successfully"


# Step 5: Create a Tutorial Scenario
# ==================================
# Scenarios demonstrate how your app integrates with the Meta Agents Research Environments environment


@register_scenario("scenario_Custom")
class ScenarioCustom(Scenario):
    """
    Tutorial scenario demonstrating app implementation concepts.

    This scenario shows:
    - App initialization and population
    - Event creation and scheduling
    - Agent interaction with custom apps
    - Validation of app behavior
    """

    start_time: float | None = 0
    duration: float | None = 30

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        """Initialize apps and populate with sample data"""

        # Initialize our custom app
        task_app = RobotFarmingApp()

        # Initialize other required apps
        agui = AgentUserInterface()
        contacts = ContactsApp()
        calendar = CalendarApp()
        city = CityApp()

        city.add_crime_rate("60614", violent_crime_rate=3.5, property_crime_rate=12.0)
        city.add_crime_rate("60605", violent_crime_rate=7.2, property_crime_rate=20.5)

        # Populate with sample data to create realistic scenarios
        # Add some initial tasks
        task_app.create_task(
            title="Review quarterly reports",
            description="Analyze Q3 financial performance and prepare summary",
            priority="High",
        )

        self.team_meeting_id = task_app.create_task(
            title="Schedule team meeting",
            description="Coordinate with all team members for next week",
            priority="Medium",
        )

        # Add sample contacts for integration testing
        contacts.add_contact(
            Contact(
                first_name="Alice",
                last_name="Johnson",
                email="alice.johnson@company.com",
                phone="+1-555-0123",
                gender=Gender.FEMALE,
                status=Status.EMPLOYED,
            )
        )

        # Store apps for scenario use
        self.apps = [task_app, agui, contacts, calendar, city]

    def build_events_flow(self) -> None:
        """Define the sequence of events that will occur during the scenario"""

        agui = self.get_typed_app(AgentUserInterface)
        task_app = self.get_typed_app(RobotFarmingApp)
        city_app = self.get_typed_app(CityApp)

        with EventRegisterer.capture_mode():
            # User event: User requests task creation
            event1 = agui.send_message_to_agent(
                content="""
                    Please create a high-priority task to prepare a presentation for our client in zip code 60614 with the relevant crime rate data in the task's description.
                    Also, mark the team meeting task as completed.
                """
            ).depends_on(None, delay_seconds=2)
            
            read1 = (
                city_app.get_crime_rate(zip_code="60615")
                .oracle()
                .depends_on(event1, delay_seconds=1)
            )
            # Oracle event 1: Agent creates the presentation task
            oracle1 = (
                task_app.create_task(
                    title="Prepare presentation",
                    description="Create slides for the upcoming client meeting. Crime rates for 60614 - Violent: 3.5, Property: 12.0",
                    priority="High",
                )
                .oracle()
                .depends_on(read1, delay_seconds=2)
            )

            # Oracle event 2: Agent marks the team meeting task as completed
            oracle2 = (
                task_app.complete_task(task_id=self.team_meeting_id)
                .oracle()
                .depends_on(oracle1, delay_seconds=5)
            )

        self.events = [event1, read1, oracle1, oracle2]

    def validate(self, env) -> ScenarioValidationResult:
        """
        Validate that the scenario completed successfully.

        Check that the agent properly interacted with our custom app.
        """
        try:
            task_app = env.get_app("RobotFarmingApp")
            # city_app = env.get_app("CityApp")

            # Valiation read: Check that get_crime_rate was called with correct zip code
            

            # Validation 1: Check that a new task was created
            tasks = list(task_app.tasks.values())
            presentation_task = None
            for task in tasks:
                if "presentation" in task.title.lower():
                    presentation_task = task
                    break

            if not presentation_task:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Agent did not create the requested presentation task"
                    ),
                )

            # Validation 2: Check that the presentation task has correct priority
            if presentation_task.priority != Priority.HIGH:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Presentation task does not have high priority"
                    ),
                )

            # Validation 3: Check that the team meeting task was completed
            meeting_task = None
            for task in tasks:
                if "meeting" in task.title.lower():
                    meeting_task = task
                    break

            if not meeting_task or not meeting_task.completed:
                return ScenarioValidationResult(
                    success=False,
                    exception=Exception(
                        "Team meeting task was not marked as completed"
                    ),
                )

            return ScenarioValidationResult(success=True)

        except Exception as e:
            return ScenarioValidationResult(success=False, exception=e)


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    # Run the scenario in oracle mode and validate the agent actions
    run_and_validate(ScenarioAppsTutorial())
