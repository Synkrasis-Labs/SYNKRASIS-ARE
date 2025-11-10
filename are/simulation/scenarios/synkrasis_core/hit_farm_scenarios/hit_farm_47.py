from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork, WeatherApp
)
from are.simulation.scenarios.core_scenario import COREScenario
from are.simulation.scenarios.utils.registry import register_scenario
from are.simulation.types import EventRegisterer

class CustomScenario(COREScenario):
    """
    scenarios47: A1: Read nitrogen; if < 0.8, apply corrective topdressing with urea at 50 kg/ha;
    If rain is forecast within 2 hours, postpone the task.
    """

    prompt: str | None = (
        "A1: Read nitrogen ; if < 0.8, apply corrective topdressing with urea at 50 kg;  "
        "If rain is forecast within 2 hours, postpone the task"
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        weather = WeatherApp()

        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        # Set nitrogen level below threshold (0.7 < 0.8)
        a1_land = state.lands.get('A1')
        if a1_land:
            for x in range(min(5, a1_land.width)):
                for y in range(min(5, a1_land.height)):
                    cell = a1_land.grid[x][y]
                    cell.nutrient_level['nitrogen'] = 0.7  # Below threshold

        # No rain forecast within 2 hours
        weather.generate_forecast([
            {"time": 1, "precipitation_probability": 5},
            {"time": 2, "precipitation_probability": 10},
            {"time": 3, "precipitation_probability": 60}
        ])

        self.apps = [agui, state, rover, hub, sensors, weather]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)
        weather = self.get_typed_app(WeatherApp)

        with EventRegisterer.capture_mode():
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get A1 coordinates
            info = state.get_coordinates(land_name="A1").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A1"].origin

            # Read nitrogen level
            o_nitrogen = sensors.get_nutrient_level(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # Check weather forecast for next 2 hours
            o_forecast = weather.get_forecast(hours=2).oracle().depends_on(o_nitrogen, delay_seconds=1)

            # If nitrogen < 0.8 and no rain forecast, apply fertilizer
            # Load fertilizer
            o_refill = hub.refill_fertilizer(device_id=rover.state.device_id, amount_kg=50.0).oracle().depends_on(
                o_forecast, delay_seconds=1)

            # Move to A1
            o_move = rover.move_to(x=x, y=y).oracle().depends_on(o_refill, delay_seconds=1)

            # Apply urea fertilizer (50 kg/ha)
            o_apply = rover.apply_fertilizer(kg=50.0).oracle().depends_on(o_move, delay_seconds=2)

            # Return to base
            o_return = rover.return_to_base().oracle().depends_on(o_apply, delay_seconds=1)

        self.events = [e0, info, o_nitrogen, o_forecast, o_refill, o_move, o_apply, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

