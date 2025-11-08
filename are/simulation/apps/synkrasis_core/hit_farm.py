from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

from are.simulation.apps.app import App
from are.simulation.apps.core_app import COREApp
from are.simulation.types import event_registered
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.utils import type_check


# -----------------------------
# State dataclasses (robot_arm.py style)
# -----------------------------


@dataclass
class DroneState:
    position: tuple[float, float, float] = (15.0, -5.0,0.0)
    speed_mps: float = 10.0
    consumption_rate: float = 0.5
    battery_percentage: float = 100.0
    pesticide_tank_ml: float = 0.0
    camera_status: bool = False
    flight_status: str = 'landed'
    device_id: str | None = None
    pesticide_tank_capacity: float | None = None


@dataclass
class IrrigationSystemState:
    water_pressure_psi: float = 40.0
    master_valve_status: bool = False
    zone_valve_status: dict = field(default_factory=dict)


@dataclass
class SensorNetworkState:
    last_reading_timestamp: datetime | None = None
    cached_data: dict[str, dict] = field(default_factory=dict)


@dataclass
class CentralHubState:
    power_grid_status: bool
    water_supply_liters: float
    pesticide_supply_ml: float
    fertilizer_supply_kg: float
    position: tuple[float, float, float] = (15.0, -5.0,0.0)
    docking_radius: float = 5.0
    seed_inventory: dict[str, int] = field(default_factory=dict)


@dataclass
class WeatherState:
    """Weather state containing current conditions and forecasts."""
    temperature_celsius: float = 22.0
    humidity_percent: float = 60.0
    wind_speed_mps: float = 3.0
    precipitation_mm: float = 0.0
    cloud_cover_percent: float = 30.0
    weather_condition: str = "clear"  # clear, cloudy, rainy, stormy, etc.
    forecast_data: list[dict] = field(default_factory=list)
    weather_alerts: list[dict] = field(default_factory=list)
    last_update: datetime | None = None


class CentralHub(COREApp[CentralHubState]):
    """CentralHub (中央基地)

    中文: 中央基地负责管理电力、水、农药、肥料库存以及停泊设备的状态。
    English: Central hub manages power grid state, water/pesticide/fertilizer inventories, and docking station statuses.

    Attributes:
      - power_grid_status: bool (电网是否在线)
      - water_supply_liters: float (中央储水量，升)
      - pesticide_supply_ml: float (中央农药库存，毫升)
      - fertilizer_supply_kg: float (中央肥料库存，千克)

    Methods (主要方法概览):
      - register_device(device_id, initial_status=None): 注册设备到中央基地 / register a device at the hub
      - recharge_device(device_id, amount=None): 为设备充电 / recharge device battery
      - refill_seeds(device_id, seed_type, count): 发放种子 / dispense seeds
      - refill_water(device_id, amount_liters): 补充水 / refill water
      - refill_pesticide(device_id, amount_ml): 补充农药 / refill pesticide
      - refill_fertilizer(device_id, amount_kg): 补充肥料 / refill fertilizer
    """
    init_state: CentralHubState = CentralHubState(power_grid_status=True, water_supply_liters=10000.0,
                                                  pesticide_supply_ml=50000.0, fertilizer_supply_kg=1000.0,
                                                  position=(15.0, -5.0, 0.0),
                                                  docking_radius=5.0,
                                                  seed_inventory={"corn": 8000, "soybean": 2000, "wheat": 3000,
                                                                  "rice": 3000})

    def __init__(self, farm_state:HitFarmState=None):
        super().__init__()
        self.farm_state = farm_state

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def recharge_device(self, device_id, amount=None):
        """
        Recharge a registered device's battery.
        Args:
            device_id (str): Target device identifier.
            amount (float | None): Percentage points to add; if None, top up to 100%.

        Returns:
            str: Result message or error description.
        """
        device = self.farm_state.get_drone(device_id)
        if device is None:
            device = self.farm_state.get_rover(device_id)
        current = device.state.battery_percentage
        if amount is None:
            delta = 100.0 - current
        else:
            try:
                delta = float(amount)
            except (TypeError, ValueError):
                return "Error: amount must be a number."
            if delta < 0:
                return "Error: amount must be non-negative."
            if current + delta > 100.0:
                delta = 100.0 - current
        device.state.battery_percentage = min(100.0, current + delta)
        return f"Recharged {device_id} by {delta:.2f}%. Battery now {device.state.battery_percentage:.2f}%.'"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_seeds(self, device_id, seed_type, count):
        """
        Dispense seeds from the central inventory to a device.

        Args:
            device_id (str): Recipient device identifier.
            seed_type (str): Seed species key (e.g., "corn").
            count (int): Number of seeds requested.

        Returns:
            str: Message including dispensed amount and remaining central inventory.

        Note:
            This only decrements the central inventory and records a 'last_dispensed_*'
            field for the device. The caller should credit the device's seed bin.
        """
        try:
            requested = int(count)
        except (TypeError, ValueError):
            return "Error: count must be an integer."
        if requested <= 0:
            return "Error: count must be positive."
        available = int(self.state.seed_inventory.get(seed_type, 0))
        if available <= 0:
            return f"Error: no {seed_type} seeds available in central inventory."
        dispensed = min(requested, available)
        self.state.seed_inventory[seed_type] = available - dispensed
        device = self.farm_state.get_rover(device_id)
        current = int(device.state.seed_bin.get(seed_type, 0))
        device.state.seed_bin[seed_type] = current + dispensed

        return f"Dispensed {dispensed} {seed_type} seeds to {device_id}. Central remaining: {self.state.seed_inventory[seed_type]}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_water(self, device_id, amount_liters):
        """
        Refill a device's water tank from the central supply.

        Args:
            device_id (str): Target device identifier.
            amount_liters (float): Requested liters to transfer.

        Returns:
            str: Result message with transferred volume and remaining central water.
        """

        try:
            amount = float(amount_liters)
        except (TypeError, ValueError):
            return "Error: amount must be a number."
        if amount <= 0:
            return "Error: amount must be positive."
        available = min(amount, self.state.water_supply_liters)
        if available <= 0:
            return "Error: no water available in central supply."
        device = self.farm_state.get_rover(device_id)
        device.state.water_tank_liters = device.state.water_tank_liters + available
        self.state.water_supply_liters -= available
        return f"Refilled {device_id} with {available:.2f} L water. Central remaining: {self.state.water_supply_liters:.2f} L."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_pesticide(self, device_id, amount_ml):
        """
        Refill a device's pesticide tank from the central supply.

        Args:
            device_id (str): Target device identifier.
            amount_ml (float): Requested milliliters to transfer.

        Returns:
            str: Result message with transferred volume and remaining central pesticide.
        """
        try:
            amount = float(amount_ml)
        except (TypeError, ValueError):
            return "Error: amount must be a number."
        if amount <= 0:
            return "Error: amount must be positive."
        available = min(amount, self.state.pesticide_supply_ml)
        if available <= 0:
            return "Error: no pesticide available in central supply."

        device = self.farm_state.get_drone(device_id)
        device.state.pesticide_tank_ml = device.state.pesticide_tank_ml + available
        self.state.pesticide_supply_ml -= available
        return f"Refilled {device_id} with {available:.2f} ml pesticide. Central remaining: {self.state.pesticide_supply_ml:.2f} ml."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def refill_fertilizer(self, device_id, amount_kg):
        """
        Refill a device's fertilizer bin from the central supply.

        Args:
            device_id (str): Target device identifier.
            amount_kg (float): Requested kilograms to transfer.

        Returns:
            str: Result message with transferred mass and remaining central fertilizer.
        """
        try:
            amount = float(amount_kg)
        except (TypeError, ValueError):
            return "Error: amount must be a number."
        if amount <= 0:
            return "Error: amount must be positive."
        available = min(amount, self.state.fertilizer_supply_kg)
        if available <= 0:
            return "Error: no fertilizer available in central supply."

        device = self.farm_state.get_rover(device_id)
        device.state.fertilizer_bin_kg = device.state.fertilizer_bin_kg + available
        self.state.fertilizer_supply_kg -= available
        return f"Refilled {device_id} with {available:.2f} kg fertilizer. Central remaining: {self.state.fertilizer_supply_kg:.2f} kg."


