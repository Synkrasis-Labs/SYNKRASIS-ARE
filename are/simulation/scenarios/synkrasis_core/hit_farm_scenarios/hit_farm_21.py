from are.simulation.apps.agent_user_interface import AgentUserInterface
from are.simulation.apps.synkrasis_core.hit_farm import (
    HitFarmState, GroundRover, CentralHub, SensorNetwork
)
from are.simulation.types import EventRegisterer
from are.simulation.scenarios.core_scenario import COREScenario


class CustomScenario(COREScenario):
    """
    scenarios21: Soil pH monitoring and lime application in A4
    - Monitor soil pH in plot A4; when pH drops below 5.5, trigger lime application.
    - Apply lime to shift pH into the target 6.0–7.0 range.
    """

    prompt: str | None = (
        "monitor soil pH in plot A4; when the sensors drop below 5.5, trigger a lime application. "
        "Apply 100.0kg lime to shift pH into the target 6.0–7.0 range."
    )

    def init_and_populate_apps(self, *args, **kwargs) -> None:
        agui = AgentUserInterface()
        state = HitFarmState()
        rover = GroundRover(farm_state=state, device_id='rover-1')
        hub = CentralHub(farm_state=state)
        sensors = SensorNetwork(farm_state=state)
        state.register_rover(rover)
        state.register_central_hub(hub)
        state.register_sensor_network(sensors)

        # Set initial pH below threshold to trigger lime application
        land_a4 = state.lands["A4"]
        for x in range(land_a4.width):
            for y in range(land_a4.height):
                land_a4.grid[x][y].soil_pH = 5.2

        self.apps = [agui, state, rover, hub, sensors]

    def build_events_flow(self) -> None:
        agui = self.get_typed_app(AgentUserInterface)
        state = self.get_typed_app(HitFarmState)
        rover = self.get_typed_app(GroundRover)
        hub = self.get_typed_app(CentralHub)
        sensors = self.get_typed_app(SensorNetwork)

        with EventRegisterer.capture_mode():
            # Single user message to trigger the entire workflow
            e0 = agui.send_message_to_agent(content=self.prompt).depends_on(None, delay_seconds=1)

            # Get coordinates for A4
            info = state.get_coordinates(land_name="A4").oracle().depends_on(e0, delay_seconds=1)
            (x, y) = state.lands["A4"].origin

            # Monitor soil pH at A4
            o_pH_check = sensors.get_soil_pH(x=x, y=y).oracle().depends_on(info, delay_seconds=1)

            # If pH < 5.5, refill lime from hub (100 kg lime to increase pH to 6.0-7.0 range)
            o_refill = hub.refill_lime(device_id=rover.state.device_id, amount_kg=100.0).oracle().depends_on(
                o_pH_check, delay_seconds=1)

            # Move rover to A4
            o_move = rover.move_to(x=x, y=y).oracle().depends_on([info, o_refill], delay_seconds=1)

            # Apply lime to adjust pH to target 6.0-7.0 range
            o_apply_lime = rover.apply_lime(kg=100.0, target_pH=6.5).oracle().depends_on(o_move, delay_seconds=1)

            # Verify pH after lime application
            o_pH_verify = sensors.get_soil_pH(x=x, y=y).oracle().depends_on(o_apply_lime, delay_seconds=1)

            # Return rover to base
            o_return = rover.return_to_base().oracle().depends_on(o_pH_verify, delay_seconds=1)

        self.events = [e0, info, o_pH_check, o_refill, o_move, o_apply_lime, o_pH_verify, o_return]


if __name__ == "__main__":
    from are.simulation.scenarios.utils.cli_utils import run_and_validate
    run_and_validate(CustomScenario())

