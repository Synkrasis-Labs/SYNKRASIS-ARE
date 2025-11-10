from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub, IrrigationSystem, WeatherApp
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    scenarios39: Received a "high severity" heavy rain warning, expected to arrive within 15 minutes.
    Immediately stop all irrigation and order all drones to land safely in place.
    """

    prompt: str | None = (
        "check the weather alterts. If there is a heavy rain warning with high severity, "
        "immediately stop all irrigation and order all drones to land safely in place."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()

        # Register drones in flying state
        drone1 = Drone(farm_state=state)
        drone1.state.device_id = "drone-1"
        drone1.name = "drone-1"
        drone1.state.flight_status = "flying"
        drone1.state.position = (50.0, 50.0, 20.0)

        drone2 = Drone(farm_state=state)
        drone2.state.device_id = "drone-2"
        drone2.name = "drone-2"
        drone2.state.flight_status = "flying"
        drone2.state.position = (80.0, 80.0, 20.0)

        hub = CentralHub(farm_state=state)
        irrigation = IrrigationSystem(farm_state=state)
        weather = WeatherApp()

        state.register_drone(drone1)
        state.register_drone(drone2)
        state.register_central_hub(hub)
        state.register_irrigation_system(irrigation)

        # Set up active irrigation zones
        irrigation.state.zone_valve_status = {
            "A1": {"open": True, "open_until": None},
            "B2": {"open": True, "open_until": None},
            "C1": {"open": True, "open_until": None}
        }
        irrigation.state.master_valve_status = True

        # Add weather alert
        weather.add_weather_alert(
            alert_type="heavy_rain",
            severity="high",
            message="High severity heavy rain warning - expected arrival in 15 minutes.",
            duration_hours=2
        )

        self.apps = [agui, state, drone1, drone2, hub, irrigation, weather]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        irrigation = self.get_typed_app(IrrigationSystem)
        weather = self.get_typed_app(WeatherApp)
        drone_1 = self.get_typed_app(Drone, "drone-1")
        drone_2 = self.get_typed_app(Drone, "drone-2")
        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get weather alerts to confirm emergency
            o_weather = weather.get_weather_alerts().oracle().depends_on(e0, delay_seconds=0)

            # Emergency: Close all irrigation valves
            o_close_irrigation = irrigation.close_all_valves().oracle().depends_on(o_weather, delay_seconds=0)
            o_land_drone1 = drone_1.land().oracle().depends_on(o_weather, delay_seconds=0)
            o_land_drone2 = drone_2.land().oracle().depends_on(o_weather, delay_seconds=0)

        self.events = [e0, o_weather, o_close_irrigation, o_land_drone1, o_land_drone2]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