class WeatherApp(COREApp[WeatherState]):
    """WeatherApp (天气应用)

    中文: 天气应用负责提供当前天气信息、天气预测、历史数据和天气警报功能。
    English: Weather app provides current weather information, forecasts, historical data and weather alerts.

    Attributes:
      - temperature_celsius: float (当前温度，摄氏度)
      - humidity_percent: float (相对湿度，百分比)
      - wind_speed_mps: float (风速，米/秒)
      - precipitation_mm: float (降雨量，毫米)
      - cloud_cover_percent: float (云量，百分比)
      - weather_condition: str (天气状况描述)
      - forecast_data: list[dict] (天气预测数据)
      - weather_alerts: list[dict] (天气警报列表)

    Methods (主要方法概览):
      - get_current_weather(): 获取当前天气信息 / get current weather conditions
      - get_forecast(hours): 获取未来几小时的天气预测 / get weather forecast for next hours
      - update_weather(new_conditions): 更新天气状态 / update weather conditions
      - add_weather_alert(alert_type, severity, message): 添加天气警报 / add weather alert
      - get_weather_alerts(): 获取当前有效警报 / get active weather alerts
      - clear_weather_alerts(): 清除所有警报 / clear all alerts
    """
    init_state: WeatherState = WeatherState(
        temperature_celsius=22.0,
        humidity_percent=60.0,
        wind_speed_mps=3.0,
        precipitation_mm=0.0,
        cloud_cover_percent=30.0,
        weather_condition="clear",
        forecast_data=[],
        weather_alerts=[],
        last_update=None
    )

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_current_weather(self):
        """
        Get the current weather conditions.

        Returns:
            dict: A mapping with keys:
                wind_speed_mps: float (speed of wind, meters per second)
                precipitation_mm: float (precipitation, millimeters)
                and so on
        """
        from datetime import datetime, timezone
        self.state.last_update = datetime.now(timezone.utc)
        return {
            "temperature_celsius": self.state.temperature_celsius,
            "humidity_percent": self.state.humidity_percent,
            "wind_speed_mps": self.state.wind_speed_mps,
            "precipitation_mm": self.state.precipitation_mm,
            "cloud_cover_percent": self.state.cloud_cover_percent,
            "weather_condition": self.state.weather_condition,
            "last_update": self.state.last_update.isoformat() if self.state.last_update else None
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_forecast(self, hours: int = 24):
        """
        Get weather forecast for the next specified hours.

        Args:
            hours (int): Number of hours to forecast (default: 24, max: 168 for 7 days).

        Returns:
            list[dict] | str: List of forecast entries or error message.
        """
        try:
            hours = int(hours)
        except (TypeError, ValueError):
            return "Error: hours must be an integer."

        if hours <= 0:
            return "Error: hours must be positive."

        if hours > 168:
            hours = 168  # Cap at 7 days

        # Generate or return cached forecast data
        if not self.state.forecast_data or len(self.state.forecast_data) < hours:
            self.generate_forecast(hours)

        return self.state.forecast_data[:hours]

    def generate_forecast(self, hours: int, forecast_entry: dict | None = None):
        """
        Generate synthetic weather forecast data.

        Args:
            hours (int): Number of hours to generate forecast for.
        """
        if forecast_entry:
            self.state.forecast_data = [forecast_entry]
            return


        import random

        self.state.forecast_data = []

        # Use current weather as starting point
        temp = self.state.temperature_celsius
        humidity = self.state.humidity_percent
        wind = self.state.wind_speed_mps

        for i in range(hours):
            # Add some random variation
            temp += random.uniform(-2, 2)
            temp = max(0, min(40, temp))  # Clamp between 0-40°C

            humidity += random.uniform(-5, 5)
            humidity = max(20, min(100, humidity))

            wind += random.uniform(-1, 1)
            wind = max(0, min(20, wind))

            forecast_entry = {
                "time": i,
                "temperature_celsius": round(temp, 1),
                "humidity_percent": round(humidity, 1),
                "wind_speed_mps": round(wind, 1),
                "precipitation_probability": random.randint(0, 100),
            }
            self.state.forecast_data.append(forecast_entry)

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_weather(self, temperature_celsius: float | None = None,
                      humidity_percent: float | None = None,
                      wind_speed_mps: float | None = None,
                      precipitation_mm: float | None = None,
                      cloud_cover_percent: float | None = None,
                      atmospheric_pressure_hpa: float | None = None,
                      weather_condition: str | None = None):
        """
        Update current weather conditions.

        Args:
            temperature_celsius (float | None): New temperature value.
            humidity_percent (float | None): New humidity value.
            wind_speed_mps (float | None): New wind speed value.
            precipitation_mm (float | None): New precipitation value.
            cloud_cover_percent (float | None): New cloud cover value.
            atmospheric_pressure_hpa (float | None): New atmospheric pressure value.
            weather_condition (str | None): New weather condition description.

        Returns:
            dict: Updated weather state.
        """
        from datetime import datetime, timezone

        if temperature_celsius is not None:
            self.state.temperature_celsius = float(temperature_celsius)
        if humidity_percent is not None:
            self.state.humidity_percent = float(humidity_percent)
        if wind_speed_mps is not None:
            self.state.wind_speed_mps = float(wind_speed_mps)
        if precipitation_mm is not None:
            self.state.precipitation_mm = float(precipitation_mm)
        if cloud_cover_percent is not None:
            self.state.cloud_cover_percent = float(cloud_cover_percent)
        if atmospheric_pressure_hpa is not None:
            self.state.atmospheric_pressure_hpa = float(atmospheric_pressure_hpa)
        if weather_condition is not None:
            self.state.weather_condition = str(weather_condition)

        self.state.last_update = datetime.now(timezone.utc)

        return self.get_current_weather()

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_weather_alert(self, alert_type: str, severity: str, message: str, duration_hours: int = 24):
        """
        Add a weather alert/warning.

        Args:
            alert_type (str): Type of alert (e.g., "storm", "frost", "heat", "wind").
            severity (str): Severity level (e.g., "low", "medium", "high", "critical").
            message (str): Alert message description.
            duration_hours (int): How many hours the alert should remain active.

        Returns:
            dict: The created alert entry.
        """
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        alert = {
            "alert_id": len(self.state.weather_alerts) + 1,
            "type": str(alert_type),
            "severity": str(severity),
            "message": str(message),
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=int(duration_hours))).isoformat(),
        }

        self.state.weather_alerts.append(alert)
        return alert

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_weather_alerts(self):
        """
        Get all active weather alerts.

        Returns:
            list[dict]: List of active weather alerts.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Filter out expired alerts
        active_alerts = []
        for alert in self.state.weather_alerts:
            try:
                expires_at = datetime.fromisoformat(alert["expires_at"])
                if expires_at > now:
                    active_alerts.append(alert)
            except Exception:
                # Keep alerts with invalid expiration dates
                active_alerts.append(alert)

        # Update the state to only keep active alerts
        self.state.weather_alerts = active_alerts

        return active_alerts

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def clear_weather_alerts(self):
        """
        Clear all weather alerts.

        Returns:
            str: Confirmation message.
        """
        count = len(self.state.weather_alerts)
        self.state.weather_alerts = []
        return f"Cleared {count} weather alert(s)."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_agricultural_recommendations(self):
        """
        Get agricultural recommendations based on current weather conditions.

        Returns:
            dict: Recommendations for farming operations.
        """
        recommendations = {
            "irrigation": "normal",
            "pesticide_application": "suitable",
            "planting": "suitable",
            "harvesting": "suitable",
            "notes": []
        }

        # Check temperature
        if self.state.temperature_celsius < 5:
            recommendations["planting"] = "not recommended"
            recommendations["notes"].append("Temperature too low for planting.")
        elif self.state.temperature_celsius > 35:
            recommendations["irrigation"] = "increased"
            recommendations["notes"].append("High temperature - increase irrigation.")

        # Check wind speed
        if self.state.wind_speed_mps > 8:
            recommendations["pesticide_application"] = "not suitable"
            recommendations["notes"].append("Wind speed too high for pesticide application.")

        # Check precipitation
        if self.state.precipitation_mm > 5:
            recommendations["irrigation"] = "not needed"
            recommendations["pesticide_application"] = "not suitable"
            recommendations["harvesting"] = "postpone"
            recommendations["notes"].append("Rainfall detected - postpone outdoor operations.")

        # Check humidity
        if self.state.humidity_percent > 85:
            recommendations["notes"].append("High humidity - monitor for fungal diseases.")
        elif self.state.humidity_percent < 30:
            recommendations["irrigation"] = "increased"
            recommendations["notes"].append("Low humidity - increase irrigation frequency.")

        return recommendations


class Land:
    """Land（土地图）

    中文: 表示耕地的二维网格，包含名称、世界坐标原点(origin)、宽高与格子矩阵。
    English: Represents a farmland as a 2D grid with a *name*, a world-space
    origin (top-left), width/height, and a 2D matrix of GridCell objects.

    Attributes:
      - name (str): Land identifier (e.g., 'A1').
      - origin (tuple[int,int]): World-grid origin (x0, y0) of the land's (0,0) cell.
      - width, height (int): Grid dimensions.
      - grid (list[list[GridCell]]): 2D array of GridCell.
      - default_species (str | None): Optional default crop species for this land.
    """

    def __init__(self, name: str, width: int, height: int, origin=(0, 0)):
        self.name = str(name)
        self.origin = (int(origin[0]), int(origin[1]))
        self.width = int(width)
        self.height = int(height)
        self.water_depth = 0.0
        self.MDA = 0.52
        self.default_species = None
        self.grid = [[GridCell(x, y, land_name=self.name, origin=self.origin)
                      for y in range(self.height)] for x in range(self.width)]

    def set_default_species(self, species: str) -> None:
        """Set the default crop species for this land."""
        self.default_species = str(species)

    def plant_at(self, x: int, y: int, species: str | None = None, planting_date=None) -> bool:
        """Plant a crop at local cell (x, y). Returns True if planted.

        If *species* is None, use ``self.default_species`` if available.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        cell = self.grid[x][y]
        if cell.plant is not None:
            return False
        if species is None:
            species = self.default_species or 'soybean'
        if planting_date is None:
            from datetime import datetime, timezone
            planting_date = datetime.now(timezone.utc)
        cell.plant = Plant(species=species, planting_date=planting_date)
        return True

    def clear_cell(self, x: int, y: int) -> bool:
        """Clear the plant at local cell (x, y). Returns True if cleared."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        cell = self.grid[x][y]
        if cell.plant is None:
            return False
        cell.plant = None
        return True

    def world_position(self, x: int, y: int) -> tuple[int, int]:
        """Get world-grid coordinates for local cell (x, y)."""
        return (self.origin[0] + int(x), self.origin[1] + int(y))


class GridCell:
    """GridCell（网格单元）

    中文: 单个网格单元，保存所属地块名、局部/世界坐标、植物对象、土壤湿度和养分水平。
    English: Single grid cell storing the owning land name, local/world positions,
    an optional Plant, soil moisture and nutrient levels.

    Attributes:
      - land_name: Name/id of the owning land.
      - position: Local (x, y) coordinate inside the land.
      - world_position: Global/world (X, Y) coordinate derived from land origin.
      - plant: Plant or None.
      - soil_moisture: float in [0, 1].
      - nutrient_level: dict of nutrients (nitrogen, phosphorus, potassium).
    """

    def __init__(self, x, y, land_name=None, origin=(0, 0)):
        self.land_name = land_name
        self.position = (x, y)
        self.world_position = (origin[0] + x, origin[1] + y)
        self.plant = None
        self.soil_moisture = 0.6
        self.nutrient_level = {'nitrogen': 0.8, 'phosphorus': 0.6, 'potassium': 0.7}


class Plant:
    """Plant（植物）

    中文: 表示一株植物的基本生长状态与生长函数。
    English: Represents a plant with basic growth state and a grow method.

    Attributes:
      - species: 作物种类
      - planting_date: 种植时间
      - age_days: 成长天数
      - height_cm: 高度（厘米）
      - health: 健康系数（0-1）
      - water_demand: 单位时间需水量的简化表示

    Methods:
      - grow(time_delta_seconds, moisture, nutrients): 基于湿度和养分增加高度 / increment height based on moisture and nutrients
    """

    def __init__(self, species, planting_date):
        self.species = species
        self.planting_date = planting_date
        self.age_days = 0
        self.height_cm = 1.0
        self.health = 1.0
        self.water_demand = 0.01

    def grow(self, time_delta_seconds, moisture, nutrients):
        self.age_days += time_delta_seconds / (24 * 3600)
        moisture_factor = min(1.0, moisture / 0.7)
        nutrient_factor = min(1.0, nutrients.get('nitrogen', 0.0) / 0.8)
        base_growth_rate = 0.0001
        height_increase = base_growth_rate * time_delta_seconds * moisture_factor * nutrient_factor * self.health
        self.height_cm += height_increase


class Drone(COREApp[DroneState]):
    """AerialDrone / 无人机 (空中无人机)

    中文: 表示空中无人机，带有位置、电量、农药罐和相机状态，可飞行和喷洒农药。
    English: Represents an aerial drone with 3D position, battery, pesticide tank and camera; supports flight and pesticide application.

    Attributes:
      - position: (x, y, z) 三维坐标
      - speed_mps: 最大速度（米/秒）
      - consumption_rate: 电耗率（百分比/秒）
      - battery_percentage: 电量百分比
      - pesticide_tank_ml: 罐内农药剩余（毫升）
      - camera_status: 相机开关
      - flight_status: 'landed'/'flying' 等

    Methods (主要方法):
      - takeoff(): 起飞
      - land(): 降落
      - fly_to(x,y,z): 飞往指定坐标
      - inspect_plot(x,y,resolution): 使用相机查看地块
      - apply_pesticide(area, amount_ml): 喷洒农药
    """
    init_state:DroneState = DroneState(position=(15.0, -5.0,0.0), speed_mps=10.0, consumption_rate=0.5,
                                      battery_percentage=100.0, pesticide_tank_ml=0.0,
                                      camera_status=False, flight_status='landed',
                                      device_id=None, pesticide_tank_capacity=None)

    def __init__(self, farm_state=None):
        super().__init__()
        self.farm_state = farm_state


    @property
    def battery(self):
        return self.state.battery_percentage

    @battery.setter
    def battery(self, v):
        try:
            self.state.battery_percentage = float(v)
        except Exception:
            pass

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def takeoff(self):
        """
        Arm rotors and transition the drone to the 'flying' state.

        Returns:
            str: Result message or an error if already flying or battery is too low.
        """
        if self.state.flight_status == 'flying':
            return "Already flying."
        if self.state.battery_percentage <= 1.0:
            return "Error: Insufficient battery to take off."
        self.state.flight_status = 'taking_off'
        self.state.flight_status = 'flying'
        return "Takeoff successful."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def land(self):
        """
        Land the drone and set flight_status to 'landed'.

        Returns:
            str: Result message.
        """
        if self.state.flight_status == 'landed':
            return "Already landed."
        self.state.flight_status = 'landing'
        self.state.flight_status = 'landed'
        return "Landed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def drone_return_to_base(self):
        """
        Move the drone back to the central hub position.

        The central hub charges all devices and replenishes pesticides, etc.; drones without tasks will also wait for tasks in the central hub.
        Returns:
            str: Final position and battery usage, or a partial-move warning.
        """
        hub_pos = self.farm_state.central_hub.state.position if self.farm_state and self.farm_state.central_hub else (0.0, 0.0)
        return self._fly_to(hub_pos[0], hub_pos[1])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def fly_to(self, x, y):
        """
        Fly to a target 3D coordinate, consuming battery proportional to travel time.

        Args:
            x (float): Target X coordinate in meters.
            y (float): Target Y coordinate in meters.

        Returns:
            str: Message including travel time and battery used, or a partial-flight warning.
        """
        return self._fly_to(x, y)

    def _fly_to(self, x, y):
        if self.state.flight_status != 'flying':
            return "Error: Drone not flying."
        target = np.array((float(x), float(y),20.0), dtype=float)
        distance = float(np.linalg.norm(self.state.position - target))
        time_needed_seconds = distance / max(1e-6, self.state.speed_mps)
        energy_cost = time_needed_seconds * self.state.consumption_rate
        if energy_cost <= self.state.battery_percentage:
            self.state.position = target
            self.state.battery_percentage = max(0.0, self.state.battery_percentage - energy_cost)
            return f"Flight successful. Time: {time_needed_seconds:.1f}s, Battery used: {energy_cost:.2f}% (remaining {self.state.battery_percentage:.2f}%)."
        else:
            max_time = self.state.battery_percentage / max(1e-9, self.state.consumption_rate)
            travel_fraction = min(1.0, (max_time * self.state.speed_mps) / max(1e-9, distance)) if distance > 0 else 0.0
            new_pos = self.state.position + (target - self.state.position) * travel_fraction
            self.state.position = new_pos
            used = self.state.battery_percentage
            self.state.battery_percentage = 0.0
            return f"Warning: Insufficient battery. Flew partially to {tuple(self.state.position)}, battery depleted (used {used:.2f}%)."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def inspect_plot(self, x, y, resolution=(640, 480)):
        """
        Capture a simulated observation of a plot center.

        Args:
            x (float): Plot center X coordinate.
            y (float): Plot center Y coordinate.
            resolution (tuple[int, int]): Image resolution as (width, height).

        Returns:
            dict | str: Observation dictionary if the camera is on; otherwise an error string.
        """
        if not self.state.camera_status:
            return "Error: Camera is off."
        obs = {
            'center': (float(x), float(y)),
            'resolution': tuple(resolution),
            'position': tuple(self.state.position),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return obs

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def apply_pesticide(self, area, amount_ml):
        """
        Apply pesticide over an area, consuming fluid from the on-board tank.

        Args:
            area (Any): Identifier or description of the target area.
            amount_ml (float): Milliliters requested to spray.

        Returns:
            str: Result message or error if tank is empty or the amount is invalid.
        """
        try:
            amount = float(amount_ml)
        except (TypeError, ValueError):
            return "Error: amount must be a number."
        if amount <= 0:
            return "Error: amount must be positive."
        if self.state.pesticide_tank_ml <= 0:
            return "Error: pesticide tank empty."
        applied = min(amount, self.state.pesticide_tank_ml)
        self.state.pesticide_tank_ml -= applied
        return f"Applied {applied:.2f} ml pesticide to {area}. Remaining tank: {self.state.pesticide_tank_ml:.2f} ml."


@dataclass
class GroundRoverState:
    position: tuple[float, float] = (0.0, 0.0)
    battery_percentage: float = 100.0
    water_tank_liters: float = 10.0
    fertilizer_bin_kg: float = 50.0
    tool_attachment_status: dict = field(default_factory=dict)
    seed_bin: dict[str, int] = field(default_factory=dict)
    device_id: str | None = None
    planter_config: dict = field(default_factory=lambda: {
        "row_spacing_cm": None, "depth_cm": None, "in_row_spacing_cm": None
    })


class GroundRover(COREApp[GroundRoverState]):
    """GroundRover / 地面机器人

    中文: 表示地面机器人，能移动、浇水、施肥、种植与收割，维护自身的电量和物料箱状态。
    English: Represents a ground rover capable of moving, watering, fertilizing, planting and harvesting while tracking battery and material bins.

    Attributes:
      - position: (x, y)
      - battery_percentage: 电量百分比
      - water_tank_liters: 水箱容量（升）
      - fertilizer_bin_kg: 肥料箱（千克）
      - tool_attachment_status: 工具挂载状态字典
      - seed_bin: 种子箱（按种类计数）

    Methods (主要方法):
      - move_to(x, y): 移动到目标坐标
      - water_plant(plant_loc, liters): 为指定植物浇水
      - apply_fertilizer(plant_loc, kg): 为指定植物施肥
      - plant_seed(seed_type): 在当前位置种植种子
      - harvest_crop(plant_loc): 收获作物
    """
    init_state: GroundRoverState = GroundRoverState(position=(0.0, 0.0), battery_percentage=100.0,
                                                    water_tank_liters=10.0, fertilizer_bin_kg=5.0,
                                                    tool_attachment_status={}, seed_bin={},
                                                    planter_config={"row_spacing_cm": None, "depth_cm": None,
                                                                    "in_row_spacing_cm": None})

    def __init__(self, device_id, farm_state:HitFarmState=None):
        super().__init__()
        self.state.device_id = device_id
        self.farm_state = farm_state

    def set_planter_config(self, row_spacing_cm: float , depth_cm: float,
                           in_row_spacing_cm: float):
        """
        Set or update the planter configuration parameters.

        Args:
            row_spacing_cm (float): Spacing between rows in centimeters.
            depth_cm (float): Planting depth in centimeters.
            in_row_spacing_cm (float): Spacing between plants within a row in centimeters
        """
        if row_spacing_cm is not None:
            self.state.planter_config["row_spacing_cm"] = float(row_spacing_cm)
        if depth_cm is not None:
            self.state.planter_config["depth_cm"] = float(depth_cm)
        if in_row_spacing_cm is not None:
            self.state.planter_config["in_row_spacing_cm"] = float(in_row_spacing_cm)
        return dict(self.state.planter_config)

    def _consume_battery_for_distance(self, distance_m):
        cost = distance_m * 0.02
        cost = float(cost)
        if cost > self.state.battery_percentage:
            return False, cost
        self.state.battery_percentage = max(0.0, self.state.battery_percentage - cost)
        return True, cost

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def return_to_base(self):
        """
        Move the rover back to the central hub position.

        The central hub charges all devices and replenishes seeds, fertilizers, pesticides, etc.; rovers without tasks will also wait for tasks in the central hub.
        Returns:
            str: Final position and battery usage, or a partial-move warning.
        """
        hub_pos = self.farm_state.central_hub.state.position if self.farm_state and self.farm_state.central_hub else (0.0, 0.0)
        return self._move_to(hub_pos[0], hub_pos[1])

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def move_to(self, x, y):
        """
        Move the rover to a target (x, y) coordinate, consuming battery.

        Args:
           x (float): Target X coordinate.
           y (float): Target Y coordinate.

        Returns:
           str: Final position and battery usage, or a partial-move warning.
        """
        self._move_to(x, y)

    def _move_to(self, x, y):
        try:
            target = np.array((float(x), float(y)), dtype=float)
        except Exception:
            return "Error: invalid target coordinates."
        distance = float(np.linalg.norm(self.state.position - target))
        ok, cost = self._consume_battery_for_distance(distance)
        if not ok:
            if distance <= 0:
                return "Error: Already at target or cannot move."
            fraction = self.state.battery_percentage / max(1e-9, cost)
            new_pos = self.state.position + (target - self.state.position) * fraction
            # TODO
            self.state.position = new_pos
            used = self.state.battery_percentage
            self.state.battery_percentage = 0.0
            return f"Warning: Insufficient battery. Moved partially to {tuple(self.state.position)}. Battery depleted (used {used:.2f}%)."
        else:
            # TODO
            self.state.position = target
            return f"Moved to {tuple(self.state.position)}. Battery used: {cost:.2f}%. Remaining: {self.state.battery_percentage:.2f}%"

    def _resolve_cell(self, plant_loc):
        if plant_loc is None:
            return None, None



    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def apply_fertilizer(self, kg):
        """
        Apply fertilizer to a plant/location and update local nutrient levels.

        Args:
            kg (float): Kilograms requested to apply.

        Returns:
            str: Result message with applied mass and remaining bin.
        """
        try:
            amount = float(kg)
        except Exception:
            return "Error: amount must be a number."
        if amount <= 0:
            return "Error: amount must be positive."
        if self.state.fertilizer_bin_kg <= 0:
            return "Error: fertilizer bin empty."

        applied = min(amount, self.state.fertilizer_bin_kg)
        self.state.fertilizer_bin_kg -= applied
        return f"Applied {applied:.3f} kg fertilizer to plant . Remaining bin: {self.state.fertilizer_bin_kg:.3f} kg."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def plant_seed(self, seed_type ,row_spacing_cm: float = 2.0, depth_cm: float = 2.0,
                           in_row_spacing_cm: float = 2.0):
        """
        Plant a seed of the given type at the rover's current grid cell.

        Args:
            seed_type (str): Seed species key (must exist in `seed_bin`).
            row_spacing_cm (float): Spacing between rows in centimeters. defaults to 2.0 cm.
            depth_cm (float): Planting depth in centimeters.defaults to 2.0 cm.
            in_row_spacing_cm (float): Spacing between plants within a row in centimeters defaults to 2.0 cm.
        Returns:
            str: Result message or error if bin is empty, env is missing, or cell is occupied.
        """
        self.set_planter_config(row_spacing_cm=row_spacing_cm, depth_cm=depth_cm,in_row_spacing_cm=in_row_spacing_cm)
        available = int(self.state.seed_bin.get(seed_type, 0))
        if available <= 0:
            return f"Error: no {seed_type} seeds in bin."

        x, y = int(round(float(self.state.position[0]))), int(round(float(self.state.position[1])))

        land = self.farm_state.get_land_at(self.state.position[0] , self.state.position[1])
        if land is None:
            return "Error: no land at current position."

        planted_count = 0
        for yy in range(y-land.origin[1], land.height):
            if available <= 0:
                break
            cell = land.grid[x-land.origin[0]][yy]
            if cell.plant is not None:
                continue  # Skip occupied cells
            new_plant = Plant(species=seed_type, planting_date=self.farm_state.time)
            cell.plant = new_plant
            available -= 1
            planted_count += 1

        self.state.seed_bin[seed_type] = available
        return f"Planted {planted_count} '{seed_type}' seeds along the row. Remaining {seed_type} seeds: {self.state.seed_bin[seed_type]}"

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def harvest_crop(self, plant_loc):
        """
        Harvest a crop at a specific location and estimate yield.

        Args:
            plant_loc (tuple | GridCell | Plant): Plant or grid reference to harvest.

        Returns:
            str: Result message with estimated yield.
        """
        cell, plant = self._resolve_cell(plant_loc)
        if cell is None or plant is None:
            return "Error: target plant not found or env not provided."
        estimated_yield = plant.height_cm * plant.health * 0.01
        cell.plant = None
        return f"Harvested plant at {cell.position}. Estimated yield: {estimated_yield:.3f} kg."


class IrrigationSystem(COREApp[IrrigationSystemState]):
    """IrrigationSystem (灌溉系统)

    中文: 管理分区阀门状态并提供打开/关闭与自动超时关闭的接口。
    English: Manages zone valve states and provides open/close and auto-close-on-timeout functionality.

    Attributes:
      - zone_valve_status: {zone_id: {'open': bool, 'open_until': datetime or None}}
      - water_pressure_psi: 水压（psi）
      - master_valve_status: 主阀门开关
    """
    init_state : IrrigationSystemState = IrrigationSystemState(water_pressure_psi=40.0, master_valve_status=False,
                                                              zone_valve_status={})

    def __init__(self, farm_state:HitFarmState=None):
        super().__init__()
        self.farm_state = farm_state

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def open_valve(self, land_name, duration_minutes=45):
        """
        Open a zone valve, optionally scheduling an automatic close time.

        Args:
            land_name (str): Land identifier, e.g., A1
            duration_minutes (float ): If provided, set an 'open_until' timestamp.defaults to 45 minutes from now.

        Returns:
            str: Result message; also ensures the master valve is open.
        """
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        entry = self.state.zone_valve_status.get(land_name, {})
        entry['open'] = True
        if duration_minutes is not None:
            try:
                mins = float(duration_minutes)
                entry['open_until'] = now + timedelta(minutes=mins)
            except Exception:
                entry['open_until'] = None
        else:
            entry['open_until'] = None
        self.state.zone_valve_status[land_name] = entry
        # 确保主阀门打开以允许分区供水
        if not self.state.master_valve_status:
            self.state.master_valve_status = True

        self.farm_state.lands.get(land_name).water_depth = 3.0
        self.farm_state.lands.get(land_name).MDA = 0.2

        return f"Valve {land_name} opened. Master valve: {self.state.master_valve_status}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def close_valve(self, land_name):
        """
        Close the specified land valve and clear any auto-close timestamp.

        Args:
            land_name (str): land identifier eg A1.

        Returns:
            str: Result message.
        """
        entry = self.state.zone_valve_status.get(land_name)
        if not entry:
            # 如果没有记录，创建一个关闭状态
            self.state.zone_valve_status[land_name] = {'open': False, 'open_until': None}
            return f"Valve {land_name} closed (was not registered)."
        entry['open'] = False
        entry['open_until'] = None
        self.state.zone_valve_status[land_name] = entry
        return f"Valve {land_name} closed."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def check_and_auto_close(self):
        """
        Check all valves with an 'open_until' and close those whose timeout has elapsed.

        Returns:
            list[str | int]: Zone IDs that were auto-closed during this check.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        changed = []
        for zid, entry in list(self.state.zone_valve_status.items()):
            if entry.get('open') and entry.get('open_until'):
                if now >= entry['open_until']:
                    entry['open'] = False
                    entry['open_until'] = None
                    self.state.zone_valve_status[zid] = entry
                    changed.append(zid)
        return changed


