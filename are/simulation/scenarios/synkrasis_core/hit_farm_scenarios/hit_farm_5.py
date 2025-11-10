from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, Drone, CentralHub, WeatherApp
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.types import EventRegisterer


class CustomScenario(COREScenario):
    """
    Scenario 5: Apply pesticides 100ml to land B2, and understand the wind speed by the current weather.
    If the wind speed is > 5 m/s, then suspend spraying on B2 and land the equipment in place.
    """

    prompt: str | None = (
        "Apply pesticides 100ml to land B2, and understand the wind speed by the current weather. "
        "If the wind speed is > 5 m/s, then suspend spraying on B2 and land the equipment in place."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        drone = Drone(farm_state=state)
        hub = CentralHub(farm_state=state)
        weather = WeatherApp()

        state.register_drone(drone)
        state.register_central_hub(hub)

        # Set wind speed > 5 m/s (too windy for spraying)
        weather.update_weather(wind_speed_mps=6.5)

        self.apps = [agui, state, drone, hub, weather]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        drone = self.get_typed_app(Drone)
        hub = self.get_typed_app(CentralHub)
        weather = self.get_typed_app(WeatherApp)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get current weather (including wind speed)
            o_weather = weather.get_current_weather().oracle().depends_on(e0, delay_seconds=1)

            # Get B2 coordinates
            info = state.get_coordinates(land_name="B2").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["B2"].origin

            # Refill pesticide
            o_refill = hub.refill_pesticide(device_id=drone.state.device_id, amount_ml=100.0).oracle().depends_on(
                e0, delay_seconds=1)

            # Takeoff
            o_takeoff = drone.takeoff().oracle().depends_on(o_refill, delay_seconds=1)

            # Fly to B2
            o_fly = drone.fly_to(x=x, y=y).oracle().depends_on([info, o_takeoff], delay_seconds=1)

            # Wind speed > 5 m/s, suspend spraying and land in place
            o_land = drone.land().oracle().depends_on([o_weather,o_fly], delay_seconds=1)

        self.events = [e0, o_weather, info, o_refill, o_takeoff, o_fly, o_land]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate

    run_and_validate(CustomScenario())