class SensorNetwork(COREApp[SensorNetworkState]):
    """SensorNetwork (传感器网络)

    中文: 维护传感器缓存数据并提供读取接口（土壤湿度、温度、养分、植物状态等），优先使用环境中的实时值。
    English: Maintains cached sensor readings and provides read interfaces (soil moisture, temperature, nutrients, plant status), preferring live env values when available.

    Attributes:
      - last_reading_timestamp: 最近一次读取时间戳
      - cached_data: 按 sensor_id 存储的数据字典
      - env: 可选的环境引用，用于直接读取 Land/ GridCell 数据

    主要方法:
      - update_cache(sensor_id, data_dict): 更新缓存
      - get_soil_moisture(x, y): 获取土壤湿度
      - get_temperature(x, y): 获取温度
      - get_nutrient_level(x, y): 获取养分
      - get_plant_status(x, y): 查询植物状态
      - get_data(sensor_ids): 带宽受限的批量读取
    """
    init_state : SensorNetworkState=SensorNetworkState(last_reading_timestamp=None,cached_data={})

    def __init__(self, farm_state :HitFarmState):
        super().__init__()
        self.farm_state = farm_state
        self.zone_depths = {
            "B1": 2.0,
        }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def update_cache(self, sensor_id, data_dict):
        """
        Update cached readings for a sensor and refresh the last read timestamp.

        Args:
            sensor_id (str): Sensor identifier.
            data_dict (dict): Arbitrary sensor payload to cache.

        Returns:
            bool: True when the cache was updated successfully.
        """
        from datetime import datetime, timezone
        self.state.cached_data[sensor_id] = data_dict
        self.state.last_reading_timestamp = datetime.now(timezone.utc)
        return True

    def _cell_at(self, x, y):
        """尝试从 env 中获取对应的 GridCell（x,y 期望为整数或可转为整数）。"""
        land = self.farm_state.get_land_at(x, y)

        try:
            xi = int(round(float(x)))
            yi = int(round(float(y)))
        except Exception:
            return None
        if land is not None:
            return land.grid[xi-land.origin[0]][yi-land.origin[1]]
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_water_depth(self,land_name:str):
        """
        Return water depth at the specified irrigation land.

        Args:
            land_name (str): land identifier.

        Returns:
            float | None: Water depth in cm, or None if unavailable.
        """

        return self.farm_state.lands.get(land_name).water_depth

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_land_MDA(self,land_name:str):
        """
        Return land MDA at the specified land.

        Args:
            land_name (str): land identifier.

        Returns:
            float | None: MDA value, or None if unavailable.
        """

        return self.farm_state.lands.get(land_name).MDA



    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_soil_moisture(self, x, y):
        """
        Return soil moisture at (x, y), preferring live env data over cached values.

        Args:
            x (int | float): X coordinate.
            y (int | float): Y coordinate.

        Returns:
            float | None: Moisture in [0, 1], or None if unavailable.
        """
        cell = self._cell_at(x, y)
        if cell is not None:
            from datetime import datetime, timezone
            self.last_reading_timestamp = datetime.now(timezone.utc)
            return float(cell.soil_moisture)
        # 回退：在 cached_data 中查找最近的 moisture 值
        for sid, data in self.state.cached_data.items():
            if 'moisture' in data:
                return float(data['moisture'])
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_temperature(self, x, y):
        """
        Return temperature at (x, y), preferring live env data over cached values.

        Args:
            x (int | float): X coordinate.
            y (int | float): Y coordinate.

        Returns:
            float | None: Temperature estimate in °C, or None if unavailable.
        """
        cell = self._cell_at(x, y)
        if cell is not None:
            from datetime import datetime, timezone
            self.last_reading_timestamp = datetime.now(timezone.utc)
            # 简化：没有细化温度模型，返回基于土壤湿度的估算
            return 20.0 + (0.5 - cell.soil_moisture) * 10.0
        for sid, data in self.state.cached_data.items():
            if 'temperature' in data:
                return float(data['temperature'])
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_nutrient_level(self, x, y):
        """
        Return soil nutrient levels at (x, y), preferring live env data.

        Args:
            x (int | float): X coordinate.
            y (int | float): Y coordinate.

        Returns:
            dict | None: Nutrient mapping (e.g., {'nitrogen': ...}), or None if unavailable.
        """
        cell = self._cell_at(x, y)
        if cell is not None:
            from datetime import datetime, timezone
            self.last_reading_timestamp = datetime.now(timezone.utc)
            return dict(cell.nutrient_level)
        # 回退：尝试从缓存数据中读取
        for sid, data in self.state.cached_data.items():
            if 'nutrient_level' in data:
                return dict(data['nutrient_level'])
        return None

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_plant_status(self, x, y):
        """
        Query whether a plant exists at (x, y) and return simple status flags.

        Args:
            x (int | float): X coordinate.
            y (int | float): Y coordinate.

        Returns:
            dict: Status with keys {position, emerged, mature, height_cm}.
        """
        cell = self._cell_at(x, y)
        status = {"position": None, "emerged": False, "mature": False, "height_cm": 0.0}
        if cell is None:
            return status
        status["position"] = cell.position
        if cell.plant is not None:
            status["emerged"] = True
            try:
                status["height_cm"] = float(getattr(cell.plant, "height_cm", 0.0))
                status["mature"] = status["height_cm"] >= 150.0
            except Exception:
                pass
        return status

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_data(self, sensor_ids: list[str]) -> dict[str, dict]:
        """
        Fetch multiple sensor payloads with a bandwidth limit of at most 10 IDs.

        Args:
            sensor_ids (list[str]): Sensor IDs to fetch (max 10).

        Returns:
            dict: Mapping of sensor_id to cached payload; returns {'error': str} on invalid input.
        """
        try:
            if len(sensor_ids) > 10:
                return {"error": "Too many sensors requested; max 10 per minute."}
        except Exception:
            return {"error": "sensor_ids must be a list of strings"}
        result: dict[str, dict] = {}
        for sid in sensor_ids:
            data = self.state.cached_data.get(sid)
            if data is not None:
                result[sid] = dict(data)
        return result


class HitFarmState(App):
    """HitFarmState（仿真环境-多地块）

    中文: 维护五个地块（A1–A5）、中央基地 CentralHub、无人机/地面机器人/灌溉/传感网络，并提供时间推进与状态导出。
    English: Maintains five lands (A1–A5), a single CentralHub, a drone, a ground rover,
    irrigation and sensor subsystems, with time management and a step() API.

    主要方法:
      - step(agent_action): 执行 agent_action 并推进仿真一步
      - _update_environment(time_delta_seconds): 植物生长、土壤湿度衰减（遍历所有地块）
      - _execute_action(agent_action): 将动作分派到实体的方法上
      - get_state(): 返回当前仿真状态（含多地块汇总与 CentralHub 位置）
    """

    def __init__(self, land_size=(100, 100), initial_conditions=None):
        super().__init__("HitFarmState")
        if initial_conditions is None:
            initial_conditions = {}

        # ---- Five lands with names, sizes, and world origins (reasonable defaults) ----
        self.land_layout = {
            'A1': {'size': (30, 30), 'origin': (0, 0)},
            'A2': {'size': (30, 25), 'origin': (35, 0)},
            'A3': {'size': (24, 24), 'origin': (70, 0)},
            'A4': {'size': (40, 20), 'origin': (0, 32)},
            'A5': {'size': (30, 30), 'origin': (42, 32)},
            # Additional blocks to support scenarios B/C/D
            'B1': {'size': (28, 28), 'origin': (75, 32)},
            'B2': {'size': (28, 24), 'origin': (105, 32)},
            'C1': {'size': (30, 26), 'origin': (75, 62)},
            'D1': {'size': (30, 26), 'origin': (0, 62)},
            'D2': {'size': (30, 26), 'origin': (35, 62)},
        }
        self.lands: dict[str, Land] = {
            lid: Land(name=lid, width=meta['size'][0], height=meta['size'][1], origin=meta['origin'])
            for lid, meta in self.land_layout.items()
        }

        # ---- Subsystems (registered later; allow multiples) ----
        self.drones: list[Drone] = []
        self.rovers: list[GroundRover] = []
        self.central_hubs: list[CentralHub] = []
        self.irrigation_systems: list[IrrigationSystem] = []
        self.sensor_networks: list[SensorNetwork] = []

        # Default hub position when no hub registered yet
        self.hub_position = (15.0, -5.0, 0.0)

        # Timekeeping
        self.time = datetime(2024, 6, 1, 6, 0, 0, tzinfo=timezone.utc)
        self.time_step = timedelta(minutes=1)

        # No implicit coupling/registration here; handled by register_* methods

    # ---- Registration API (supports multiple instances) ----
    def register_drone(self, drone: Drone) -> None:
        try:
            drone.farm_state = self
        except Exception:
            pass
        self.drones.append(drone)

    def register_rover(self, rover: GroundRover) -> None:
        try:
            rover.farm_state = self
        except Exception:
            pass
        self.rovers.append(rover)


    def register_central_hub(self, hub: CentralHub) -> None:
        self.central_hubs.append(hub)
        try:
            self.hub_position = tuple(hub.state.position)
            hub.farm_state = self
        except Exception:
            pass

    def register_irrigation_system(self, irrigation: IrrigationSystem) -> None:
        self.irrigation_systems.append(irrigation)

    def register_sensor_network(self, sensors: SensorNetwork) -> None:
        try:
            sensors.env = self
        except Exception:
            pass
        self.sensor_networks.append(sensors)

    # ---- Backward-compat convenience properties (first instance or None) ----
    @property
    def drone(self):
        return self.drones[0] if self.drones else None

    @property
    def rover(self):
        return self.rovers[0] if self.rovers else None

    @property
    def central_hub(self):
        return self.central_hubs[0] if self.central_hubs else None

    @property
    def irrigation_system(self):
        return self.irrigation_systems[0] if self.irrigation_systems else None

    def get_rover(self,device_id:str) -> GroundRover | None:
        for r in self.rovers:
            if r.state.device_id == device_id:
                return r
        return self.rovers[0]

    def get_drone(self, device_id: str) -> Drone |None:
        for d in self.drones:
            if d.state.device_id == device_id:
                return d
        return self.drones[0]

    @property
    def sensor_network(self):
        return self.sensor_networks[0] if self.sensor_networks else None

        # ---- Single-crop policy per land; plant a few GridCells so each land has Plants ----
        per_land_species = {
            'A1': 'soybean', 'A2': 'corn', 'A3': 'wheat', 'A4': 'corn', 'A5': 'soybean',
            'B1': 'rice', 'B2': 'rice', 'C1': 'soybean', 'D1': 'wheat', 'D2': 'wheat'
        }
        for lid, land in self.lands.items():
            land.set_default_species(per_land_species.get(lid, 'soybean'))
            w, h = land.width, land.height
            centers = [
                (w // 2, h // 2),
                (max(0, w // 2 - 2), max(0, h // 2 - 2)),
                (min(w - 1, w // 2 + 2), min(h - 1, h // 2 + 2)),
            ]
            for (cx, cy) in centers:
                land.plant_at(cx, cy, planting_date=self.time)

    def step(self, agent_action):
        self._execute_action(agent_action)
        self._update_environment(self.time_step.total_seconds())
        self.time += self.time_step
        return self.get_state(), self._calculate_reward(), self._check_if_done(), {}

    def _update_environment(self, time_delta_seconds):
        for land in self.lands.values():
            for x in range(land.width):
                for y in range(land.height):
                    cell = land.grid[x][y]
                    if cell.plant:
                        cell.plant.grow(time_delta_seconds, cell.soil_moisture, cell.nutrient_level)
                    cell.soil_moisture *= 0.999

    def _execute_action(self, agent_action):
        if not agent_action:
            return None
        try:
            if isinstance(agent_action, (list, tuple)) and len(agent_action) >= 2:
                entity_name, method_name = agent_action[0], agent_action[1]
                params = agent_action[2] if len(agent_action) > 2 and isinstance(agent_action[2], dict) else {}
            elif isinstance(agent_action, dict):
                entity_name = agent_action.get('entity')
                method_name = agent_action.get('action')
                params = agent_action.get('params', {}) or {}
            else:
                return None
            if not isinstance(entity_name, str) or not isinstance(method_name, str):
                return None
            entity = getattr(self, entity_name, None)
            if entity is None:
                return None
            func = getattr(entity, method_name, None)
            if not callable(func):
                return None
            try:
                return func(**params)
            except TypeError:
                if params:
                    return func(params)
                return func()
        except Exception:
            return None

    def _calculate_reward(self):
        return 0.0

    def _check_if_done(self):
        return False

    def get_state(self):
        lands_state = {}
        for lid, land in self.lands.items():
            plant_count = 0
            for x in range(land.width):
                for y in range(land.height):
                    if land.grid[x][y].plant is not None:
                        plant_count += 1
            lands_state[lid] = {
                'name': land.name,
                'size': (land.width, land.height),
                'origin': land.origin,
                'plant_count': plant_count,
            }
        return {
            'time': self.time.isoformat(),
            'land_shape': (self.lands['A1'].width, self.lands['A1'].height),  # backward-compatible
            'lands': lands_state,
            'central_hub': (
                {
                    'position': tuple(self.hub_position),
                    'power_grid_status': self.central_hub.state.power_grid_status,
                    'water_supply_liters': self.central_hub.state.water_supply_liters,
                    'pesticide_supply_ml': self.central_hub.state.pesticide_supply_ml,
                    'fertilizer_supply_kg': self.central_hub.state.fertilizer_supply_kg
                } if self.central_hub is not None else None
            )
        }

    def layout_diagram(self) -> str:
        """Return a simple ASCII schematic of land sizes and origins plus hub position."""
        lines = []
        lines.append("Farm Layout (current configuration):")
        for lid in sorted(self.lands.keys()):
            land = self.lands[lid]
            lines.append(f"  - {land.name}: size={land.width}x{land.height} origin={land.origin}")
        lines.append(f"CentralHub: position={tuple(self.hub_position)}")
        lines.append("")
        lines.append("Schematic (not to scale):")
        # Group lands roughly by their Y origin for a two-row layout
        origins = {lid: self.lands[lid].origin for lid in self.lands}
        min_y = min(o[1] for o in origins.values())
        row1 = [lid for lid, o in origins.items() if o[1] <= min_y + 1]
        row2 = [lid for lid in self.lands if lid not in row1]

        def box(land: Land):
            return f"[{land.name} {land.width}x{land.height} @O{land.origin}]"

        if row1:
            lines.append("  ".join(box(self.lands[lid]) for lid in sorted(row1)))
        if row2:
            lines.append("  ".join(box(self.lands[lid]) for lid in sorted(row2)))
        return "\n".join(lines)

    # @type_check
    # @app_tool()
    # @data_tool()
    # @event_registered(operation_type=OperationType.READ)
    # def get_land_coordinates(self, land_name: str) -> dict:
    #     """
    #     Get world‑grid coordinates and bounds for a land by name.
    #     Args:
    #         land_name (str): Land identifier, e.g., 'A1' ~ 'A5'.
    #
    #     Returns:
    #         dict: A mapping with keys:
    #             - name: land id
    #             - origin: (x0, y0) world-grid origin (top-left cell)
    #             - size: (width, height)
    #             - bbox: {'min': (x_min, y_min), 'max': (x_max, y_max)} inclusive bounds in world grid
    #             - center: (cx, cy) center cell in world grid (integer)
    #             If the land is not found, returns {'error': str}.
    #     """
    #     lid = str(land_name)
    #     land = self.lands.get(lid)
    #     if land is None:
    #         return {"error": f"Land {land_name} not found"}
    #     x0, y0 = land.origin
    #     w, h = land.width, land.height
    #     bbox_min = (x0, y0)
    #     bbox_max = (x0 + w - 1, y0 + h - 1)
    #     center = (x0 + w // 2, y0 + h // 2)
    #     return {
    #         'name': land.name,
    #         'origin': (x0, y0),
    #         'size': (w, h),
    #         'bbox': {'min': bbox_min, 'max': bbox_max},
    #         'center': center,
    #     }

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_coordinates(self, land_name: str) -> str | tuple[int, int]:
        """
        Get world‑grid coordinates for a land by name.
        Args:
            land_name (str): Land identifier, e.g., A1

        Returns:
            tuple: world‑grid coordinate (x0, y0)
            str:   If the land is not found, returns str.
        """
        lid = str(land_name)
        land = self.lands.get(lid)
        if land is None:
            return f"Land {land_name} not found"
        return land.origin

    def get_land_at(self, x: float, y: float) -> Land | None:
        """
        Get the land that contains the given world coordinates (x, y).

        Args:
            x (int): World X coordinate.
            y (int): World Y coordinate.

        Returns:
            Land | None: The land object if found, otherwise None.
        """
        for land in self.lands.values():
            ox, oy = land.origin
            if ox <= x < ox + land.width and oy <= y < oy + land.height:
                return land
        return None
